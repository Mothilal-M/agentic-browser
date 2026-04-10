"""Skills panel — list saved workflows with one-click replay."""

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from browser_agent.skills.models import Skill
from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    ACCENT_SECONDARY,
    DARK_TEXT,
    DARK_TEXT_MUTED,
    DARK_TEXT_SECONDARY,
    ERROR,
    SUCCESS,
    fade_in,
)


class _SkillCard(QFrame):
    """A single skill card with play and delete buttons."""

    play_clicked = pyqtSignal(str)    # skill name
    delete_clicked = pyqtSignal(str)  # skill_id

    def __init__(self, skill: Skill, parent=None):
        super().__init__(parent)
        self.setObjectName("skill_card")
        self._skill = skill

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header: name + play button
        header = QHBoxLayout()
        header.setSpacing(8)

        icon = QLabel("\u26a1")
        icon.setStyleSheet(f"color: {ACCENT_SECONDARY}; font-size: 14px;")
        icon.setFixedWidth(18)
        header.addWidget(icon)

        name = QLabel(skill.name)
        name.setStyleSheet(
            f"color: {DARK_TEXT}; font-size: 13px; font-weight: 600;"
        )
        header.addWidget(name, 1)

        play_btn = QPushButton("\u25b6")
        play_btn.setFixedSize(28, 28)
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.setToolTip("Run this skill")
        play_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(16,185,129,0.12); color: {SUCCESS}; "
            f"border: 1px solid rgba(16,185,129,0.25); border-radius: 8px; "
            f"font-size: 12px; }}"
            f"QPushButton:hover {{ background: rgba(16,185,129,0.22); }}"
        )
        play_btn.clicked.connect(lambda: self.play_clicked.emit(skill.name))
        header.addWidget(play_btn)

        del_btn = QPushButton("\u2715")
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {DARK_TEXT_MUTED}; "
            f"border: none; border-radius: 8px; font-size: 11px; }}"
            f"QPushButton:hover {{ background: rgba(239,68,68,0.12); color: {ERROR}; }}"
        )
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(skill.skill_id))
        header.addWidget(del_btn)

        layout.addLayout(header)

        # Meta line
        steps = len(skill.steps)
        meta = QLabel(f"{steps} steps \u00b7 run {skill.run_count}x")
        meta.setStyleSheet(f"color: {DARK_TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(meta)


class SkillsPanel(QWidget):
    """Panel showing list of saved skills with play/delete."""

    skill_play_requested = pyqtSignal(str)   # skill name
    skill_deleted = pyqtSignal(str)          # skill_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("skills_panel")

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(12, 8, 12, 4)

        icon = QLabel("\u26a1")
        icon.setStyleSheet(f"color: {ACCENT_SECONDARY}; font-size: 14px;")
        header_layout.addWidget(icon)

        title = QLabel("SKILLS")
        title.setStyleSheet(
            f"color: {DARK_TEXT_MUTED}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.2px;"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Scroll area
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
        self._empty_label = QLabel("No skills yet.\nAsk the AI to save a workflow as a skill.")
        self._empty_label.setStyleSheet(
            f"color: {DARK_TEXT_MUTED}; font-size: 11px; padding: 20px;"
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header_layout)
        layout.addWidget(self._empty_label)
        layout.addWidget(self._scroll, 1)

    def set_skills(self, skills: list[Skill]) -> None:
        # Clear existing
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._empty_label.setVisible(len(skills) == 0)
        self._scroll.setVisible(len(skills) > 0)

        for skill in skills:
            card = _SkillCard(skill)
            card.play_clicked.connect(self.skill_play_requested.emit)
            card.delete_clicked.connect(self.skill_deleted.emit)
            count = self._list_layout.count()
            self._list_layout.insertWidget(count - 1, card)
