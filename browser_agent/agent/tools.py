"""Browser tool functions — created via closure factory to bind PageController."""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from browser_agent.browser.engine import BrowserEngine
    from browser_agent.browser.page_controller import PageController
    from browser_agent.browser.screenshot import ScreenshotCapture
    from browser_agent.multiagent.coordinator import MultiAgentCoordinator
    from browser_agent.skills.player import SkillPlayer
    from browser_agent.skills.store import SkillStore
    from browser_agent.storage.memory_db import MemoryDB
    from browser_agent.storage.user_profile import UserProfile


# ═══════════════════════════════════════════════════════════════
#  TOOL TIERING SYSTEM
# ═══════════════════════════════════════════════════════════════

CORE_TOOLS = {
    "navigate_to", "snapshot", "click_ref", "fill_ref",
    "press_key", "scroll_page", "take_screenshot", "done",
}

STANDARD_TOOLS = CORE_TOOLS | {
    "click_element", "type_text", "extract_text", "go_back",
    "wait_for_element", "find_element_by_text", "diff_snapshot",
    "remember", "recall", "get_page_elements",
}

ADVANCED_TOOLS = STANDARD_TOOLS | {
    "smart_click", "smart_type", "click_by_description",
    "click_at_coordinates", "understand_page", "autofill_form",
    "get_my_profile", "save_profile_field", "upload_file",
    "click_shadow_element", "list_iframes", "check_for_captcha",
    "wait_for_network_idle", "wait_for_url_match",
    "diff_screenshot", "go_forward",
}

# Step budgets per tier
STEP_BUDGETS = {"simple": 20, "standard": 25, "advanced": 30, "full": 40}


def classify_task_complexity(user_message: str) -> str:
    """Classify task complexity from user message."""
    msg = user_message.lower()

    full_kw = ["skill", "save workflow", "qa test", "dogfood", "multi-agent", "specialist", "export session"]
    if any(k in msg for k in full_kw):
        return "full"

    advanced_kw = ["upload", "captcha", "shadow", "iframe", "autofill", "profile", "session", "import"]
    if any(k in msg for k in advanced_kw):
        return "advanced"

    simple_kw = [
        "send", "click", "type", "open", "go to", "navigate", "search",
        "log in", "sign in", "fill", "write", "say", "reply", "message",
    ]
    if len(msg.split()) <= 20 and any(k in msg for k in simple_kw):
        return "simple"

    return "standard"


def filter_tools_by_tier(all_tools: list, tier: str) -> list:
    """Return only tools matching the given tier."""
    if tier == "full":
        return all_tools
    allowed = {"simple": CORE_TOOLS, "standard": STANDARD_TOOLS, "advanced": ADVANCED_TOOLS}.get(tier, STANDARD_TOOLS)
    return [t for t in all_tools if t.__name__ in allowed]


