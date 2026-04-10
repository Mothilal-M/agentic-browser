"""PageController — async bridge between Python and JavaScript on the page.

Injects a visual automation layer (cursor, highlights, typing animation)
on every page load so the user can watch the AI work.
"""

import asyncio
import json

from browser_agent.browser import js_scripts
from browser_agent.browser.engine import BrowserEngine


def _js_string(value: str) -> str:
    """Safely encode a Python string as a JS string literal."""
    return json.dumps(value)


class PageController:
    def __init__(self, engine: BrowserEngine) -> None:
        self._engine = engine
        self._visual_injected_pages: set[int] = set()

    async def _ensure_visuals(self) -> None:
        """Inject the visual cursor/highlight layer if not already present."""
        page = self._engine.current_page()
        if not page:
            return
        page_id = id(page)
        if page_id not in self._visual_injected_pages:
            await self.run_js(js_scripts.INIT_VISUAL_LAYER)
            self._visual_injected_pages.add(page_id)
            # Re-inject after navigations within the same page object
            page.loadFinished.connect(lambda ok, pid=page_id: self._on_page_load(pid))

    def _on_page_load(self, page_id: int) -> None:
        """Mark page as needing visual re-injection after navigation."""
        self._visual_injected_pages.discard(page_id)

    async def run_js(self, script: str):
        """Execute JavaScript on the current page and return the result."""
        page = self._engine.current_page()
        if not page:
            return None

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def callback(result):
            if not future.done():
                loop.call_soon_threadsafe(future.set_result, result)

        page.runJavaScript(script, callback)

        try:
            return await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            return None

    async def _run_js_json(self, script: str) -> dict:
        raw = await self.run_js(script)
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"success": False, "error": f"Invalid JSON: {raw[:200]}"}
        return {"success": False, "error": "No result from JavaScript"}

    async def navigate(self, url: str) -> None:
        from PyQt6.QtCore import QUrl

        view = self._engine.current_view()
        if not view:
            return

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def on_load_finished(ok):
            view.loadFinished.disconnect(on_load_finished)
            if not future.done():
                loop.call_soon_threadsafe(future.set_result, ok)

        view.loadFinished.connect(on_load_finished)
        view.setUrl(QUrl(url))

        try:
            await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            pass

        # Inject visuals on the new page
        await asyncio.sleep(0.3)
        await self._ensure_visuals()

    async def click(self, selector: str) -> str:
        await self._ensure_visuals()
        script = js_scripts.CLICK_ELEMENT % _js_string(selector)
        result = await self._run_js_json(script)
        if result.get("success"):
            return f"Clicked {result.get('tag', '')} element: {result.get('text', '')[:60]}"
        return f"Click failed: {result.get('error', 'unknown')}"

    async def type_text(self, selector: str, text: str, clear_first: bool = True) -> str:
        await self._ensure_visuals()
        script = js_scripts.TYPE_TEXT % (
            _js_string(selector),
            _js_string(text),
            "true" if clear_first else "false",
        )
        result = await self._run_js_json(script)
        if result.get("success"):
            return f"Typed text into element. Current value: {result.get('value', '')}"
        return f"Type failed: {result.get('error', 'unknown')}"

    async def scroll(self, direction: str = "down", pixels: int = 500) -> str:
        await self._ensure_visuals()
        script = js_scripts.SCROLL_PAGE % (_js_string(direction), pixels)
        result = await self._run_js_json(script)
        if result.get("success"):
            return f"Scrolled {direction} {pixels}px. Position: {result.get('scrollY')}px / {result.get('scrollHeight')}px"
        return "Scroll failed"

    async def press_key(self, key: str) -> str:
        await self._ensure_visuals()
        script = js_scripts.PRESS_KEY % _js_string(key)
        result = await self._run_js_json(script)
        if result.get("success"):
            return f"Pressed key: {key}"
        return f"Key press failed: {result.get('error', 'unknown')}"

    async def get_interactive_elements(self) -> str:
        result = await self.run_js(js_scripts.GET_INTERACTIVE_ELEMENTS)
        if isinstance(result, str):
            try:
                elements = json.loads(result)
                lines = []
                for el in elements:
                    line = f"[{el['index']}] <{el['tag']}> selector={el['selector']!r}"
                    if el.get("type"):
                        line += f" type={el['type']}"
                    if el.get("text"):
                        line += f" text={el['text']!r}"
                    lines.append(line)
                return "\n".join(lines) if lines else "No interactive elements found"
            except json.JSONDecodeError:
                pass
        return "Could not extract elements"

    async def extract_text(self, selector: str = "body") -> str:
        script = js_scripts.EXTRACT_TEXT % _js_string(selector)
        result = await self._run_js_json(script)
        if result.get("success"):
            return result.get("text", "")
        return f"Extract failed: {result.get('error', 'unknown')}"

    async def get_page_info(self) -> dict:
        result = await self._run_js_json(js_scripts.GET_PAGE_INFO)
        return result if result.get("url") else {"url": "", "title": ""}

    async def wait_for_selector(self, selector: str, timeout_ms: int = 5000) -> bool:
        script = js_scripts.WAIT_FOR_ELEMENT % (_js_string(selector), timeout_ms)
        result = await self._run_js_json(script)
        return result.get("found", False)

    async def hide_visuals(self) -> None:
        await self.run_js(js_scripts.HIDE_VISUALS)

    # ── Phase 3: Advanced browser control ──

    async def upload_file(self, selector: str, file_name: str, file_b64: str, mime_type: str) -> str:
        await self._ensure_visuals()
        script = js_scripts.UPLOAD_FILE % (
            _js_string(selector), _js_string(file_name),
            _js_string(file_b64), _js_string(mime_type),
        )
        result = await self._run_js_json(script)
        if result.get("success"):
            return f"Uploaded '{result.get('fileName')}' ({result.get('size')} bytes)"
        return f"Upload failed: {result.get('error', 'unknown')}"

    async def detect_captcha(self) -> dict:
        result = await self._run_js_json(js_scripts.DETECT_CAPTCHA)
        return result

    async def query_shadow_dom(self, selector: str) -> dict:
        script = js_scripts.QUERY_SHADOW_DOM % _js_string(selector)
        return await self._run_js_json(script)

    async def click_shadow(self, selector: str) -> str:
        await self._ensure_visuals()
        script = js_scripts.CLICK_SHADOW_DOM % _js_string(selector)
        result = await self._run_js_json(script)
        if result.get("success"):
            return f"Clicked shadow element: {result.get('tag')} — {result.get('text', '')[:60]}"
        return f"Shadow click failed: {result.get('error', 'unknown')}"

    async def get_iframes(self) -> str:
        raw = await self.run_js(js_scripts.GET_IFRAMES)
        if isinstance(raw, str):
            try:
                frames = json.loads(raw)
                if not frames:
                    return "No iframes on this page."
                lines = [f"Found {len(frames)} iframes:"]
                for f in frames:
                    lines.append(f"  [{f['index']}] src={f['src']!r} id={f['id']!r} visible={f['visible']}")
                return "\n".join(lines)
            except json.JSONDecodeError:
                pass
        return "Could not detect iframes."

    async def autofill_form(self, field_map_json: str) -> str:
        await self._ensure_visuals()
        script = js_scripts.AUTOFILL_FORM % _js_string(field_map_json)
        result = await self._run_js_json(script)
        if result.get("success"):
            filled = result.get("filled", [])
            ok = sum(1 for f in filled if f.get("success"))
            return f"Auto-filled {ok}/{len(filled)} fields."
        return f"Autofill failed: {result.get('error', 'unknown')}"

    # ── Accessibility Tree Snapshots ──

    async def take_snapshot(self) -> tuple[str, dict]:
        """Capture an accessibility tree snapshot with @ref system.

        Returns (snapshot_text, refs_dict) where refs_dict maps 'e0','e1'...
        to {selector, tag, role, text, x, y}.
        """
        raw = await self.run_js(js_scripts.ACCESSIBILITY_SNAPSHOT)
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
                return data.get("snapshot", ""), data.get("refs", {})
            except json.JSONDecodeError:
                pass
        return "", {}

    async def click_ref(self, ref: str, refs: dict) -> str:
        """Click an element by its @ref (e.g. 'e3'). Looks up the selector from refs dict."""
        await self._ensure_visuals()
        info = refs.get(ref)
        if not info:
            return f"Ref @{ref} not found in current snapshot."
        selector = info.get("selector", "")
        if not selector:
            return f"No selector for @{ref}"
        script = js_scripts.CLICK_REF % _js_string(selector)
        result = await self._run_js_json(script)
        if result.get("success"):
            return f"Clicked @{ref} [{info.get('role', info.get('tag'))}] \"{info.get('text', '')[:40]}\""
        return f"Click @{ref} failed: {result.get('error', 'unknown')}"

    # ── Network Wait Strategies ──

    async def wait_for_network_idle(self, timeout_ms: int = 10000, quiet_ms: int = 500) -> str:
        script = js_scripts.WAIT_NETWORK_IDLE % (timeout_ms, quiet_ms)
        result = await self._run_js_json(script)
        if result.get("idle"):
            return "Network is idle — no pending requests."
        return f"Network idle timeout: {result.get('error', 'unknown')}"

    async def wait_for_url(self, pattern: str, timeout_ms: int = 10000) -> str:
        script = js_scripts.WAIT_URL_MATCH % (_js_string(pattern), timeout_ms)
        result = await self._run_js_json(script)
        if result.get("success"):
            return f"URL matched: {result.get('url', '')}"
        return f"URL match timeout: current={result.get('current', '')}"
