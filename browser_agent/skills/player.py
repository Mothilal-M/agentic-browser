"""Skill player — replays a recorded workflow step by step with visual feedback."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable

from browser_agent.skills.models import Skill, SkillStep

if TYPE_CHECKING:
    from browser_agent.browser.engine import BrowserEngine
    from browser_agent.browser.page_controller import PageController

logger = logging.getLogger(__name__)


class SkillPlayer:
    """Replays a Skill by executing each step's tool call on the browser."""

    def __init__(
        self,
        page_controller: PageController,
        browser_engine: BrowserEngine,
    ) -> None:
        self._pc = page_controller
        self._engine = browser_engine
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def stop(self) -> None:
        self._running = False

    async def play(
        self,
        skill: Skill,
        on_step_start: Callable[[int, SkillStep], None] | None = None,
        on_step_done: Callable[[int, SkillStep, str], None] | None = None,
        on_error: Callable[[int, SkillStep, str], None] | None = None,
    ) -> tuple[bool, str]:
        """Execute all steps in sequence. Returns (success, summary)."""
        self._running = True
        completed = 0

        for i, step in enumerate(skill.steps):
            if not self._running:
                return False, f"Stopped after {completed}/{len(skill.steps)} steps."

            if on_step_start:
                on_step_start(i, step)

            try:
                result = await self._execute_step(step)
                completed += 1
                if on_step_done:
                    on_step_done(i, step, result)
            except Exception as e:
                msg = f"Step {i + 1} failed: {e}"
                logger.exception(msg)
                if on_error:
                    on_error(i, step, str(e))
                self._running = False
                return False, msg

            # Wait between steps
            if step.wait_after_ms > 0:
                await asyncio.sleep(step.wait_after_ms / 1000)

        self._running = False
        return True, f"Completed all {completed} steps."

    async def _execute_step(self, step: SkillStep) -> str:
        """Dispatch a single step to the appropriate page controller method."""
        name = step.tool_name
        args = step.args

        if name == "navigate_to":
            await self._pc.navigate(args["url"])
            info = await self._pc.get_page_info()
            return f"Navigated to {args['url']}. Title: {info.get('title', '')}"

        if name == "click_element":
            return await self._pc.click(args["selector"])

        if name == "type_text":
            return await self._pc.type_text(
                args["selector"], args["text"], args.get("clear_first", True)
            )

        if name == "scroll_page":
            return await self._pc.scroll(
                args.get("direction", "down"), args.get("pixels", 500)
            )

        if name == "press_key":
            return await self._pc.press_key(args["key"])

        if name == "extract_text":
            return await self._pc.extract_text(args.get("selector", "body"))

        if name == "wait_for_element":
            found = await self._pc.wait_for_selector(
                args["selector"], args.get("timeout", 5000)
            )
            return f"Element {'found' if found else 'not found'}: {args['selector']}"

        if name == "go_back":
            view = self._engine.current_view()
            if view:
                view.back()
                await asyncio.sleep(1)
            return "Went back"

        if name == "go_forward":
            view = self._engine.current_view()
            if view:
                view.forward()
                await asyncio.sleep(1)
            return "Went forward"

        return f"Unknown tool: {name}"
