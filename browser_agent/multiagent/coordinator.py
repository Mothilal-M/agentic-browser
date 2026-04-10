"""Multi-agent coordinator — dispatches tasks to specialist agents.

Runs a coordinator that breaks complex requests into sub-tasks and
assigns them to specialist agents (Research, Form-Fill, Monitor).
Each specialist has a focused system prompt and subset of tools.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser_agent.bridge.agent_controller import AgentController

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    COORDINATOR = "coordinator"
    RESEARCHER = "researcher"
    FORM_FILLER = "form_filler"
    MONITOR = "monitor"
    NAVIGATOR = "navigator"


@dataclass
class SubTask:
    description: str
    role: AgentRole
    status: str = "pending"  # pending, running, done, failed
    result: str = ""


@dataclass
class TaskPlan:
    goal: str
    subtasks: list[SubTask] = field(default_factory=list)


# Specialist prompts — injected before the base system prompt
SPECIALIST_PROMPTS = {
    AgentRole.RESEARCHER: (
        "You are a RESEARCH specialist. Your job is to find information across web pages. "
        "Use navigate_to, extract_text, get_page_elements, understand_page, and take_screenshot. "
        "Do NOT fill forms or click submit buttons — only gather information and report back."
    ),
    AgentRole.FORM_FILLER: (
        "You are a FORM-FILLING specialist. Your job is to fill out forms accurately. "
        "Use get_my_profile, autofill_form, type_text, click_element, and upload_file. "
        "Always use recall() first to check for saved user data before asking."
    ),
    AgentRole.MONITOR: (
        "You are a MONITORING specialist. Your job is to watch pages for changes. "
        "Use take_screenshot, extract_text, and understand_page to check current state. "
        "Compare with previous observations and report any differences."
    ),
    AgentRole.NAVIGATOR: (
        "You are a NAVIGATION specialist. Your job is to navigate to the right pages. "
        "Use navigate_to, click_element, smart_click, scroll_page to get to the target page. "
        "Report the final URL and page title when you arrive."
    ),
}


class MultiAgentCoordinator:
    """Breaks complex goals into sub-tasks and dispatches to specialists.

    The coordinator itself uses the main agent to plan, then executes
    each sub-task by prepending the specialist prompt to the user message.
    """

    def __init__(self, agent_controller: AgentController | None = None) -> None:
        self._controller = agent_controller
        self._current_plan: TaskPlan | None = None

    def set_controller(self, agent_controller: AgentController) -> None:
        self._controller = agent_controller

    @property
    def has_active_plan(self) -> bool:
        return self._current_plan is not None

    async def execute_plan(self, goal: str, subtasks: list[dict]) -> str:
        """Execute a multi-step plan with specialist agents.

        subtasks: [{"description": "...", "role": "researcher"}, ...]
        """
        plan = TaskPlan(goal=goal)
        for st in subtasks:
            role = AgentRole(st.get("role", "navigator"))
            plan.subtasks.append(SubTask(description=st["description"], role=role))

        self._current_plan = plan
        results = []

        for i, subtask in enumerate(plan.subtasks):
            subtask.status = "running"

            # Build specialist message
            specialist_prefix = SPECIALIST_PROMPTS.get(subtask.role, "")
            message = f"[{subtask.role.value.upper()} AGENT — Step {i + 1}/{len(plan.subtasks)}]\n"
            if specialist_prefix:
                message += f"Role: {specialist_prefix}\n\n"
            message += f"Task: {subtask.description}"

            # Execute through the main agent controller
            await self._controller.handle_user_message(message)

            # Wait for agent to finish (simple polling)
            for _ in range(300):  # max 5 minutes
                await asyncio.sleep(1)
                if self._controller._current_task is None or self._controller._current_task.done():
                    break

            subtask.status = "done"
            subtask.result = f"Step {i + 1} completed"
            results.append(f"Step {i + 1} ({subtask.role.value}): {subtask.description} — Done")

        self._current_plan = None
        return "\n".join(results)

    def create_plan_prompt(self, goal: str) -> str:
        """Generate a prompt asking the main agent to break a goal into sub-tasks."""
        return (
            f"I need you to create a multi-agent plan for this goal:\n\n"
            f'"{goal}"\n\n'
            f"Break this into ordered sub-tasks. For each sub-task, specify:\n"
            f"1. A clear description of what to do\n"
            f"2. Which specialist agent should handle it:\n"
            f"   - researcher: gather information from pages\n"
            f"   - form_filler: fill out forms and submit\n"
            f"   - monitor: watch for changes on a page\n"
            f"   - navigator: navigate to specific pages\n\n"
            f"Reply with ONLY a JSON array:\n"
            f'[{{"description": "...", "role": "researcher"}}, ...]\n'
        )
