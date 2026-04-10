"""Smart error recovery — wraps tool calls with automatic retry and fallback strategies.

When an action fails, tries alternative approaches before giving up:
1. Retry with a short wait (element might not be loaded yet)
2. Try scrolling to find the element
3. Try alternative selectors (by text content, aria-label)
4. Fall back to coordinate-based clicking via vision
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser_agent.browser.page_controller import PageController

logger = logging.getLogger(__name__)

# JS to find elements by visible text content
FIND_BY_TEXT = """
(function(searchText) {
    const allEls = document.querySelectorAll('a, button, input, textarea, select, [role="button"], label, span, p, h1, h2, h3, h4, li, td, th');
    const lower = searchText.toLowerCase();

    for (const el of allEls) {
        const text = (el.textContent || el.value || '').trim().toLowerCase();
        if (text === lower || text.includes(lower)) {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0 && rect.top < window.innerHeight && rect.bottom > 0) {
                // Build a reliable selector
                let selector = el.tagName.toLowerCase();
                if (el.id) selector += '#' + el.id;
                else if (el.name) selector += '[name="' + el.name + '"]';

                return JSON.stringify({
                    success: true,
                    selector: selector,
                    tag: el.tagName.toLowerCase(),
                    text: text.substring(0, 80),
                    x: Math.round(rect.left + rect.width / 2),
                    y: Math.round(rect.top + rect.height / 2)
                });
            }
        }
    }
    return JSON.stringify({success: false, error: 'No visible element with text: ' + searchText});
})(%s)
"""

FIND_BY_ARIA = """
(function(label) {
    const el = document.querySelector('[aria-label="' + label + '"], [title="' + label + '"], [placeholder="' + label + '"]');
    if (!el) return JSON.stringify({success: false});
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return JSON.stringify({success: false});

    let selector = el.tagName.toLowerCase();
    if (el.id) selector += '#' + el.id;
    else if (el.getAttribute('aria-label')) selector += '[aria-label="' + el.getAttribute('aria-label') + '"]';

    return JSON.stringify({
        success: true,
        selector: selector,
        x: Math.round(rect.left + rect.width / 2),
        y: Math.round(rect.top + rect.height / 2)
    });
})(%s)
"""


class ErrorRecovery:
    """Provides fallback strategies when primary tool actions fail."""

    def __init__(self, page_controller: PageController) -> None:
        self._pc = page_controller

    async def find_element_by_text(self, text: str) -> dict | None:
        """Find an element by its visible text content."""
        import json as _json
        script = FIND_BY_TEXT % _json.dumps(text)
        result = await self._pc._run_js_json(script)
        return result if result.get("success") else None

    async def find_element_by_aria(self, label: str) -> dict | None:
        """Find an element by aria-label, title, or placeholder."""
        import json as _json
        script = FIND_BY_ARIA % _json.dumps(label)
        result = await self._pc._run_js_json(script)
        return result if result.get("success") else None

    async def smart_click(self, selector: str) -> str:
        """Try to click with CSS selector, falling back through multiple strategies."""

        # Strategy 1: Direct CSS selector
        result = await self._pc.click(selector)
        if "failed" not in result.lower():
            return result

        logger.info("Direct click failed for %r, trying fallbacks", selector)

        # Strategy 2: Wait a bit and retry (element might be loading)
        await asyncio.sleep(1.0)
        result = await self._pc.click(selector)
        if "failed" not in result.lower():
            return f"[retry] {result}"

        # Strategy 3: Try to find by text extracted from selector
        text_match = _extract_text_hint(selector)
        if text_match:
            found = await self.find_element_by_text(text_match)
            if found:
                result = await self._pc.click(found["selector"])
                if "failed" not in result.lower():
                    return f"[by-text] {result}"

        # Strategy 4: Try aria-label
        if text_match:
            found = await self.find_element_by_aria(text_match)
            if found:
                result = await self._pc.click(found["selector"])
                if "failed" not in result.lower():
                    return f"[by-aria] {result}"

        # Strategy 5: Scroll down and retry
        await self._pc.scroll("down", 400)
        await asyncio.sleep(0.5)
        result = await self._pc.click(selector)
        if "failed" not in result.lower():
            return f"[after-scroll] {result}"

        return f"All click strategies failed for '{selector}'. Try click_by_description() with a visual description instead."

    async def smart_type(self, selector: str, text: str) -> str:
        """Try to type with CSS selector, falling back through strategies."""

        result = await self._pc.type_text(selector, text)
        if "failed" not in result.lower():
            return result

        logger.info("Direct type failed for %r, trying fallbacks", selector)

        # Wait and retry
        await asyncio.sleep(1.0)
        result = await self._pc.type_text(selector, text)
        if "failed" not in result.lower():
            return f"[retry] {result}"

        # Try by placeholder/aria text
        text_hint = _extract_text_hint(selector)
        if text_hint:
            found = await self.find_element_by_aria(text_hint)
            if found:
                result = await self._pc.type_text(found["selector"], text)
                if "failed" not in result.lower():
                    return f"[by-aria] {result}"

        return f"All type strategies failed for '{selector}'. Try using click_by_description() first to focus the field."


def _extract_text_hint(selector: str) -> str | None:
    """Extract possible text content from a selector for fuzzy matching.

    e.g. 'button:has-text("Submit")' → 'Submit'
    e.g. 'a.apply-btn' → 'apply'
    e.g. '#login-button' → 'login'
    """
    # :has-text("...")
    m = re.search(r':has-text\(["\'](.+?)["\']\)', selector)
    if m:
        return m.group(1)

    # Text in attribute selectors: [aria-label="Search"]
    m = re.search(r'\[(?:aria-label|title|placeholder)=["\'](.+?)["\']\]', selector)
    if m:
        return m.group(1)

    # Extract words from id/class: #login-button → login button
    m = re.search(r'[#.]([a-zA-Z][\w-]*)', selector)
    if m:
        words = re.split(r'[-_]', m.group(1))
        meaningful = [w for w in words if len(w) > 2 and w.lower() not in ("btn", "div", "wrapper", "container")]
        if meaningful:
            return " ".join(meaningful)

    return None
