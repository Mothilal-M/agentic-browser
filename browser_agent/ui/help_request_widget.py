"""Interactive help-request card shown when the agent needs user input."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    DARK_TEXT,
    DARK_TEXT_MUTED,
    FONT_SM,
    FONT_XS,
    WARNING,
    slide_fade_in,
)


class HelpRequestWidget(QFrame):
    continue_clicked = pyqtSignal()

    def __init__(self, payload: dict, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("msg_help")
        self.setStyleSheet(
            f"QFrame#msg_help {{"
            f"background: rgba(245,158,11,0.08);"
            f"border: 1px solid rgba(245,158,11,0.24);"
            f"border-radius: 14px;"
            f"padding: 12px;"
            f"}}"
            f"QPushButton#help_continue {{"
            f"background: rgba(59,130,246,0.18);"
            f"color: {ACCENT_PRIMARY};"
            f"border: 1px solid rgba(59,130,246,0.35);"
            f"border-radius: 10px;"
            f"padding: 8px 14px;"
            f"font-weight: 600;"
            f"}}"
            f"QPushButton#help_continue:hover {{"
            f"background: rgba(59,130,246,0.28);"
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Needs Your Help")
        title.setStyleSheet(f"color: {WARNING}; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()

        ts = QLabel(datetime.now().strftime("%H:%M"))
        ts.setStyleSheet(f"color: {DARK_TEXT_MUTED}; font-size: {FONT_XS}px;")
        header.addWidget(ts)
        layout.addLayout(header)

        blocker = payload.get("blocker_type", "").replace("_", " ").title()
        if blocker:
            badge = QLabel(blocker)
            badge.setStyleSheet(
                f"color: {ACCENT_PRIMARY}; font-size: {FONT_XS}px; "
                f"background: rgba(59,130,246,0.12); border-radius: 8px; padding: 4px 8px;"
            )
            layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)

        reason = QLabel(payload.get("reason", "The agent is blocked."))
        reason.setWordWrap(True)
        reason.setStyleSheet(f"color: {DARK_TEXT};")
        layout.addWidget(reason)

        instructions = QLabel(payload.get("instructions", ""))
        instructions.setWordWrap(True)
        instructions.setStyleSheet(f"color: {DARK_TEXT_MUTED}; font-size: {FONT_SM}px;")
        layout.addWidget(instructions)

        expected = payload.get("expected_response_type", "text")
        helper_text = (
            "Use Continue after you finish in the browser."
            if payload.get("allow_continue", False)
            else "Reply in chat with the requested details."
        )
        hint = QLabel(f"Expected input: {expected}. {helper_text}")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {DARK_TEXT_MUTED}; font-size: {FONT_XS}px;")
        layout.addWidget(hint)

        if payload.get("allow_continue", False):
            button = QPushButton(payload.get("continue_label", "Continue"))
            button.setObjectName("help_continue")
            button.clicked.connect(self.continue_clicked.emit)
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)

        self._anim = slide_fade_in(self, duration=260)
