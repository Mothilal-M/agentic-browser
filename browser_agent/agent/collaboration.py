"""Human-in-the-loop task collaboration primitives.

Tools can pause a running task, explain the blocker, and await user help
without forcing the whole agent run to restart.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable


TaskStatus = str


@dataclass
class HelpRequest:
    blocker_type: str
    reason: str
    instructions: str
    expected_response_type: str = "text"
    continue_label: str = "Continue"
    allow_continue: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_payload(self) -> dict[str, Any]:
        return {
            "blocker_type": self.blocker_type,
            "reason": self.reason,
            "instructions": self.instructions,
            "expected_response_type": self.expected_response_type,
            "continue_label": self.continue_label,
            "allow_continue": self.allow_continue,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class TaskSession:
    goal: str
    status: TaskStatus = "running"
    current_subgoal: str = ""
    last_successful_action: str = ""
    last_snapshot_text: str = ""
    last_snapshot_refs: dict[str, Any] = field(default_factory=dict)
    pending_blocker: HelpRequest | None = None
    resume_instructions: str = ""
    result_summary: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.updated_at = time.time()


class CollaborationManager:
    """Stores the active task session and coordinates help/resume flow."""

    def __init__(
        self,
        on_help_requested: Callable[[HelpRequest, TaskSession], None] | None = None,
        on_status_changed: Callable[[TaskStatus, TaskSession], None] | None = None,
    ) -> None:
        self._session: TaskSession | None = None
        self._waiter: asyncio.Future[str] | None = None
        self._on_help_requested = on_help_requested
        self._on_status_changed = on_status_changed

    @property
    def session(self) -> TaskSession | None:
        return self._session

    @property
    def is_waiting(self) -> bool:
        return bool(self._session and self._session.status == "waiting_for_user" and self._waiter and not self._waiter.done())

    def start_task(self, goal: str) -> TaskSession:
        self._session = TaskSession(goal=goal, status="running")
        self._emit_status()
        return self._session

    def reset(self) -> None:
        if self._waiter and not self._waiter.done():
            self._waiter.cancel()
        self._waiter = None
        self._session = None

    def note_subgoal(self, subgoal: str) -> None:
        if not self._session:
            return
        self._session.current_subgoal = subgoal
        self._session.touch()

    def note_action(self, action: str) -> None:
        if not self._session:
            return
        self._session.last_successful_action = action
        self._session.touch()

    def note_snapshot(self, snapshot_text: str, refs: dict[str, Any]) -> None:
        if not self._session:
            return
        self._session.last_snapshot_text = snapshot_text
        self._session.last_snapshot_refs = dict(refs)
        self._session.touch()

    async def request_help(
        self,
        blocker_type: str,
        reason: str,
        instructions: str,
        *,
        expected_response_type: str = "text",
        continue_label: str = "Continue",
        allow_continue: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if not self._session:
            self.start_task("Untracked task")

        allow_continue = expected_response_type in {"manual", "confirmation", "acknowledge"} if allow_continue is None else allow_continue
        request = HelpRequest(
            blocker_type=blocker_type,
            reason=reason,
            instructions=instructions,
            expected_response_type=expected_response_type,
            continue_label=continue_label,
            allow_continue=allow_continue,
            metadata=metadata or {},
        )

        loop = asyncio.get_running_loop()
        self._waiter = loop.create_future()
        assert self._session is not None
        self._session.pending_blocker = request
        self._session.resume_instructions = instructions
        self._session.status = "waiting_for_user"
        self._session.touch()
        self._emit_status()
        if self._on_help_requested:
            self._on_help_requested(request, self._session)

        try:
            response = await self._waiter
        finally:
            if self._session:
                self._session.pending_blocker = None
                self._session.resume_instructions = ""
                self._session.status = "running"
                self._session.touch()
                self._emit_status()
            self._waiter = None
        return response

    def resume(self, response: str = "continue") -> bool:
        if not self._waiter or self._waiter.done():
            return False
        self._waiter.set_result(response)
        return True

    def fail(self, summary: str) -> None:
        if not self._session:
            return
        self._session.status = "failed"
        self._session.result_summary = summary
        self._session.touch()
        self._emit_status()

    def complete(self, summary: str) -> None:
        if not self._session:
            return
        self._session.status = "completed"
        self._session.result_summary = summary
        self._session.touch()
        self._emit_status()

    def _emit_status(self) -> None:
        if self._session and self._on_status_changed:
            self._on_status_changed(self._session.status, self._session)
