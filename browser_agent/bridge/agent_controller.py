"""AgentController — orchestrates user message -> agent -> browser -> UI.

Persists all messages to ConversationDB and injects long-term memory.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject

from agentflow.core.state import Message

from browser_agent.bridge.signals import AgentSignals

if TYPE_CHECKING:
    from agentflow.core.graph.compiled_graph import CompiledGraph

    from browser_agent.browser.engine import BrowserEngine
    from browser_agent.browser.page_controller import PageController
    from browser_agent.browser.screenshot import ScreenshotCapture
    from browser_agent.config import AppConfig
    from browser_agent.storage.conversation_db import ConversationDB
    from browser_agent.storage.memory_db import MemoryDB
    from browser_agent.storage.user_profile import UserProfile

logger = logging.getLogger(__name__)


class AgentController(QObject):
    def __init__(
        self,
        compiled_graph: CompiledGraph,
        config: AppConfig,
        screenshot: ScreenshotCapture,
        page_controller: PageController,
        browser_engine: BrowserEngine,
        conversation_db: ConversationDB | None = None,
        memory_db: MemoryDB | None = None,
        user_profile: UserProfile | None = None,
        guardrails=None,
        session_recorder=None,
    ) -> None:
        super().__init__()
        self.signals = AgentSignals()
        self._graph = compiled_graph
        self._config = config
        self._user_profile = user_profile
        self._guardrails = guardrails
        self._recorder = session_recorder
        self._screenshot = screenshot
        self._page_controller = page_controller
        self._engine = browser_engine
        self._conv_db = conversation_db
        self._memory_db = memory_db
        self._thread_id = str(uuid.uuid4())
        self._current_task: asyncio.Task | None = None

        # Auto-create first thread
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

        # Persist user message + record
        if self._conv_db:
            self._conv_db.add_message(self._thread_id, "user", text)
        if self._recorder and self._recorder.is_recording:
            self._recorder.record_user_message(text)

        try:
            # Capture current browser state
            view = self._engine.current_view()
            screenshot_b64 = ""
            if view:
                screenshot_b64 = self._screenshot.capture(view)

            page_info = await self._page_controller.get_page_info()
            elements = await self._page_controller.get_interactive_elements()

            # Get memory + profile context
            memory_text = ""
            if self._memory_db:
                memory_text = self._memory_db.format_for_prompt(limit=20)

            profile_text = ""
            if self._user_profile:
                profile_text = self._user_profile.format_for_prompt()

            # Build messages
            messages = [Message.text_message(text, role="user")]
            if screenshot_b64:
                messages.append(
                    Message.image_message(
                        image_base64=screenshot_b64,
                        mime_type="image/jpeg",
                        text=f"Current page: {page_info.get('url', 'unknown')}",
                        role="user",
                    )
                )

            input_data = {
                "messages": messages,
                "current_url": page_info.get("url", ""),
                "page_title": page_info.get("title", ""),
                "interactive_elements": elements,
                "agent_memory": memory_text,
                "user_profile": profile_text,
            }

            config = {
                "thread_id": self._thread_id,
                "recursion_limit": self._config.recursion_limit,
            }

            result = await self._graph.ainvoke(input_data, config=config)

            # Process result messages
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

                                # Guardrails check
                                if self._guardrails:
                                    import json as _json
                                    try:
                                        tool_args = _json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                                    except _json.JSONDecodeError:
                                        tool_args = {}
                                    warning = self._guardrails.check(tool_name, tool_args)
                                    if warning:
                                        self.signals.error_occurred.emit(warning)

                                self.signals.tool_call_started.emit(
                                    tool_name, tool_args_str,
                                )
                                if self._recorder and self._recorder.is_recording:
                                    self._recorder.record_tool_call(tool_name, tool_args_str)
                        text_content = msg.text()
                        if text_content and not msg.tools_calls:
                            assistant_msgs.append(text_content)

                    elif msg.role == "tool":
                        tool_name = (msg.metadata or {}).get("function_name", "tool")
                        result_text = msg.text() or ""
                        tool_msgs.append((tool_name, result_text[:200]))

                # Emit tool results + record
                for tool_name, result_text in tool_msgs:
                    self.signals.tool_result_received.emit(tool_name, result_text)
                    if self._recorder and self._recorder.is_recording:
                        self._recorder.record_tool_result(tool_name, result_text)

                # Emit and persist final assistant response
                if assistant_msgs:
                    final_msg = assistant_msgs[-1]
                    self.signals.assistant_message_complete.emit(final_msg)
                    if self._recorder and self._recorder.is_recording:
                        self._recorder.record_assistant_message(final_msg)

                    if self._conv_db:
                        self._conv_db.add_message(
                            self._thread_id, "assistant", final_msg
                        )

                        # Auto-title the thread from first exchange
                        threads = self._conv_db.list_threads()
                        for t in threads:
                            if t.thread_id == self._thread_id and t.title == "New Chat":
                                title = final_msg[:50].split("\n")[0]
                                self._conv_db.update_thread_title(
                                    self._thread_id, title
                                )
                                break

        except asyncio.CancelledError:
            self.signals.error_occurred.emit("Agent stopped by user.")
        except Exception as e:
            logger.exception("Agent error")
            self.signals.error_occurred.emit(str(e))
        finally:
            self.signals.agent_busy.emit(False)

    def switch_thread(self, thread_id: str) -> list:
        """Switch to an existing thread. Returns stored messages."""
        self._thread_id = thread_id
        if self._conv_db:
            return self._conv_db.get_messages(thread_id)
        return []

    def new_thread(self) -> str:
        """Create a new conversation thread."""
        if self._conv_db:
            thread = self._conv_db.create_thread("New Chat")
            self._thread_id = thread.thread_id
            return thread.thread_id
        self._thread_id = str(uuid.uuid4())
        return self._thread_id

    def stop(self) -> None:
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
