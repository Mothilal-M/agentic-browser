"""Tests for human-in-the-loop task collaboration."""

import asyncio

import pytest

from browser_agent.agent.collaboration import CollaborationManager


@pytest.mark.anyio
async def test_request_help_waits_then_resumes():
    manager = CollaborationManager()
    manager.start_task("Apply for a job")

    async def wait_for_help():
        return await manager.request_help(
            "captcha_required",
            "CAPTCHA detected.",
            "Solve it and continue.",
            expected_response_type="manual",
        )

    task = asyncio.create_task(wait_for_help())
    await asyncio.sleep(0)

    assert manager.is_waiting is True
    assert manager.session is not None
    assert manager.session.pending_blocker is not None
    assert manager.session.pending_blocker.blocker_type == "captcha_required"

    manager.resume("done")
    result = await task

    assert result == "done"
    assert manager.is_waiting is False
    assert manager.session is not None
    assert manager.session.status == "running"


def test_complete_marks_session_complete():
    manager = CollaborationManager()
    session = manager.start_task("Change site to dark mode")
    manager.complete("Dark mode enabled.")

    assert session.status == "completed"
    assert session.result_summary == "Dark mode enabled."
