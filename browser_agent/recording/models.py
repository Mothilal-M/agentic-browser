"""Session recording data models."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class RecordedEvent:
    """A single timestamped event in a session recording."""
    timestamp: float
    event_type: str       # "user_msg", "tool_call", "tool_result", "assistant_msg", "screenshot", "error"
    tool_name: str = ""
    content: str = ""
    detail: str = ""
    screenshot_b64: str = ""  # JPEG base64 at the moment of the event


@dataclass
class SessionRecording:
    """A complete recorded session — all events + metadata."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "Untitled Session"
    started_at: float = field(default_factory=time.time)
    ended_at: float = 0.0
    events: list[RecordedEvent] = field(default_factory=list)

    @property
    def duration_sec(self) -> float:
        if self.ended_at > 0:
            return self.ended_at - self.started_at
        if self.events:
            return self.events[-1].timestamp - self.started_at
        return 0.0

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def screenshot_count(self) -> int:
        return sum(1 for e in self.events if e.screenshot_b64)
