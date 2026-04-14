"""AgentController — orchestrates user message -> agent -> browser -> UI.

Per-task: classifies complexity, builds a filtered tool graph, sends smart context.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject

from agentflow.core.state import Message

from browser_agent.agent.graph import build_agent_graph, reset_step_history
from browser_agent.agent.tools import STEP_BUDGETS, classify_task_complexity
from browser_agent.bridge.signals import AgentSignals

if TYPE_CHECKING:
    from browser_agent.browser.engine import BrowserEngine
    from browser_agent.browser.page_controller import PageController
    from browser_agent.browser.screenshot import ScreenshotCapture
    from browser_agent.config import AppConfig
    from browser_agent.predictive.pattern_tracker import PatternTracker
    from browser_agent.storage.conversation_db import ConversationDB
    from browser_agent.storage.memory_db import MemoryDB
    from browser_agent.storage.user_profile import UserProfile

logger = logging.getLogger(__name__)


class AgentController(QObject):
    def __init__(
        self,
        config: AppConfig,
        screenshot: ScreenshotCapture,
        page_controller: PageController,
        browser_engine: BrowserEngine,
        conversation_db: ConversationDB | None = None,
        memory_db: MemoryDB | None = None,
        user_profile: UserProfile | None = None,
        pattern_tracker: PatternTracker | None = None,
        guardrails=None,
        session_recorder=None,
        # Components for per-task graph building
        vision_detector=None,
        error_recovery=None,
        skill_store=None,
        skill_player=None,
        multi_agent=None,
    ) -> None:
        super().__init__()
        self.signals = AgentSignals()
        self._config = config
        self._screenshot = screenshot
        self._page_controller = page_controller
        self._engine = browser_engine
        self._conv_db = conversation_db
        self._memory_db = memory_db
        self._user_profile = user_profile
        self._pattern_tracker = pattern_tracker
        self._guardrails = guardrails
        self._recorder = session_recorder

        # Store components for per-task graph building
        self._graph_components = {
            "config": config,
            "page_controller": page_controller,
            "screenshot_capture": screenshot,
            "browser_engine": browser_engine,
            "memory_db": memory_db,
            "skill_store": skill_store,
            "skill_player": skill_player,
            "user_profile": user_profile,
            "vision_detector": vision_detector,
            "error_recovery": error_recovery,
            "multi_agent": multi_agent,
        }

        self._thread_id = str(uuid.uuid4())
        self._current_task: asyncio.Task | None = None
        self._last_url = ""

        if self._conv_db:
            thread = self._conv_db.create_thread("New Chat")
            self._thread_id = thread.thread_id

    @property
    def thread_id(self) -> str:
        return self._thread_id

    async def handle_user_message(self, text: str) -> None:
        if self._current_task and not self._current_task.done():
            self.signals.error_occurred.emit("Agent is still processing. Please wait.")
            return
        self._current_task = asyncio.create_task(self._run(text))

    async def _run(self, text: str) -> None:
        self.signals.agent_busy.emit(True)

        if self._conv_db:
            self._conv_db.add_message(self._thread_id, "user", text)
        if self._recorder and self._recorder.is_recording:
            self._recorder.record_user_message(text)

        try:
            # ── Classify task and set budget ──
            tier = classify_task_complexity(text)
            step_budget = STEP_BUDGETS.get(tier, 15)
            logger.info("Task tier: %s, step budget: %d, tools tier: %s", tier, step_budget, tier)

            # ── Build per-task graph with filtered tools ──
            graph = build_agent_graph(**self._graph_components, tool_tier=tier)

            # Reset stuck-loop detection
            reset_step_history("current")

            # ── Smart context: screenshot only on first turn or URL change ──
            page_info = await self._page_controller.get_page_info()
            current_url = page_info.get("url", "")

            screenshot_b64 = ""
            if current_url != self._last_url:
                view = self._engine.current_view()
                if view:
                    screenshot_b64 = self._screenshot.capture(view)
                self._last_url = current_url

            # Compact memory (reduced from 20 to 10)
            memory_text = ""
            if self._memory_db:
                memory_text = self._memory_db.format_for_prompt(limit=10)

            # Short hint instead of 50-element dump
            elements_hint = f"Call snapshot() to see interactive elements with @ref IDs. [tier={tier}, budget={step_budget} steps]"

            # ── Build messages ──
            messages = [Message.text_message(text, role="user")]
            if screenshot_b64:
                messages.append(
                    Message.image_message(
                        image_base64=screenshot_b64,
                        mime_type="image/jpeg",
                        text=f"Current page: {current_url}",
                        role="user",
                    )
                )

            input_data = {
                "messages": messages,
                "current_url": current_url,
                "page_title": page_info.get("title", ""),
                "interactive_elements_hint": elements_hint,
                "agent_memory": memory_text,
            }

            config = {
                "thread_id": self._thread_id,
                "recursion_limit": step_budget,
            }

            # ── Execute ──
            result = await graph.ainvoke(input_data, config=config)

            # ── Process results ──
            if result and "messages" in result:
                assistant_msgs = []
                tool_msgs = []

                for msg in result["messages"]:
                    if msg.role == "assistant":
                        if msg.tools_calls:
                            for tc in msg.tools_calls:
                                fn = tc.get("function", {})
                                tool_name = fn.get("name", "unknown")
                                tool_args_str = fn.get("arguments", "{}")

                                if self._guardrails:
                                    import json as _json
                                    try:
                                        tool_args = _json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                                    except _json.JSONDecodeError:
                                        tool_args = {}
                                    warning = self._guardrails.check(tool_name, tool_args)
                                    if warning:
                                        self.signals.error_occurred.emit(warning)

                                self.signals.tool_call_started.emit(tool_name, tool_args_str)
                                if self._recorder and self._recorder.is_recording:
                                    self._recorder.record_tool_call(tool_name, tool_args_str)

                        text_content = msg.text()
                        if text_content and not msg.tools_calls:
                            assistant_msgs.append(text_content)

                    elif msg.role == "tool":
                        tool_name = (msg.metadata or {}).get("function_name", "tool")
                        result_text = msg.text() or ""
                        tool_msgs.append((tool_name, result_text[:200]))

                for tool_name, result_text in tool_msgs:
                    self.signals.tool_result_received.emit(tool_name, result_text)
                    if self._recorder and self._recorder.is_recording:
                        self._recorder.record_tool_result(tool_name, result_text)

                if assistant_msgs:
                    final_msg = assistant_msgs[-1]
                    self.signals.assistant_message_complete.emit(final_msg)
                    if self._recorder and self._recorder.is_recording:
                        self._recorder.record_assistant_message(final_msg)

                    if self._conv_db:
                        self._conv_db.add_message(self._thread_id, "assistant", final_msg)
                        threads = self._conv_db.list_threads()
                        for t in threads:
                            if t.thread_id == self._thread_id and t.title == "New Chat":
                                title = final_msg[:50].split("\n")[0]
                                self._conv_db.update_thread_title(self._thread_id, title)
                                break

        except asyncio.CancelledError:
            self.signals.error_occurred.emit("Agent stopped by user.")
        except Exception as e:
            logger.exception("Agent error")
            self.signals.error_occurred.emit(str(e))
        finally:
            self.signals.agent_busy.emit(False)

    def switch_thread(self, thread_id: str) -> list:
        self._thread_id = thread_id
        if self._conv_db:
            return self._conv_db.get_messages(thread_id)
        return []

    def new_thread(self) -> str:
        if self._conv_db:
            thread = self._conv_db.create_thread("New Chat")
            self._thread_id = thread.thread_id
            return thread.thread_id
        self._thread_id = str(uuid.uuid4())
        return self._thread_id

    def stop(self) -> None:
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
