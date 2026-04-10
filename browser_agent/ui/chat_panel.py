"""Chat panel — header with action icons, message list, overlay panels for history/skills."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from browser_agent.ui.animated_input import AnimatedChatInput
from browser_agent.ui.chat_message_widget import ChatMessageWidget
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


class _HeaderButton(QLabel):
    """Clickable icon button for the chat header."""
    clicked = pyqtSignal()

    def __init__(self, icon: str, tooltip: str, parent=None):
        super().__init__(icon, parent)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"QLabel {{ color: {DARK_TEXT_MUTED}; font-size: 16px;"
            f" background: transparent; border-radius: 8px; }}"
            f"QLabel:hover {{ color: {DARK_TEXT}; background: rgba(255,255,255,0.06); }}"
        )

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

        header_layout.addSpacing(SPACE_2)

        # Action buttons: New Chat | History | Skills
        self._new_btn = _HeaderButton("+", "New Chat")
        self._new_btn.setStyleSheet(
            f"QLabel {{ color: {ACCENT_PRIMARY}; font-size: 20px; font-weight: 500;"
            f" background: transparent; border-radius: 8px; }}"
            f"QLabel:hover {{ background: rgba(59,130,246,0.15); }}"
        )
        self._new_btn.clicked.connect(self.new_thread_requested.emit)
        header_layout.addWidget(self._new_btn)

        self._history_btn = _HeaderButton("\u2263", "Chat History") # Strict equivalent (≡)
        self._history_btn.clicked.connect(self.history_toggled.emit)
        header_layout.addWidget(self._history_btn)

        self._skills_btn = _HeaderButton("\u22c6", "Skills") # Star operator (⋆)
        self._skills_btn.clicked.connect(self.skills_toggled.emit)
        header_layout.addWidget(self._skills_btn)

        self._rules_btn = _HeaderButton("\u23f0", "Rules") # Alarm clock
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
        default = (
            f"QLabel {{ color: {DARK_TEXT_MUTED}; font-size: 16px;"
            f" background: transparent; border-radius: 8px; }}"
            f"QLabel:hover {{ color: {DARK_TEXT}; background: rgba(255,255,255,0.06); }}"
        )
        self._history_btn.setStyleSheet(default)
        self._skills_btn.setStyleSheet(default)
        self._rules_btn.setStyleSheet(default)

    def show_chat(self) -> None:
        self._stack.setCurrentIndex(0)
        self._reset_overlay_buttons()

    def toggle_history(self) -> None:
        if self._stack.currentIndex() == 1:
            self.show_chat()
        else:
            self._reset_overlay_buttons()
            self._stack.setCurrentIndex(1)
            self._history_btn.setStyleSheet(
                f"QLabel {{ color: {ACCENT_PRIMARY}; font-size: 16px;"
                f" background: rgba(108,92,231,0.12); border-radius: 8px; }}"
            )

    def toggle_skills(self) -> None:
        if self._stack.currentIndex() == 2:
            self.show_chat()
        else:
            self._reset_overlay_buttons()
            self._stack.setCurrentIndex(2)
            self._skills_btn.setStyleSheet(
                f"QLabel {{ color: {ACCENT_SECONDARY}; font-size: 16px;"
                f" background: rgba(168,85,247,0.12); border-radius: 8px; }}"
            )

    def toggle_rules(self) -> None:
        if self._stack.currentIndex() == 3:
            self.show_chat()
        else:
            self._reset_overlay_buttons()
            self._stack.setCurrentIndex(3)
            self._rules_btn.setStyleSheet(
                f"QLabel {{ color: {WARNING}; font-size: 16px;"
                f" background: rgba(245,158,11,0.12); border-radius: 8px; }}"
            )

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
        self._add_widget(ChatMessageWidget("user", text))

    def append_assistant_message(self, text: str) -> None:
        self._streaming_widget = None
        self._tool_group = None
        self._add_widget(ChatMessageWidget("assistant", text))

    def append_tool_message(self, tool_name: str, result: str) -> None:
        if self._tool_group is None:
            self._tool_group = ToolCallGroup()
            self._add_widget(self._tool_group)
        self._tool_group.add_tool_call(tool_name, result)
        self._scroll_to_bottom()

    def append_thinking(self, text: str) -> None:
        self._add_widget(ChatMessageWidget("thinking", text))

    def append_error(self, text: str) -> None:
        self._add_widget(ChatMessageWidget("error", text))

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
            self._show_typing_indicator()
            self._status_dot.setStyleSheet(label_style(ACCENT_PRIMARY, 18))
            self._status_text.setText("Thinking...")
            self._status_text.setStyleSheet(label_style(ACCENT_PRIMARY, FONT_SM))
        else:
            self._remove_typing_indicator()
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
