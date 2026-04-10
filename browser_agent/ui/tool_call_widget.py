"""Collapsible tool call group — shows a compact summary, expands on click."""

from datetime import datetime

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    pyqtProperty,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from browser_agent.ui.markdown_renderer import md_to_html
from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    DARK_TEXT,
    DARK_TEXT_MUTED,
    DARK_TEXT_SECONDARY,
    SUCCESS,
    slide_fade_in,
)


class _ToolEntry(QWidget):
    """A single tool call + result row inside the collapsible group."""

    def __init__(self, tool_name: str, detail: str, parent=None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Status dot
        dot = QLabel("\u2713")
        dot.setStyleSheet(f"color: {SUCCESS}; font-size: 11px; font-weight: bold;")
        dot.setFixedWidth(14)
        layout.addWidget(dot)

        # Tool name
        name_label = QLabel(tool_name)
        name_label.setStyleSheet(
            f"color: {DARK_TEXT}; font-size: 12px; font-weight: 600;"
        )
        layout.addWidget(name_label)

        # Detail (truncated)
        if detail:
            short = detail[:80] + "\u2026" if len(detail) > 80 else detail
            detail_label = QLabel(short)
            detail_label.setStyleSheet(
                f"color: {DARK_TEXT_MUTED}; font-size: 11px;"
            )
            detail_label.setWordWrap(False)
            layout.addWidget(detail_label, 1)
        else:
            layout.addStretch()


class ToolCallGroup(QFrame):
    """Collapsible group that holds multiple tool calls.

    Shows a compact header like: "⚙ 3 actions performed  ▸"
    Clicking expands to show all tool call details.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("tool_group")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._expanded = False
        self._entries: list[tuple[str, str]] = []  # (tool_name, detail)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -- Header (always visible) --
        self._header = QWidget()
        self._header.setStyleSheet(
            "QWidget {"
            "  background: transparent;"
            "  border-radius: 10px;"
            "  padding: 0px;"
            "}"
        )
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(8)

        # Gear icon
        gear = QLabel("\u2699")
        gear.setStyleSheet(f"color: {SUCCESS}; font-size: 13px;")
        header_layout.addWidget(gear)

        # Summary text
        self._summary = QLabel("1 action performed")
        self._summary.setStyleSheet(
            f"color: {DARK_TEXT_SECONDARY}; font-size: 12px; font-weight: 500;"
        )
        header_layout.addWidget(self._summary)

        header_layout.addStretch()

        # Timestamp
        self._ts = QLabel(datetime.now().strftime("%H:%M"))
        self._ts.setStyleSheet(f"color: rgba(255,255,255,0.12); font-size: 10px;")
        header_layout.addWidget(self._ts)

        # Chevron
        self._chevron = QLabel("\u25b8")
        self._chevron.setStyleSheet(
            f"color: {DARK_TEXT_MUTED}; font-size: 12px;"
        )
        header_layout.addWidget(self._chevron)

        main_layout.addWidget(self._header)

        # -- Detail area (hidden by default) --
        self._detail_container = QWidget()
        self._detail_container.setObjectName("tool_detail_container")
        self._detail_layout = QVBoxLayout(self._detail_container)
        self._detail_layout.setContentsMargins(4, 0, 4, 8)
        self._detail_layout.setSpacing(2)
        self._detail_container.setMaximumHeight(0)

        main_layout.addWidget(self._detail_container)

        # Entrance animation
        self._anim = slide_fade_in(self, duration=300)

    def add_tool_call(self, tool_name: str, detail: str) -> None:
        """Add a tool call entry to this group."""
        self._entries.append((tool_name, detail))

        entry = _ToolEntry(tool_name, detail)
        entry.setStyleSheet(
            "QWidget {"
            "  background: rgba(255,255,255,0.02);"
            "  border-radius: 6px;"
            "  margin: 1px 0px;"
            "}"
        )
        self._detail_layout.addWidget(entry)

        # Update summary
        n = len(self._entries)
        names = ", ".join(t[0] for t in self._entries[-3:])
        if n > 3:
            names += f" +{n - 3} more"
        self._summary.setText(f"{n} action{'s' if n != 1 else ''} \u00b7 {names}")
        self._ts.setText(datetime.now().strftime("%H:%M"))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle()
        super().mousePressEvent(event)

    def _toggle(self) -> None:
        self._expanded = not self._expanded

        if self._expanded:
            self._chevron.setText("\u25be")  # down
            target_height = self._detail_container.sizeHint().height()
        else:
            self._chevron.setText("\u25b8")  # right
            target_height = 0

        anim = QPropertyAnimation(self._detail_container, b"maximumHeight")
        anim.setDuration(250)
        anim.setStartValue(self._detail_container.maximumHeight())
        anim.setEndValue(target_height)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        # Keep reference so it's not garbage collected
        self._expand_anim = anim
