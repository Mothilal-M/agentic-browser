"""Application entry — sets up event loop, creates window, wires agent + storage, runs."""

import logging
from pathlib import Path

from dotenv import load_dotenv
from qasync import asyncSlot

from browser_agent.agent.error_recovery import ErrorRecovery
from browser_agent.agent.graph import build_agent_graph
from browser_agent.agent.guardrails import Guardrails
from browser_agent.agent.vision import VisionDetector
from browser_agent.recording.exporter import export_html, export_json
from browser_agent.recording.recorder import SessionRecorder
from browser_agent.bridge.agent_controller import AgentController
from browser_agent.bridge.async_bridge import create_app_and_loop
from browser_agent.browser.engine import BrowserEngine
from browser_agent.browser.page_controller import PageController
from browser_agent.browser.screenshot import ScreenshotCapture
from browser_agent.config import AppConfig
from browser_agent.skills.player import SkillPlayer
from browser_agent.skills.store import SkillStore
from browser_agent.storage.conversation_db import ConversationDB
from browser_agent.storage.memory_db import MemoryDB
from browser_agent.storage.user_profile import UserProfile
from browser_agent.voice.engine import VoiceEngine
from browser_agent.multiagent.coordinator import MultiAgentCoordinator
from browser_agent.predictive.pattern_tracker import PatternTracker
from browser_agent.autonomous.rules_engine import RulesEngine
from browser_agent.ui.main_window import MainWindow
from browser_agent.ui.rules_panel import RulesPanel
from browser_agent.ui.skills_panel import SkillsPanel
from browser_agent.ui.thread_selector import ThreadSelector

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _load_fonts() -> None:
    """Load custom Inter + JetBrains Mono fonts from bundled .ttf files."""
    from PyQt6.QtGui import QFontDatabase

    fonts_dir = Path(__file__).parent / "ui" / "fonts"
    if not fonts_dir.exists():
        return
    for ttf in fonts_dir.glob("*.ttf"):
        font_id = QFontDatabase.addApplicationFont(str(ttf))
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            logging.info("Loaded font: %s → %s", ttf.name, families)
        else:
            logging.warning("Failed to load font: %s", ttf.name)


