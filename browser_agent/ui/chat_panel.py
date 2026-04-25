"""Chat panel — header with action icons, message list, overlay panels for history/skills."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from browser_agent.ui.animated_input import AnimatedChatInput
from browser_agent.ui.chat_message_widget import ChatMessageWidget
from browser_agent.ui.help_request_widget import HelpRequestWidget
from browser_agent.ui.tool_call_widget import ToolCallGroup
from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    ACCENT_SECONDARY,
    DARK_BG,
    DARK_TEXT,
    DARK_TEXT_MUTED,
    DARK_TEXT_SECONDARY,
    ERROR,
    FONT_BASE,
    FONT_LG,
    FONT_SM,
    FONT_XS,
    GLASS_BORDER,
    HEADER_H,
    RADIUS_LG,
    RADIUS_MD,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SUCCESS,
    WARNING,
    fade_in,
    label_style,
)


class _HeaderActionButton(QWidget):
    """Styled header button with icon + label, proper hit target, and hover effect."""
    clicked = pyqtSignal()

    def __init__(self, icon: str, label: str, tooltip: str,
                 accent: bool = False, parent=None):
        super().__init__(parent)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self._accent = accent
        self._hovered = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_2, SPACE_1, SPACE_3, SPACE_1)
        layout.setSpacing(SPACE_1)

        self._icon_label = QLabel(icon)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_label)

        self._text_label = QLabel(label)
        layout.addWidget(self._text_label)

        self._apply_default_style()

    def _apply_default_style(self) -> None:
        if self._accent:
            icon_color = ACCENT_PRIMARY
            text_color = ACCENT_PRIMARY
        else:
            icon_color = DARK_TEXT_MUTED
            text_color = DARK_TEXT_MUTED
        self._icon_label.setStyleSheet(
            f"color: {icon_color}; font-size: 15px; background: transparent;"
        )
        self._text_label.setStyleSheet(
            f"color: {text_color}; font-size: {FONT_XS}px; font-weight: 600;"
            f" letter-spacing: 0.3px; background: transparent;"
        )
        bg = "rgba(59,130,246,0.08)" if self._accent else "transparent"
        border = f"1px solid rgba(59,130,246,0.15)" if self._accent else "1px solid transparent"
        self.setStyleSheet(
            f"_HeaderActionButton {{ background: {bg}; border: {border};"
            f" border-radius: {RADIUS_MD}px; }}"
        )

    def set_active_style(self, color: str, bg: str) -> None:
        """Apply active/selected styling (e.g., when overlay is shown)."""
        self._icon_label.setStyleSheet(
            f"color: {color}; font-size: 15px; background: transparent;"
        )
        self._text_label.setStyleSheet(
            f"color: {color}; font-size: {FONT_XS}px; font-weight: 600;"
            f" letter-spacing: 0.3px; background: transparent;"
        )
        self.setStyleSheet(
            f"_HeaderActionButton {{ background: {bg};"
            f" border: 1px solid {color}40; border-radius: {RADIUS_MD}px; }}"
        )

    def enterEvent(self, event) -> None:
        self._hovered = True
        if self._accent:
            self.setStyleSheet(
                f"_HeaderActionButton {{ background: rgba(59,130,246,0.15);"
                f" border: 1px solid rgba(59,130,246,0.25); border-radius: {RADIUS_MD}px; }}"
            )
        else:
            self._icon_label.setStyleSheet(
                f"color: {DARK_TEXT}; font-size: 15px; background: transparent;"
            )
            self._text_label.setStyleSheet(
                f"color: {DARK_TEXT}; font-size: {FONT_XS}px; font-weight: 600;"
                f" letter-spacing: 0.3px; background: transparent;"
            )
            self.setStyleSheet(
                f"_HeaderActionButton {{ background: rgba(255,255,255,0.06);"
                f" border: 1px solid rgba(255,255,255,0.08); border-radius: {RADIUS_MD}px; }}"
            )
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._apply_default_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class TypingIndicator(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("typing_indicator")
        self.setFixedHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_4, SPACE_2, SPACE_4, SPACE_2)
        layout.setSpacing(SPACE_1)

        label = QLabel("Thinking")
        label.setStyleSheet(label_style(ACCENT_PRIMARY, FONT_SM, 500))
        layout.addWidget(label)

        self._dots: list[QLabel] = []
        for _ in range(3):
            dot = QLabel("\u2022")
            dot.setObjectName("typing_dot")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedWidth(8)
            self._dots.append(dot)
            layout.addWidget(dot)
        layout.addStretch()

        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(400)

    def _animate(self) -> None:
        for i, dot in enumerate(self._dots):
            if i == self._tick % 3:
                dot.setStyleSheet(label_style(ACCENT_PRIMARY, 20, 600))
            else:
                dot.setStyleSheet(label_style(DARK_TEXT_MUTED, 16, 400))
        self._tick += 1

    def stop(self) -> None:
        self._timer.stop()


class ChatPanel(QWidget):
    message_submitted = pyqtSignal(str)
    stop_requested = pyqtSignal()
    continue_requested = pyqtSignal()
    # Signals for history/skills actions (wired in app.py)
    new_thread_requested = pyqtSignal()
    history_toggled = pyqtSignal()
    skills_toggled = pyqtSignal()
    rules_toggled = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("chat_panel")
        self.setMinimumWidth(300)

        # ── Header with action icons ──
        header = QWidget()
        header.setObjectName("chat_header")
        header.setFixedHeight(HEADER_H)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(SPACE_4, 0, SPACE_3, 0)

        # Logo
        icon = QLabel("\u2b22") # sleek hexagon
        icon.setStyleSheet(label_style(ACCENT_PRIMARY, 20, 400))
        header_layout.addWidget(icon)

        title = QLabel("Agentic Browser")
        title.setStyleSheet(label_style(DARK_TEXT, FONT_LG, 600, spacing=0.5))
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Status
        self._status_dot = QLabel("\u2022")
        self._status_dot.setStyleSheet(label_style(DARK_TEXT_MUTED, 18))
        header_layout.addWidget(self._status_dot)

        self._status_text = QLabel("Ready")
        self._status_text.setStyleSheet(label_style(DARK_TEXT_MUTED, FONT_SM))
        header_layout.addWidget(self._status_text)

        # Separator between status and action buttons
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(24)
        sep.setStyleSheet(f"color: {GLASS_BORDER};")
        header_layout.addSpacing(SPACE_2)
        header_layout.addWidget(sep)
        header_layout.addSpacing(SPACE_1)

        # Action buttons: New Chat | History | Skills | Rules
        self._new_btn = _HeaderActionButton("+", "New", "New Chat (Ctrl+N)", accent=True)
        self._new_btn.clicked.connect(self.new_thread_requested.emit)
        header_layout.addWidget(self._new_btn)

        header_layout.addSpacing(2)

        self._history_btn = _HeaderActionButton("\u2263", "History", "Chat History")
        self._history_btn.clicked.connect(self.history_toggled.emit)
        header_layout.addWidget(self._history_btn)

        header_layout.addSpacing(2)

        self._skills_btn = _HeaderActionButton("\u22c6", "Skills", "Saved Skills")
        self._skills_btn.clicked.connect(self.skills_toggled.emit)
        header_layout.addWidget(self._skills_btn)

        header_layout.addSpacing(2)

        self._rules_btn = _HeaderActionButton("\u23f0", "Rules", "Automation Rules")
        self._rules_btn.clicked.connect(self.rules_toggled.emit)
        header_layout.addWidget(self._rules_btn)

        # ── Stacked: chat view / history overlay / skills overlay ──
        self._stack = QStackedWidget()

        # Page 0: Chat messages
        chat_page = QWidget()
        chat_layout = QVBoxLayout(chat_page)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("chat_scroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._messages_container = QWidget()
        self._messages_container.setObjectName("messages_container")
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(SPACE_2, SPACE_3, SPACE_2, SPACE_3)
        self._messages_layout.setSpacing(SPACE_2)
        self._messages_layout.addStretch()
        self._scroll.setWidget(self._messages_container)

        chat_layout.addWidget(self._scroll, 1)
        self._stack.addWidget(chat_page)  # index 0

        # Page 1: History overlay (populated externally)
        self._history_page = QWidget()
        self._history_page.setObjectName("chat_panel")
        self._history_layout = QVBoxLayout(self._history_page)
        self._history_layout.setContentsMargins(0, 0, 0, 0)
        self._history_layout.setSpacing(0)
        self._stack.addWidget(self._history_page)  # index 1

        # Page 2: Skills overlay (populated externally)
        self._skills_page = QWidget()
        self._skills_page.setObjectName("chat_panel")
        self._skills_layout = QVBoxLayout(self._skills_page)
        self._skills_layout.setContentsMargins(0, 0, 0, 0)
        self._skills_layout.setSpacing(0)
        self._stack.addWidget(self._skills_page)  # index 2

        # Page 3: Rules overlay (populated externally)
        self._rules_page = QWidget()
        self._rules_page.setObjectName("chat_panel")
        self._rules_layout = QVBoxLayout(self._rules_page)
        self._rules_layout.setContentsMargins(0, 0, 0, 0)
        self._rules_layout.setSpacing(0)
        self._stack.addWidget(self._rules_page)  # index 3

        # ── Composer ──
        composer = QWidget()
        composer.setObjectName("composer_area")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        composer_layout.setSpacing(0)

        self._input = AnimatedChatInput()
        self._input.sendClicked.connect(self._on_send)
        self._input.stop_btn.clicked.connect(self.stop_requested.emit)
        self._input.edit.installEventFilter(self)
        composer_layout.addWidget(self._input)

        # ── Main layout ──
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(self._stack, 1)
        layout.addWidget(composer)

        self._streaming_widget: ChatMessageWidget | None = None
        self._typing_indicator: TypingIndicator | None = None
        self._tool_group: ToolCallGroup | None = None
        self._help_widget: HelpRequestWidget | None = None
        self._waiting_for_user = False

    # ── Overlay management ──

    def set_history_widget(self, widget: QWidget) -> None:
        """Set the history panel widget (ThreadSelector)."""
        self._history_layout.addWidget(widget)

    def set_skills_widget(self, widget: QWidget) -> None:
        """Set the skills panel widget (SkillsPanel)."""
        self._skills_layout.addWidget(widget)

    def set_rules_widget(self, widget: QWidget) -> None:
        """Set the rules panel widget (RulesPanel)."""
        self._rules_layout.addWidget(widget)

    def _reset_overlay_buttons(self) -> None:
        self._history_btn._apply_default_style()
        self._skills_btn._apply_default_style()
        self._rules_btn._apply_default_style()

    def show_chat(self) -> None:
        self._stack.setCurrentIndex(0)
        self._reset_overlay_buttons()

    def toggle_history(self) -> None:
        if self._stack.currentIndex() == 1:
            self.show_chat()
        else:
            self._reset_overlay_buttons()
            self._stack.setCurrentIndex(1)
            self._history_btn.set_active_style(ACCENT_PRIMARY, "rgba(59,130,246,0.12)")

    def toggle_skills(self) -> None:
        if self._stack.currentIndex() == 2:
            self.show_chat()
        else:
            self._reset_overlay_buttons()
            self._stack.setCurrentIndex(2)
            self._skills_btn.set_active_style(ACCENT_SECONDARY, "rgba(168,85,247,0.12)")

    def toggle_rules(self) -> None:
        if self._stack.currentIndex() == 3:
            self.show_chat()
        else:
            self._reset_overlay_buttons()
            self._stack.setCurrentIndex(3)
            self._rules_btn.set_active_style(WARNING, "rgba(245,158,11,0.12)")

    # ── Event filter (Enter to send) ──

    def eventFilter(self, obj, event) -> bool:
        if obj is self._input.edit and event.type() == event.Type.KeyPress:
            if (
                event.key() == Qt.Key.Key_Return
                and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            ):
                self._on_send()
                return True
        return super().eventFilter(obj, event)

    def _on_send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._input.clear()
        self.show_chat()  # switch back to chat if on history/skills
        self.append_user_message(text)
        self.message_submitted.emit(text)

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def _add_widget(self, widget) -> None:
        self._remove_typing_indicator()
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, widget)
        self._scroll_to_bottom()

    def _show_typing_indicator(self) -> None:
        if self._typing_indicator is not None:
            return
        self._typing_indicator = TypingIndicator()
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, self._typing_indicator)
        self._scroll_to_bottom()

    def _remove_typing_indicator(self) -> None:
        if self._typing_indicator is not None:
            self._typing_indicator.stop()
            self._messages_layout.removeWidget(self._typing_indicator)
            self._typing_indicator.deleteLater()
            self._typing_indicator = None

    def append_user_message(self, text: str) -> None:
        self._tool_group = None
        self._help_widget = None
        self._add_widget(ChatMessageWidget("user", text))

    def append_assistant_message(self, text: str) -> None:
        self._streaming_widget = None
        self._tool_group = None
        self._help_widget = None
        self._add_widget(ChatMessageWidget("assistant", text))

    def start_tool_call(self, tool_name: str, args_str: str = "") -> None:
        """Show a tool call in-progress with spinner."""
        if self._tool_group is None:
            self._tool_group = ToolCallGroup()
            self._add_widget(self._tool_group)
        self._tool_group.start_tool_call(tool_name, args_str)
        self._scroll_to_bottom()

    def complete_tool_call(self, tool_name: str, result: str = "") -> None:
        """Mark a tool call as complete with result."""
        if self._tool_group is None:
            self._tool_group = ToolCallGroup()
            self._add_widget(self._tool_group)
        self._tool_group.complete_tool_call(tool_name, result)
        self._scroll_to_bottom()

    def append_tool_message(self, tool_name: str, result: str) -> None:
        """Legacy fallback for tool messages."""
        if self._tool_group is None:
            self._tool_group = ToolCallGroup()
            self._add_widget(self._tool_group)
        self._tool_group.add_tool_call(tool_name, result)
        self._scroll_to_bottom()

    def append_thinking(self, text: str) -> None:
        self._add_widget(ChatMessageWidget("thinking", text))

    def append_error(self, text: str) -> None:
        self._add_widget(ChatMessageWidget("error", text))

    def append_help_request(self, payload: dict) -> None:
        self._streaming_widget = None
        self._tool_group = None
        self._help_widget = HelpRequestWidget(payload)
        self._help_widget.continue_clicked.connect(self.continue_requested.emit)
        self._add_widget(self._help_widget)
        self.set_waiting(True, payload)

    def update_streaming_message(self, delta: str) -> None:
        if self._streaming_widget is None:
            self._streaming_widget = ChatMessageWidget("assistant", "")
            self._add_widget(self._streaming_widget)
        self._streaming_widget.append_text(delta)
        self._scroll_to_bottom()

    def finish_streaming(self) -> None:
        self._streaming_widget = None

    def set_busy(self, busy: bool) -> None:
        self._input.set_busy(busy)
        if busy:
            self._waiting_for_user = False
            self._show_typing_indicator()
            self._status_dot.setStyleSheet(label_style(ACCENT_PRIMARY, 18))
            self._status_text.setText("Thinking...")
            self._status_text.setStyleSheet(label_style(ACCENT_PRIMARY, FONT_SM))
        else:
            self._remove_typing_indicator()
            if not self._waiting_for_user:
                self._status_dot.setStyleSheet(label_style(DARK_TEXT_MUTED, 18))
                self._status_text.setText("Ready")
                self._status_text.setStyleSheet(label_style(DARK_TEXT_MUTED, FONT_SM))

    def set_waiting(self, waiting: bool, payload: dict | None = None) -> None:
        self._waiting_for_user = waiting
        if waiting:
            self._remove_typing_indicator()
            self._input.set_busy(False)
            self._status_dot.setStyleSheet(label_style(WARNING, 18))
            blocker = (payload or {}).get("blocker_type", "Waiting").replace("_", " ").title()
            self._status_text.setText(f"Waiting: {blocker}")
            self._status_text.setStyleSheet(label_style(WARNING, FONT_SM))
        else:
            self._status_dot.setStyleSheet(label_style(DARK_TEXT_MUTED, 18))
            self._status_text.setText("Ready")
            self._status_text.setStyleSheet(label_style(DARK_TEXT_MUTED, FONT_SM))

    def clear_chat(self) -> None:
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._streaming_widget = None
        self._tool_group = None
        self._help_widget = None
        self._waiting_for_user = False
