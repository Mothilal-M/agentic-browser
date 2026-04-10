"""Session recorder — captures all agent actions with timestamps and screenshots."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from browser_agent.recording.models import RecordedEvent, SessionRecording

if TYPE_CHECKING:
    from browser_agent.browser.engine import BrowserEngine
    from browser_agent.browser.screenshot import ScreenshotCapture

logger = logging.getLogger(__name__)


class SessionRecorder:
    """Records all agent interactions into a SessionRecording."""

    def __init__(
        self,
        screenshot_capture: ScreenshotCapture | None = None,
        browser_engine: BrowserEngine | None = None,
    ) -> None:
        self._ss = screenshot_capture
        self._engine = browser_engine
        self._recording: SessionRecording | None = None

    @property
    def is_recording(self) -> bool:
        return self._recording is not None

    @property
    def current(self) -> SessionRecording | None:
        return self._recording

    def start(self, title: str = "Untitled Session") -> SessionRecording:
        self._recording = SessionRecording(title=title)
        logger.info("Session recording started: %s", self._recording.session_id)
        return self._recording

    def stop(self) -> SessionRecording | None:
        if not self._recording:
            return None
        self._recording.ended_at = time.time()
        rec = self._recording
        self._recording = None
        logger.info("Session recording stopped: %s (%d events)", rec.session_id, rec.event_count)
        return rec

    def _capture_screenshot(self) -> str:
        """Take a quick screenshot if available."""
        if self._ss and self._engine:
            view = self._engine.current_view()
            if view:
                try:
                    return self._ss.capture(view)
                except Exception:
                    pass
        return ""

    def record_user_message(self, text: str) -> None:
        if not self._recording:
            return
        self._recording.events.append(RecordedEvent(
            timestamp=time.time(),
            event_type="user_msg",
            content=text,
            screenshot_b64=self._capture_screenshot(),
        ))

    def record_tool_call(self, tool_name: str, args: str) -> None:
        if not self._recording:
            return
        self._recording.events.append(RecordedEvent(
            timestamp=time.time(),
            event_type="tool_call",
            tool_name=tool_name,
            content=f"{tool_name}({args})",
        ))

    def record_tool_result(self, tool_name: str, result: str) -> None:
        if not self._recording:
            return
        self._recording.events.append(RecordedEvent(
            timestamp=time.time(),
            event_type="tool_result",
            tool_name=tool_name,
            content=result,
            screenshot_b64=self._capture_screenshot(),
        ))

    def record_assistant_message(self, text: str) -> None:
        if not self._recording:
            return
        self._recording.events.append(RecordedEvent(
            timestamp=time.time(),
            event_type="assistant_msg",
            content=text,
            screenshot_b64=self._capture_screenshot(),
        ))

    def record_error(self, error: str) -> None:
        if not self._recording:
            return
        self._recording.events.append(RecordedEvent(
            timestamp=time.time(),
            event_type="error",
            content=error,
        ))