def main() -> int:
    load_dotenv()

    app, loop = create_app_and_loop()

    # Load custom fonts before any widgets are created
    _load_fonts()

    config = AppConfig()

    # Storage layer
    storage_dir = Path(config.persistent_storage_path)
    conv_db = ConversationDB(storage_dir / "conversations.db")
    memory_db = MemoryDB(storage_dir / "memory.db")
    skill_store = SkillStore(storage_dir / "skills.db")
    profile = UserProfile(storage_dir / "profile.db")

    # Browser layer
    engine = BrowserEngine(config)
    page_controller = PageController(engine)
    screenshot = ScreenshotCapture(config)
    skill_player = SkillPlayer(page_controller, engine)
    vision = VisionDetector(page_controller, screenshot, engine)
    recovery = ErrorRecovery(page_controller)
    guardrails = Guardrails(sensitivity=config.guardrail_sensitivity)
    recorder = SessionRecorder(screenshot, engine)

    # Phase 7: Future systems
    voice = VoiceEngine()
    voice.setup_stt_page(engine)
    pattern_tracker = PatternTracker(storage_dir / "patterns.db")
    rules_engine = RulesEngine(storage_dir / "rules.db")

    # Multi-agent coordinator (created early, controller set after)
    multi_agent = MultiAgentCoordinator()

    # Agent layer (with memory + skills + intelligence)
    compiled_graph = build_agent_graph(
        config, page_controller, screenshot, engine,
        memory_db, skill_store, skill_player, profile,
        vision, recovery, multi_agent,
    )

    # Bridge layer (with persistence)
    controller = AgentController(
        compiled_graph, config, screenshot, page_controller, engine,
        conversation_db=conv_db, memory_db=memory_db, user_profile=profile,
        pattern_tracker=pattern_tracker,
        guardrails=guardrails, session_recorder=recorder,
    )

    # UI
    window = MainWindow(config, engine)

    # Embed history, skills, and rules inside chat panel (overlay pages)
    thread_selector = ThreadSelector()
    skills_panel = SkillsPanel()
    rules_panel = RulesPanel()
    window.chat_panel.set_history_widget(thread_selector)
    window.chat_panel.set_skills_widget(skills_panel)
    window.chat_panel.set_rules_widget(rules_panel)

    # Wire header buttons
    window.chat_panel.history_toggled.connect(window.chat_panel.toggle_history)
    window.chat_panel.skills_toggled.connect(window.chat_panel.toggle_skills)
    window.chat_panel.rules_toggled.connect(window.chat_panel.toggle_rules)

    window.show()

    # --- Wire chat → agent ---
    @asyncSlot(str)
    async def on_message(text: str) -> None:
        await controller.handle_user_message(text)

    window.chat_panel.message_submitted.connect(on_message)
    window.chat_panel.stop_requested.connect(controller.stop)

    # --- Wire agent → chat ---
    signals = controller.signals
    signals.assistant_message_complete.connect(window.chat_panel.append_assistant_message)
    signals.assistant_text.connect(window.chat_panel.update_streaming_message)
    signals.tool_call_started.connect(
        lambda name, args: window.chat_panel.append_tool_message(name, f"args: {args}")
    )
    signals.tool_result_received.connect(
        lambda name, result: window.chat_panel.append_tool_message(f"{name} result", result)
    )
    signals.thinking_update.connect(window.chat_panel.append_thinking)
    signals.error_occurred.connect(window.chat_panel.append_error)
    signals.agent_busy.connect(window.chat_panel.set_busy)

    # --- Wire thread selector ---
    def refresh_threads():
        threads = conv_db.list_threads()
        thread_selector.set_threads(threads, controller.thread_id)

    def on_thread_selected(thread_id: str):
        messages = controller.switch_thread(thread_id)
        window.chat_panel.clear_chat()
        window.chat_panel.show_chat()  # switch back to chat view
        for msg in messages:
            if msg.role == "user":
                window.chat_panel.append_user_message(msg.content)
            elif msg.role == "assistant":
                window.chat_panel.append_assistant_message(msg.content)
            elif msg.role == "tool":
                window.chat_panel.append_tool_message("tool", msg.content)
        refresh_threads()

    def on_new_thread():
        controller.new_thread()
        window.chat_panel.clear_chat()
        window.chat_panel.show_chat()  # switch back to chat view
        refresh_threads()

    def on_thread_deleted(thread_id: str):
        conv_db.delete_thread(thread_id)
        if thread_id == controller.thread_id:
            on_new_thread()
        else:
            refresh_threads()

    thread_selector.thread_selected.connect(on_thread_selected)
    thread_selector.new_thread_requested.connect(on_new_thread)
    thread_selector.thread_deleted.connect(on_thread_deleted)
    window.chat_panel.new_thread_requested.connect(on_new_thread)

    # --- Wire skills panel ---
    def refresh_skills():
        skills_panel.set_skills(skill_store.list_all())

    @asyncSlot(str)
    async def on_skill_play(skill_name: str):
        window.chat_panel.append_user_message(f"Run skill: {skill_name}")
        window.chat_panel.set_busy(True)
        skill = skill_store.get_by_name(skill_name)
        if not skill:
            window.chat_panel.append_error(f"Skill '{skill_name}' not found.")
            window.chat_panel.set_busy(False)
            return
        skill_store.increment_run_count(skill.skill_id)
        success, summary = await skill_player.play(
            skill,
            on_step_start=lambda i, s: window.chat_panel.append_tool_message(
                s.tool_name, f"Step {i + 1}: {s.description or str(s.args)}"
            ),
        )
        if success:
            window.chat_panel.append_assistant_message(f"Skill **{skill_name}** completed: {summary}")
        else:
            window.chat_panel.append_error(f"Skill failed: {summary}")
        window.chat_panel.set_busy(False)
        refresh_skills()

    def on_skill_deleted(skill_id: str):
        skill_store.delete(skill_id)
        refresh_skills()

    skills_panel.skill_play_requested.connect(on_skill_play)
    skills_panel.skill_deleted.connect(on_skill_deleted)

    # Refresh thread list + skills after each agent response
    signals.assistant_message_complete.connect(lambda _: refresh_threads())
    signals.assistant_message_complete.connect(lambda _: refresh_skills())

    # --- Wire session recording menu ---
    _last_recording = [None]  # mutable container for closure

    def on_start_recording():
        recorder.start("Session Recording")
        window._record_action.setEnabled(False)
        window._stop_record_action.setEnabled(True)
        window._export_html_action.setEnabled(False)
        window._export_json_action.setEnabled(False)
        window.statusBar().showMessage("\u23fa Recording session...", 0)
        window.chat_panel.append_tool_message("Recording", "Session recording started")

    def on_stop_recording():
        rec = recorder.stop()
        _last_recording[0] = rec
        window._record_action.setEnabled(True)
        window._stop_record_action.setEnabled(False)
        window._export_html_action.setEnabled(rec is not None)
        window._export_json_action.setEnabled(rec is not None)
        window.statusBar().showMessage("Recording stopped", 3000)
        if rec:
            window.chat_panel.append_tool_message(
                "Recording", f"Stopped. {rec.event_count} events, {rec.screenshot_count} screenshots"
            )

    def on_export_html():
        rec = _last_recording[0]
        if not rec:
            return
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            window, "Export HTML Report", f"{rec.title}.html", "HTML Files (*.html)"
        )
        if path:
            export_html(rec, path)
            window.statusBar().showMessage(f"Exported: {path}", 5000)

    def on_export_json():
        rec = _last_recording[0]
        if not rec:
            return
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            window, "Export JSON", f"{rec.title}.json", "JSON Files (*.json)"
        )
        if path:
            export_json(rec, path)
            window.statusBar().showMessage(f"Exported: {path}", 5000)

    def on_import_skill():
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            window, "Import Skill", "", "JSON Files (*.json)"
        )
        if path:
            skill = skill_store.import_skill(path)
            if skill:
                window.statusBar().showMessage(f"Imported skill: {skill.name}", 5000)
                refresh_skills()
            else:
                window.statusBar().showMessage("Failed to import skill", 5000)

    def on_export_all_skills():
        from PyQt6.QtWidgets import QFileDialog
        dir_path = QFileDialog.getExistingDirectory(window, "Export Skills Folder")
        if dir_path:
            paths = skill_store.export_all(dir_path)
            window.statusBar().showMessage(f"Exported {len(paths)} skills to {dir_path}", 5000)

    window._record_action.triggered.connect(on_start_recording)
    window._stop_record_action.triggered.connect(on_stop_recording)
    window._export_html_action.triggered.connect(on_export_html)
    window._export_json_action.triggered.connect(on_export_json)
    window._import_skill_action.triggered.connect(on_import_skill)
    window._export_skills_action.triggered.connect(on_export_all_skills)

    # --- Wire voice control ---
    @asyncSlot()
    async def on_voice_btn():
        if voice.is_listening:
            voice.stop_listening()
        else:
            await voice.start_listening()

    def on_transcript(text: str):
        # Feed voice transcript into chat as if user typed it
        window.chat_panel._input._edit.setPlainText(text)
        window.chat_panel._on_send()

    voice.transcript_ready.connect(on_transcript)
    voice.listening_changed.connect(
        lambda active: window.statusBar().showMessage(
            "\U0001f3a4 Listening..." if active else "", 0 if active else 3000
        )
    )

    # --- Wire rules panel ---
    def refresh_rules():
        rules_panel.set_rules(rules_engine.list_rules())

    def on_rule_added(name: str, trigger: str, action_prompt: str):
        rules_engine.add_rule(name, trigger, action_prompt)
        refresh_rules()

    def on_rule_toggled(rule_id: str, enabled: bool):
        rules_engine.toggle_rule(rule_id, enabled)
        refresh_rules()

    def on_rule_deleted(rule_id: str):
        rules_engine.delete_rule(rule_id)
        refresh_rules()

    rules_panel.rule_added.connect(on_rule_added)
    rules_panel.rule_toggled.connect(on_rule_toggled)
    rules_panel.rule_deleted.connect(on_rule_deleted)

    # --- Wire pattern tracking (learn from browsing) ---
    def on_page_visit(url: str, title: str):
        pattern_tracker.track_visit(url, title)

    window.browser_panel.page_loaded.connect(on_page_visit)

    # --- Wire multi-agent coordinator ---
    multi_agent.set_controller(controller)

    # --- Wire autonomous rules engine ---
    rules_engine.start(controller)

    # Initial load
    refresh_threads()
    refresh_skills()
    refresh_rules()

    with loop:
        loop.run_forever()

    # Cleanup
    rules_engine.stop()
    conv_db.close()
    memory_db.close()
    skill_store.close()
    profile.close()
    pattern_tracker.close()
    rules_engine.close()

    return 0


    # (removed _add_sidebar_panels — history/skills now inside chat panel)
