"""Vision-first element detection — use Gemini's vision to locate elements by description.

Instead of fragile CSS selectors, the agent describes what it wants to click
("the blue Apply button", "the search box") and Gemini finds the coordinates
by analyzing a screenshot.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser_agent.browser.engine import BrowserEngine
    from browser_agent.browser.page_controller import PageController
    from browser_agent.browser.screenshot import ScreenshotCapture

logger = logging.getLogger(__name__)

# JS to get the viewport dimensions + annotate elements with numbered labels
ANNOTATE_PAGE = """
(function() {
    // Remove previous annotations
    document.querySelectorAll('.__ai_label').forEach(e => e.remove());

    const sel = 'a[href], button, input, textarea, select, [role="button"], [onclick], [tabindex]:not([tabindex="-1"]), img[alt]';
    const els = document.querySelectorAll(sel);
    const results = [];

    for (let i = 0; i < els.length && results.length < 40; i++) {
        const el = els[i];
        const rect = el.getBoundingClientRect();
        if (rect.width < 5 || rect.height < 5) continue;
        if (rect.bottom < 0 || rect.top > window.innerHeight) continue;
        if (rect.right < 0 || rect.left > window.innerWidth) continue;

        const idx = results.length;

        // Overlay a small numbered label on each element
        const label = document.createElement('div');
        label.className = '__ai_label';
        label.textContent = idx.toString();
        Object.assign(label.style, {
            position: 'fixed',
            left: (rect.left - 2) + 'px',
            top: (rect.top - 14) + 'px',
            background: '#6c5ce7',
            color: '#fff',
            fontSize: '10px',
            fontWeight: '700',
            fontFamily: 'monospace',
            padding: '1px 4px',
            borderRadius: '4px',
            zIndex: '2147483640',
            pointerEvents: 'none',
            lineHeight: '13px'
        });
        document.documentElement.appendChild(label);

        results.push({
            index: idx,
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            tag: el.tagName.toLowerCase(),
            text: (el.textContent || el.value || el.placeholder || el.getAttribute('aria-label') || el.alt || '').trim().substring(0, 60)
        });
    }

    return JSON.stringify({elements: results, viewport: {w: window.innerWidth, h: window.innerHeight}});
})()
"""

REMOVE_ANNOTATIONS = """
(function() {
    document.querySelectorAll('.__ai_label').forEach(e => e.remove());
})()
"""

CLICK_AT_COORDINATES = """
(async function(x, y) {
    if (window.__ai) {
        window.__ai.showLabel('Clicking at (' + x + ', ' + y + ')');
        await window.__ai.moveCursorTo(x, y, 600);
        window.__ai.showRipple(x, y);
        await new Promise(r => setTimeout(r, 200));
    }

    const el = document.elementFromPoint(x, y);
    if (!el) return JSON.stringify({success: false, error: 'No element at coordinates'});

    ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(type => {
        el.dispatchEvent(new PointerEvent(type, {
            bubbles: true, cancelable: true, view: window,
            clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse'
        }));
    });

    await new Promise(r => setTimeout(r, 300));
    if (window.__ai) { window.__ai.hideLabel(); }

    return JSON.stringify({
        success: true,
        tag: el.tagName.toLowerCase(),
        text: (el.textContent || '').trim().substring(0, 80)
    });
})(%d, %d)
"""


class VisionDetector:
    """Uses numbered annotations + screenshot + Gemini to find elements by description."""

    def __init__(
        self,
        page_controller: PageController,
        screenshot_capture: ScreenshotCapture,
        browser_engine: BrowserEngine,
    ):
        self._pc = page_controller
        self._ss = screenshot_capture
        self._engine = browser_engine

    async def annotate_and_capture(self) -> tuple[str, list[dict]]:
        """Annotate visible elements with numbers, take screenshot, return (base64, elements)."""
        raw = await self._pc.run_js(ANNOTATE_PAGE)
        elements = []
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
                elements = data.get("elements", [])
            except json.JSONDecodeError:
                pass

        # Capture screenshot WITH annotations visible
        await asyncio.sleep(0.15)
        view = self._engine.current_view()
        b64 = self._ss.capture(view) if view else ""

        # Remove annotations from the page
        await self._pc.run_js(REMOVE_ANNOTATIONS)

        return b64, elements

    async def click_at(self, x: int, y: int) -> str:
        """Click at specific pixel coordinates with visual cursor animation."""
        await self._pc._ensure_visuals()
        script = CLICK_AT_COORDINATES % (x, y)
        result = await self._pc._run_js_json(script)
        if result.get("success"):
            return f"Clicked at ({x},{y}): {result.get('tag')} — {result.get('text', '')[:60]}"
        return f"Click at ({x},{y}) failed: {result.get('error', 'unknown')}"

    def build_vision_prompt(self, description: str, elements: list[dict]) -> str:
        """Build a prompt asking Gemini to identify which numbered element matches the description."""
        element_list = "\n".join(
            f"  [{e['index']}] <{e['tag']}> at ({e['x']},{e['y']}) text={e['text']!r}"
            for e in elements
        )
        return (
            f"Look at this screenshot. Each interactive element has a purple numbered label.\n"
            f"The user wants to interact with: \"{description}\"\n\n"
            f"Elements on the page:\n{element_list}\n\n"
            f"Which element number best matches the description? "
            f"Reply with ONLY a JSON object: {{\"index\": <number>, \"x\": <center_x>, \"y\": <center_y>, \"confidence\": <0-1>}}\n"
            f"If no element matches, reply: {{\"index\": -1, \"confidence\": 0}}"
        )
