"""Rules panel — manage automation rules with add/toggle/delete."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from browser_agent.autonomous.rules_engine import AutoRule
from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    ACCENT_SECONDARY,
    DARK_TEXT,
    DARK_TEXT_MUTED,
    DARK_TEXT_SECONDARY,
    ERROR,
    GLASS_BORDER,
    SUCCESS,
    WARNING,
    fade_in,
)


class _RuleCard(QFrame):
    """A single rule card with toggle and delete buttons."""

    toggle_clicked = pyqtSignal(str, bool)   # rule_id, new_enabled
    delete_clicked = pyqtSignal(str)         # rule_id

    def __init__(self, rule: AutoRule, parent=None):
        super().__init__(parent)
        self.setObjectName("rule_card")
        self._rule = rule

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header: name + toggle + delete
        header = QHBoxLayout()
        header.setSpacing(8)

        icon = QLabel("\u23f0")
        icon.setStyleSheet(f"color: {WARNING}; font-size: 14px;")
        icon.setFixedWidth(18)
        header.addWidget(icon)

        name = QLabel(rule.name)
        name.setStyleSheet(
            f"color: {DARK_TEXT}; font-size: 13px; font-weight: 600;"
        )
        header.addWidget(name, 1)

        toggle_btn = QPushButton("\u2713" if rule.enabled else "\u2717")
        toggle_btn.setFixedSize(28, 28)
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setToolTip("Enable/Disable")
        if rule.enabled:
            toggle_btn.setStyleSheet(
                f"QPushButton {{ background: rgba(16,185,129,0.12); color: {SUCCESS}; "
                f"border: 1px solid rgba(16,185,129,0.25); border-radius: 8px; "
                f"font-size: 12px; }}"
                f"QPushButton:hover {{ background: rgba(16,185,129,0.22); }}"
            )
        else:
            toggle_btn.setStyleSheet(
                f"QPushButton {{ background: rgba(100,116,139,0.12); color: {DARK_TEXT_MUTED}; "
                f"border: 1px solid rgba(100,116,139,0.25); border-radius: 8px; "
                f"font-size: 12px; }}"
                f"QPushButton:hover {{ background: rgba(100,116,139,0.22); }}"
            )
        toggle_btn.clicked.connect(lambda: self.toggle_clicked.emit(rule.rule_id, not rule.enabled))
        header.addWidget(toggle_btn)

        del_btn = QPushButton("\u2715")
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {DARK_TEXT_MUTED}; "
            f"border: none; border-radius: 8px; font-size: 11px; }}"
            f"QPushButton:hover {{ background: rgba(239,68,68,0.12); color: {ERROR}; }}"
        )
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(rule.rule_id))
        header.addWidget(del_btn)

        layout.addLayout(header)

        # Trigger + run info
        trigger_label = QLabel(f"\u25b8 {rule.trigger}")
        trigger_label.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(trigger_label)

        meta = QLabel(f"run {rule.run_count}x")
        meta.setStyleSheet(f"color: {DARK_TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(meta)


class RulesPanel(QWidget):
    """Panel showing automation rules with add/toggle/delete."""

    rule_added = pyqtSignal(str, str, str)    # name, trigger, action_prompt
    rule_toggled = pyqtSignal(str, bool)      # rule_id, enabled
    rule_deleted = pyqtSignal(str)            # rule_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rules_panel")

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(12, 8, 12, 4)

        icon = QLabel("\u23f0")
        icon.setStyleSheet(f"color: {WARNING}; font-size: 14px;")
        header_layout.addWidget(icon)

        title = QLabel("RULES")
        title.setStyleSheet(
            f"color: {DARK_TEXT_MUTED}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.2px;"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Add rule button
        add_btn = QPushButton("+ Add")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFixedHeight(24)
        add_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(59,130,246,0.12); color: {ACCENT_PRIMARY}; "
            f"border: 1px solid rgba(59,130,246,0.25); border-radius: 6px; "
            f"font-size: 10px; font-weight: 600; padding: 0 8px; }}"
            f"QPushButton:hover {{ background: rgba(59,130,246,0.22); }}"
        )
        add_btn.clicked.connect(self._toggle_add_form)
        header_layout.addWidget(add_btn)

        # Add form (hidden by default)
        self._add_form = QWidget()
        self._add_form.setVisible(False)
        form_layout = QVBoxLayout(self._add_form)
        form_layout.setContentsMargins(12, 8, 12, 8)
        form_layout.setSpacing(6)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Rule name")
        self._name_input.setStyleSheet(
            f"QLineEdit {{ background: rgba(255,255,255,0.04); color: {DARK_TEXT}; "
            f"border: 1px solid {GLASS_BORDER}; border-radius: 6px; "
            f"padding: 6px 8px; font-size: 12px; }}"
        )
        form_layout.addWidget(self._name_input)

        trigger_row = QHBoxLayout()
        trigger_row.setSpacing(6)
        self._trigger_type = QComboBox()
        self._trigger_type.addItems(["schedule:30m", "schedule:1h", "schedule:2h"])
        self._trigger_type.setEditable(True)
        self._trigger_type.setStyleSheet(
            f"QComboBox {{ background: rgba(255,255,255,0.04); color: {DARK_TEXT}; "
            f"border: 1px solid {GLASS_BORDER}; border-radius: 6px; "
            f"padding: 4px 8px; font-size: 11px; }}"
        )
        trigger_row.addWidget(self._trigger_type)
        form_layout.addLayout(trigger_row)

        self._action_input = QTextEdit()
        self._action_input.setPlaceholderText("What should the agent do?")
        self._action_input.setFixedHeight(60)
        self._action_input.setStyleSheet(
            f"QTextEdit {{ background: rgba(255,255,255,0.04); color: {DARK_TEXT}; "
            f"border: 1px solid {GLASS_BORDER}; border-radius: 6px; "
            f"padding: 6px 8px; font-size: 12px; }}"
        )
        form_layout.addWidget(self._action_input)

        save_btn = QPushButton("Save Rule")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(16,185,129,0.12); color: {SUCCESS}; "
            f"border: 1px solid rgba(16,185,129,0.25); border-radius: 6px; "
            f"font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: rgba(16,185,129,0.22); }}"
        )
        save_btn.clicked.connect(self._on_save)
        form_layout.addWidget(save_btn)

        # Scroll area for rules list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._list_container)

        # Empty state
        self._empty_label = QLabel("No rules yet.\nAdd a rule to automate browser tasks.")
        self._empty_label.setStyleSheet(
            f"color: {DARK_TEXT_MUTED}; font-size: 11px; padding: 20px;"
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header_layout)
        layout.addWidget(self._add_form)
        layout.addWidget(self._empty_label)
        layout.addWidget(self._scroll, 1)

    def _toggle_add_form(self) -> None:
        self._add_form.setVisible(not self._add_form.isVisible())

    def _on_save(self) -> None:
        name = self._name_input.text().strip()
        trigger = self._trigger_type.currentText().strip()
        action = self._action_input.toPlainText().strip()
        if not name or not trigger or not action:
            return
        self.rule_added.emit(name, trigger, action)
        self._name_input.clear()
        self._action_input.clear()
        self._add_form.setVisible(False)

    def set_rules(self, rules: list[AutoRule]) -> None:
        # Clear existing cards
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._empty_label.setVisible(len(rules) == 0)
        self._scroll.setVisible(len(rules) > 0)

        for rule in rules:
            card = _RuleCard(rule)
            card.toggle_clicked.connect(self.rule_toggled.emit)
            card.delete_clicked.connect(self.rule_deleted.emit)
            count = self._list_layout.count()
            self._list_layout.insertWidget(count - 1, card)