def create_browser_tools(
    page_controller: PageController,
    screenshot_capture: ScreenshotCapture,
    browser_engine: BrowserEngine,
    memory_db: "MemoryDB | None" = None,
    skill_store: "SkillStore | None" = None,
    skill_player: "SkillPlayer | None" = None,
    user_profile: "UserProfile | None" = None,
    vision_detector=None,
    error_recovery=None,
    multi_agent: "MultiAgentCoordinator | None" = None,
) -> list[Callable]:
    """Create tool functions with browser components bound via closure."""

    async def navigate_to(url: str) -> str:
        """Navigate the browser to a URL."""
        await page_controller.navigate(url)
        info = await page_controller.get_page_info()
        return f"Navigated to {url}. Page title: {info.get('title', 'unknown')}"

    async def click_element(selector: str) -> str:
        """Click an element on the page by CSS selector. Shows animated cursor moving to the element."""
        result = await page_controller.click(selector)
        await asyncio.sleep(0.5)  # Let user see the click effect
        return result

    async def type_text(selector: str, text: str) -> str:
        """Type text into an input field with visible character-by-character animation."""
        result = await page_controller.type_text(selector, text)
        await asyncio.sleep(0.3)
        return result

    async def scroll_page(direction: str = "down", pixels: int = 500) -> str:
        """Scroll the page with visual indicator. direction: 'up' or 'down'."""
        result = await page_controller.scroll(direction, pixels)
        return result

    async def press_key(key: str) -> str:
        """Press a keyboard key with visual label. Common keys: Enter, Tab, Escape, Backspace, ArrowDown."""
        result = await page_controller.press_key(key)
        return result

    async def extract_text(selector: str = "body") -> str:
        """Extract visible text content from an element. Defaults to the whole page body."""
        result = await page_controller.extract_text(selector)
        return result[:4000]

    async def take_screenshot() -> str:
        """Take a screenshot of the current browser page for visual analysis."""
        view = browser_engine.current_view()
        if not view:
            return "No browser view available"
        # Hide AI visuals so they don't appear in the screenshot sent to Gemini
        await page_controller.hide_visuals()
        await asyncio.sleep(0.1)
        b64 = screenshot_capture.capture(view)
        browser_engine._last_screenshot_b64 = b64
        return "Screenshot captured. The image has been sent for visual analysis."

    async def get_page_elements() -> str:
        """List all interactive elements (buttons, links, inputs) visible on the page."""
        result = await page_controller.get_interactive_elements()
        return result

    async def go_back() -> str:
        """Navigate back in browser history."""
        view = browser_engine.current_view()
        if view:
            view.back()
            await asyncio.sleep(1)
            info = await page_controller.get_page_info()
            return f"Went back. Now on: {info.get('title', 'unknown')}"
        return "No browser view available"

    async def go_forward() -> str:
        """Navigate forward in browser history."""
        view = browser_engine.current_view()
        if view:
            view.forward()
            await asyncio.sleep(1)
            info = await page_controller.get_page_info()
            return f"Went forward. Now on: {info.get('title', 'unknown')}"
        return "No browser view available"

    async def wait_for_element(selector: str, timeout: int = 5000) -> str:
        """Wait for an element to appear on the page. timeout is in milliseconds."""
        found = await page_controller.wait_for_selector(selector, timeout)
        if found:
            return f"Element '{selector}' found on the page."
        return f"Element '{selector}' did not appear within {timeout}ms."

    # -- Memory tools --

    async def remember(fact: str, category: str = "other") -> str:
        """Save a fact about the user to long-term memory. Categories: preference, credential, personal, behavior, other. Use this when you learn something about the user that would be useful in future conversations."""
        if not memory_db:
            return "Memory system not available."
        entry = memory_db.remember(fact, category)
        return f"Remembered: '{fact}' (category: {entry.category})"

    async def recall(query: str) -> str:
        """Search long-term memory for facts about the user. Use this to recall preferences, credentials, personal info, or past behaviors."""
        if not memory_db:
            return "Memory system not available."
        entries = memory_db.recall(query, limit=5)
        if not entries:
            return f"No memories found matching '{query}'."
        lines = [f"Found {len(entries)} memories:"]
        for e in entries:
            lines.append(f"- [{e.category}] {e.fact}")
        return "\n".join(lines)

    # -- Skill tools --

    async def list_skills() -> str:
        """List all saved skills (replayable workflows)."""
        if not skill_store:
            return "Skill system not available."
        skills = skill_store.list_all(limit=20)
        if not skills:
            return "No skills saved yet."
        lines = [f"Found {len(skills)} skills:"]
        for s in skills:
            steps = len(s.steps)
            lines.append(f"- **{s.name}** ({steps} steps, run {s.run_count}x) — {s.description[:80]}")
        return "\n".join(lines)

    async def run_skill(skill_name: str) -> str:
        """Run a saved skill by name. This replays the recorded workflow step by step with visual automation."""
        if not skill_store or not skill_player:
            return "Skill system not available."
        skill = skill_store.get_by_name(skill_name)
        if not skill:
            return f"Skill '{skill_name}' not found. Use list_skills() to see available skills."
        skill_store.increment_run_count(skill.skill_id)
        success, summary = await skill_player.play(skill)
        return f"Skill '{skill_name}' {'completed' if success else 'failed'}: {summary}"

    async def save_current_as_skill(skill_name: str, steps_description: str) -> str:
        """Save a series of browser actions as a replayable skill. Provide the skill name and a description of the steps. The steps should be formatted as a JSON array like: [{"tool_name":"navigate_to","args":{"url":"https://example.com"}},{"tool_name":"click_element","args":{"selector":"#btn"}}]"""
        if not skill_store:
            return "Skill system not available."
        import json
        from browser_agent.skills.models import Skill, SkillStep
        try:
            raw_steps = json.loads(steps_description)
        except json.JSONDecodeError:
            return "Invalid JSON. Provide steps as a JSON array of {tool_name, args} objects."
        steps = [
            SkillStep(
                tool_name=s.get("tool_name", ""),
                args=s.get("args", {}),
                description=s.get("description", ""),
            )
            for s in raw_steps if s.get("tool_name")
        ]
        if not steps:
            return "No valid steps found."
        skill = Skill(name=skill_name, steps=steps)
        skill.description = f"{len(steps)} steps"
        skill_store.save(skill)
        return f"Skill '{skill_name}' saved with {len(steps)} steps. Use run_skill('{skill_name}') to replay."

    async def delete_skill(skill_name: str) -> str:
        """Delete a saved skill by name."""
        if not skill_store:
            return "Skill system not available."
        skill = skill_store.get_by_name(skill_name)
        if not skill:
            return f"Skill '{skill_name}' not found."
        skill_store.delete(skill.skill_id)
        return f"Skill '{skill_name}' deleted."

    # -- Phase 3: Advanced browser control tools --

    async def upload_file(selector: str, file_path: str) -> str:
        """Upload a local file to a <input type='file'> element. Provide the CSS selector of the file input and the absolute path to the file."""
        import base64
        import mimetypes
        from pathlib import Path as P

        p = P(file_path)
        if not p.exists():
            return f"File not found: {file_path}"

        mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        b64 = base64.b64encode(p.read_bytes()).decode()
        result = await page_controller.upload_file(selector, p.name, b64, mime)
        return result

    async def check_for_captcha() -> str:
        """Check if the current page has a CAPTCHA or 2FA prompt. If detected, the user will need to solve it manually."""
        result = await page_controller.detect_captcha()
        if result.get("detected"):
            signals = ", ".join(result.get("signals", []))
            return f"CAPTCHA/2FA detected: {signals}. Please solve it manually, then tell me to continue."
        return "No CAPTCHA or 2FA detected on this page."

    async def click_shadow_element(selector: str) -> str:
        """Click an element that might be inside a Shadow DOM. Uses deep traversal to find elements inside shadow roots."""
        result = await page_controller.click_shadow(selector)
        await asyncio.sleep(0.5)
        return result

    async def list_iframes() -> str:
        """List all iframes on the current page with their sources and visibility."""
        return await page_controller.get_iframes()

    async def autofill_form(field_mapping: str) -> str:
        """Auto-fill multiple form fields at once. Provide a JSON object mapping CSS selectors to values, e.g.: {"#name": "John", "#email": "john@example.com", "#phone": "1234567890"}"""
        result = await page_controller.autofill_form(field_mapping)
        return result

    async def get_my_profile() -> str:
        """Get the user's saved profile info (name, email, phone, etc.) for filling forms."""
        if not user_profile:
            return "User profile not available."
        filled = user_profile.get_filled()
        if not filled:
            return "No profile info saved yet. Ask the user for their details."
        lines = ["User's profile:"]
        for f in filled:
            lines.append(f"- {f.label}: {f.value}")
        return "\n".join(lines)

    async def save_profile_field(field_name: str, value: str) -> str:
        """Save or update a field in the user's profile. Common fields: full_name, email, phone, address, city, state, zip_code, country, linkedin_url, resume_path, current_company, current_title."""
        if not user_profile:
            return "User profile not available."
        user_profile.set(field_name, value, field_name.replace("_", " ").title())
        return f"Saved profile: {field_name} = {value}"

    # -- Phase 4: Intelligence & Perception tools --

    async def click_by_description(visual_description: str) -> str:
        """Click an element by describing what it looks like visually — no CSS selector needed. Examples: 'the blue Apply button', 'the search box at the top', 'the first job listing link'. This annotates the page with numbered labels, takes a screenshot, then clicks the best match."""
        if not vision_detector:
            return "Vision system not available."

        # Step 1: Annotate page with numbered labels and capture screenshot
        b64, elements = await vision_detector.annotate_and_capture()
        if not elements:
            return "No interactive elements found on the page."

        # Step 2: Build an element index for the agent to choose from
        prompt = vision_detector.build_vision_prompt(visual_description, elements)

        # Step 3: Since we can't call the LLM from inside a tool, use heuristic matching
        # Match by text similarity to the description
        desc_lower = visual_description.lower()
        best_match = None
        best_score = 0

        for el in elements:
            text = el.get("text", "").lower()
            tag = el.get("tag", "")
            score = 0

            # Exact text match
            if desc_lower in text or text in desc_lower:
                score = 10

            # Word overlap
            desc_words = set(desc_lower.split())
            text_words = set(text.split())
            overlap = len(desc_words & text_words)
            score += overlap * 3

            # Tag hints: "button" in description matches <button>
            if "button" in desc_lower and tag == "button":
                score += 5
            if "link" in desc_lower and tag == "a":
                score += 5
            if "input" in desc_lower and tag == "input":
                score += 5
            if "search" in desc_lower and ("search" in text or tag == "input"):
                score += 4

            if score > best_score:
                best_score = score
                best_match = el

        if not best_match or best_score < 3:
            # Return annotated screenshot info so agent can try again
            lines = ["Could not auto-match. Here are the visible elements:"]
            for el in elements[:15]:
                lines.append(f"  [{el['index']}] <{el['tag']}> at ({el['x']},{el['y']}) text={el['text']!r}")
            lines.append(f"\nUse click_at_coordinates(x, y) to click a specific element.")
            return "\n".join(lines)

        # Step 4: Click the matched element
        x, y = best_match["x"], best_match["y"]
        result = await vision_detector.click_at(x, y)
        return f"[vision] Matched element [{best_match['index']}] <{best_match['tag']}> '{best_match['text']}' — {result}"

    async def click_at_coordinates(x: int, y: int) -> str:
        """Click at specific pixel coordinates on the page. Use this when CSS selectors fail and you know where the element is visually."""
        if not vision_detector:
            return "Vision system not available."
        result = await vision_detector.click_at(x, y)
        await asyncio.sleep(0.5)
        return result

    async def smart_click(selector: str) -> str:
        """Click an element with automatic fallback recovery. Tries: CSS selector → wait+retry → find by text → find by aria-label → scroll+retry. Use this instead of click_element when you're unsure if the selector will work."""
        if not error_recovery:
            return await page_controller.click(selector)
        result = await error_recovery.smart_click(selector)
        await asyncio.sleep(0.3)
        return result

    async def smart_type(selector: str, text: str) -> str:
        """Type text with automatic fallback recovery. Tries: CSS selector → wait+retry → find by aria/placeholder. Use this instead of type_text when you're unsure if the selector will work."""
        if not error_recovery:
            return await page_controller.type_text(selector, text)
        result = await error_recovery.smart_type(selector, text)
        return result

    async def find_element_by_text(visible_text: str) -> str:
        """Find a clickable element by its visible text content. Returns the element's CSS selector and coordinates. Useful when you know what text is on a button/link but don't have the selector."""
        if not error_recovery:
            return "Error recovery not available."
        found = await error_recovery.find_element_by_text(visible_text)
        if found:
            return f"Found: <{found['tag']}> selector={found['selector']!r} at ({found['x']},{found['y']}) text={found['text']!r}"
        return f"No visible element found with text: '{visible_text}'"

    async def understand_page() -> str:
        """Analyze the current page and provide a structured summary: what the page is about, key content, and available actions. Takes a screenshot and reads page text to give you a complete picture."""
        view = browser_engine.current_view()
        if not view:
            return "No browser view available."

        # Get page info + text + elements
        info = await page_controller.get_page_info()
        text = await page_controller.extract_text("body")
        elements = await page_controller.get_interactive_elements()

        # Build structured summary
        url = info.get("url", "")
        title = info.get("title", "")

        lines = [
            f"## Page Analysis",
            f"**URL**: {url}",
            f"**Title**: {title}",
            f"",
            f"### Page Content (first 2000 chars):",
            text[:2000],
            f"",
            f"### Interactive Elements:",
            elements[:1500] if elements else "None found",
            f"",
            f"### Scroll Position: {info.get('scrollY', 0)}px / {info.get('scrollHeight', 0)}px",
        ]
        return "\n".join(lines)

    tools = [
        navigate_to,
        click_element,
        type_text,
        scroll_page,
        press_key,
        extract_text,
        take_screenshot,
        get_page_elements,
        go_back,
        go_forward,
        wait_for_element,
        # Phase 3
        upload_file,
        check_for_captcha,
        click_shadow_element,
        list_iframes,
        autofill_form,
        get_my_profile,
        save_profile_field,
        # Phase 4
        click_by_description,
        click_at_coordinates,
        smart_click,
        smart_type,
        find_element_by_text,
        understand_page,
    ]

    # -- Completion signal --

    async def done(summary: str) -> str:
        """Call this when the task is COMPLETE. Provide a brief summary of what was accomplished. This stops the agent loop."""
        return f"TASK_COMPLETE: {summary}"

    tools.append(done)

    # -- Agent-browser inspired tools --

    _last_snapshot = {"text": "", "refs": {}}

    async def snapshot() -> str:
        """Take an accessibility tree snapshot with @ref identifiers. Returns a compact text tree like:
        @e0 [link] "Home"
        @e1 [textbox] type="email" placeholder="Email"
        @e2 [button] "Submit"
        Use click_ref(@e2) to interact with elements. Much more token-efficient than CSS selectors."""
        text, refs = await page_controller.take_snapshot()
        _last_snapshot["text"] = text
        _last_snapshot["refs"] = refs
        if not text:
            return "No accessibility tree could be captured."
        return f"Snapshot ({len(refs)} interactive elements):\n{text}"

    async def click_ref(ref: str) -> str:
        """Click an element by its @ref from the last snapshot (e.g. 'e3'). Always take a snapshot() first to get valid refs."""
        refs = _last_snapshot.get("refs", {})
        if not refs:
            return "No snapshot available. Call snapshot() first."
        result = await page_controller.click_ref(ref, refs)
        await asyncio.sleep(0.5)
        return result

    async def fill_ref(ref: str, text: str) -> str:
        """Type text into an element by its @ref. Works with inputs, textareas, AND contenteditable divs (Slack, WhatsApp). Always call snapshot() first."""
        refs = _last_snapshot.get("refs", {})
        info = refs.get(ref)
        if not info:
            return f"Ref @{ref} not found. Call snapshot() first."
        selector = info["selector"]

        # First click to focus
        await page_controller.click(selector)
        await asyncio.sleep(0.3)

        # Try standard fill first
        result = await page_controller.type_text(selector, text)

        # If standard fill didn't work (contenteditable), use execCommand
        if "failed" in result.lower():
            js = f"""
            (function() {{
                const el = document.querySelector({__import__('json').dumps(selector)});
                if (!el) return 'not found';
                el.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('insertText', false, {__import__('json').dumps(text)});
                return 'ok';
            }})()
            """
            r = await page_controller.run_js(js)
            if r == "ok":
                return f"Filled @{ref} (contenteditable): typed '{text[:50]}'"
            return f"Fill @{ref} failed: {r}"

        return f"Filled @{ref}: {result}"

    async def diff_snapshot() -> str:
        """Compare the current page state against the last snapshot. Shows what changed (elements added/removed/modified). Useful to verify if an action worked."""
        from browser_agent.browser.snapshot_diff import diff_snapshots
        old_text = _last_snapshot.get("text", "")
        if not old_text:
            return "No previous snapshot to compare against. Call snapshot() first."
        new_text, new_refs = await page_controller.take_snapshot()
        result = diff_snapshots(old_text, new_text)
        _last_snapshot["text"] = new_text
        _last_snapshot["refs"] = new_refs
        return result

    async def diff_screenshot(baseline_b64: str = "") -> str:
        """Visual pixel diff between current screenshot and a baseline. If no baseline provided, uses the last screenshot taken. Returns mismatch percentage and highlights changed areas in red."""
        from browser_agent.browser.snapshot_diff import diff_screenshots_pixel
        view = browser_engine.current_view()
        if not view:
            return "No browser view available."
        await page_controller.hide_visuals()
        await asyncio.sleep(0.1)
        current_b64 = screenshot_capture.capture(view)
        baseline = baseline_b64 or getattr(browser_engine, '_last_screenshot_b64', '')
        if not baseline:
            return "No baseline screenshot available. Take a screenshot first."
        result = diff_screenshots_pixel(baseline, current_b64)
        return f"Visual diff: {result['mismatch_pct']}% pixels changed ({result['changed_pixels']}/{result['total_pixels']})"

    async def wait_for_network_idle(timeout_ms: int = 10000) -> str:
        """Wait until no network requests are pending for 500ms. Useful for SPAs that load data after navigation."""
        return await page_controller.wait_for_network_idle(timeout_ms, 500)

    async def wait_for_url_match(url_pattern: str, timeout_ms: int = 10000) -> str:
        """Wait until the page URL matches a regex pattern. Example: wait_for_url_match('dashboard') waits until URL contains 'dashboard'."""
        return await page_controller.wait_for_url(url_pattern, timeout_ms)

    async def export_session(file_path: str, encrypt_key: str = "") -> str:
        """Export the current browser session (cookies, localStorage) to a JSON file. Optionally encrypt with a key. The session can be imported later to restore login state."""
        from browser_agent.storage.session_state import export_session_state
        path = export_session_state(browser_engine, file_path, encrypt_key)
        return f"Session exported to: {path}"

    async def import_session(file_path: str, encrypt_key: str = "") -> str:
        """Import a previously exported browser session from a JSON file. Restores cookies and localStorage. Restart browser tab to apply."""
        from browser_agent.storage.session_state import import_session_state
        ok = import_session_state(browser_engine, file_path, encrypt_key)
        return "Session imported successfully. Reload the page to apply." if ok else "Session import failed."

    async def dogfood_test(target_url: str, focus: str = "") -> str:
        """Start exploratory QA testing on a target URL. The agent will systematically test every button, link, and form, documenting any bugs found. Optionally focus on a specific area (e.g. 'billing page', 'login flow')."""
        from browser_agent.agent.dogfood import build_dogfood_prompt
        prompt = build_dogfood_prompt(target_url, focus)
        return f"ENTERING QA MODE:\n\n{prompt}"

    tools.extend([
        snapshot,
        click_ref,
        fill_ref,
        diff_snapshot,
        diff_screenshot,
        wait_for_network_idle,
        wait_for_url_match,
        export_session,
        import_session,
        dogfood_test,
    ])

    if memory_db:
        tools.extend([remember, recall])

    if skill_store and skill_player:
        tools.extend([list_skills, run_skill, save_current_as_skill, delete_skill])

    if multi_agent:
        async def execute_multi_agent_plan(goal: str, subtasks_json: str) -> str:
            """Execute a complex goal using specialist agents. Break the goal into sub-tasks
            and assign each to a specialist role. subtasks_json should be a JSON array like:
            [{"description": "Search for jobs", "role": "researcher"},
             {"description": "Fill the form", "role": "form_filler"}]
            Roles: researcher, form_filler, monitor, navigator."""
            import json
            try:
                subtasks = json.loads(subtasks_json)
            except json.JSONDecodeError:
                return "Error: subtasks_json must be valid JSON array"
            result = await multi_agent.execute_plan(goal, subtasks)
            return result

        tools.append(execute_multi_agent_plan)

    return tools
