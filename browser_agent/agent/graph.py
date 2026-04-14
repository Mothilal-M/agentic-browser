"""Build and compile the AgentFlow ReAct graph with browser tools.

Includes stuck-loop detection and per-task tool filtering.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import TYPE_CHECKING

from agentflow.core import Agent, StateGraph, ToolNode
from agentflow.core.state import AgentState
from agentflow.storage.checkpointer import InMemoryCheckpointer
from agentflow.utils.constants import END

from browser_agent.agent.prompts import BROWSER_AGENT_SYSTEM_PROMPT
from browser_agent.agent.state import BrowserAgentState
from browser_agent.agent.tools import create_browser_tools, filter_tools_by_tier
from browser_agent.browser.engine import BrowserEngine
from browser_agent.browser.page_controller import PageController
from browser_agent.browser.screenshot import ScreenshotCapture
from browser_agent.config import AppConfig

if TYPE_CHECKING:
    from browser_agent.agent.collaboration import CollaborationManager
    from browser_agent.agent.error_recovery import ErrorRecovery
    from browser_agent.agent.guardrails import Guardrails
    from browser_agent.agent.vision import VisionDetector
    from browser_agent.multiagent.coordinator import MultiAgentCoordinator
    from browser_agent.skills.player import SkillPlayer
    from browser_agent.skills.store import SkillStore
    from browser_agent.storage.memory_db import MemoryDB
    from browser_agent.storage.user_profile import UserProfile

# Module-level step history for stuck detection (keyed by thread_id)
_step_history: dict[str, list[tuple[str, str]]] = {}


def reset_step_history(thread_id: str) -> None:
    _step_history.pop(thread_id, None)


def _should_use_tools(state: AgentState) -> str:
    """Route decision with stuck-loop detection and done-tool handling."""
    if not state.context or len(state.context) == 0:
        return "TOOL"

    last_message = state.context[-1]

    if (
        hasattr(last_message, "tools_calls")
        and last_message.tools_calls
        and len(last_message.tools_calls) > 0
        and last_message.role == "assistant"
    ):
        # Check for "done" tool → immediate END
        for tc in last_message.tools_calls:
            fn = tc.get("function", {})
            if fn.get("name") == "done":
                return END

        # Stuck-loop detection: same (tool, args_hash) called 3+ times in last 8 calls
        history = _step_history.setdefault("current", [])
        for tc in last_message.tools_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            args_str = fn.get("arguments", "{}")
            args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
            history.append((name, args_hash))

        recent = history[-8:]
        counts = Counter(recent)
        for _, count in counts.items():
            if count >= 3:
                return END  # Stuck — force stop

        return "TOOL"

    if last_message.role == "tool":
        return "MAIN"

    return END


def build_agent_graph(
    config: AppConfig,
    page_controller: PageController,
    screenshot_capture: ScreenshotCapture,
    browser_engine: BrowserEngine,
    memory_db: MemoryDB | None = None,
    skill_store: SkillStore | None = None,
    skill_player: SkillPlayer | None = None,
    user_profile: UserProfile | None = None,
    vision_detector: VisionDetector | None = None,
    error_recovery: ErrorRecovery | None = None,
    multi_agent: MultiAgentCoordinator | None = None,
    guardrails: Guardrails | None = None,
    collaboration_manager: CollaborationManager | None = None,
    tool_tier: str = "standard",
):
    all_tools = create_browser_tools(
        page_controller, screenshot_capture, browser_engine,
        memory_db, skill_store, skill_player, user_profile,
        vision_detector, error_recovery, multi_agent,
        guardrails, collaboration_manager,
    )

    # Filter tools by task complexity tier
    tools = filter_tools_by_tier(all_tools, tool_tier)
    tool_node = ToolNode(tools)

    agent_kwargs = {}
    if config.base_url:
        agent_kwargs["base_url"] = config.base_url

    agent = Agent(
        model=config.model,
        provider=config.provider,
        system_prompt=BROWSER_AGENT_SYSTEM_PROMPT,
        tool_node=tool_node,
        trim_context=True,
        reasoning_config={"effort": config.reasoning_effort},
        **agent_kwargs,
    )

    graph = StateGraph()
    graph.add_node("MAIN", agent)
    graph.add_node("TOOL", tool_node)
    graph.add_conditional_edges("MAIN", _should_use_tools, {"TOOL": "TOOL", END: END})
    graph.add_edge("TOOL", "MAIN")
    graph.set_entry_point("MAIN")

    return graph.compile(checkpointer=InMemoryCheckpointer())
