"""Custom agent state for browser automation."""

from pydantic import Field

from agentflow.core.state import AgentState


class BrowserAgentState(AgentState):
    current_url: str = ""
    page_title: str = ""
    interactive_elements: str = ""
    agent_memory: str = ""
    user_profile: str = ""
    action_log: list[str] = Field(default_factory=list)
