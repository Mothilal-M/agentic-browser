"""Collapsible tool call group — shows a compact summary, expands on click."""

import json
import time
from datetime import datetime

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
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
    ERROR,
    SUCCESS,
    WARNING,
    slide_fade_in,
)


def _format_args(args_str: str) -> str:
    """Format tool arguments into a readable key=value string."""
    try:
        data = json.loads(args_str)
        if isinstance(data, dict):
            parts = []
            for k, v in data.items():
                val = str(v)
                if len(val) > 50:
                    val = val[:47] + "..."
                parts.append(f"{k}={val}")
            return ", ".join(parts)
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: truncate raw string
    if len(args_str) > 80:
        return args_str[:77] + "..."
    return args_str


class _ToolEntry(QWidget):
    """A single tool call row inside the collapsible group."""

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"

    _STATUS_ICONS = {
        "pending": ("\u25cb", WARNING),     # ○ yellow
        "success": ("\u2713", SUCCESS),     # ✓ green
        "error": ("\u2717", ERROR),         # ✗ red
    }

    _SPINNER_FRAMES = ["\u25dc", "\u25dd", "\u25de", "\u25df"]  # ◜◝◞◟

    def __init__(self, tool_name: str, args_str: str = "", parent=None) -> None:
        super().__init__(parent)
        self._status = self.STATUS_PENDING
        self._start_time = time.monotonic()
        self._end_time: float | None = None
        self._spin_tick = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Status icon (animated spinner when pending)
        self._status_icon = QLabel("\u25cb")
        self._status_icon.setStyleSheet(
            f"color: {WARNING}; font-size: 12px; font-weight: bold;"
        )
        self._status_icon.setFixedWidth(16)
        self._status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_icon)

        # Tool name
        name_label = QLabel(tool_name)
        name_label.setStyleSheet(
            f"color: {DARK_TEXT}; font-size: 12px; font-weight: 600;"
        )
        layout.addWidget(name_label)

        # Formatted arguments
        if args_str:
            formatted = _format_args(args_str)
            args_label = QLabel(formatted)
            args_label.setStyleSheet(
                f"color: {DARK_TEXT_MUTED}; font-size: 11px;"
            )
            args_label.setWordWrap(False)
            layout.addWidget(args_label, 1)
        else:
            layout.addStretch()

        # Duration label
        self._duration_label = QLabel("")
        self._duration_label.setStyleSheet(
            f"color: {DARK_TEXT_MUTED}; font-size: 10px;"
        )
        self._duration_label.setFixedWidth(45)
        self._duration_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._duration_label)

        # Spinner timer
        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._animate_spinner)
        self._spinner_timer.start(150)

    def _animate_spinner(self) -> None:
        if self._status != self.STATUS_PENDING:
            self._spinner_timer.stop()
            return
        self._spin_tick += 1
        frame = self._SPINNER_FRAMES[self._spin_tick % 4]
        self._status_icon.setText(frame)
        # Update elapsed time
        elapsed = time.monotonic() - self._start_time
        self._duration_label.setText(f"{elapsed:.1f}s")

    def mark_complete(self, success: bool = True) -> None:
        self._end_time = time.monotonic()
        self._status = self.STATUS_SUCCESS if success else self.STATUS_ERROR
        icon_char, color = self._STATUS_ICONS[self._status]
        self._status_icon.setText(icon_char)
        self._status_icon.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: bold;"
        )
        self._spinner_timer.stop()
        elapsed = self._end_time - self._start_time
        self._duration_label.setText(f"{elapsed:.1f}s")
        self._duration_label.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 500;"
        )


class ToolCallGroup(QFrame):
    """Collapsible group that holds multiple tool calls.

    Shows a compact header like: "⚙ 3 actions · click_element, type_text  ▸"
    Clicking expands to show all tool call details with status and duration.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("tool_group")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._expanded = False
        self._tool_entries: dict[str, _ToolEntry] = {}  # keyed by tool_name for lookup
        self._entry_list: list[str] = []  # ordered tool names
        self._pending_count = 0
        self._completed_count = 0
        self._error_count = 0

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
        self._gear = QLabel("\u2699")
        self._gear.setStyleSheet(f"color: {SUCCESS}; font-size: 13px;")
        header_layout.addWidget(self._gear)

        # Summary text
        self._summary = QLabel("Working...")
        self._summary.setStyleSheet(
            f"color: {DARK_TEXT_SECONDARY}; font-size: 12px; font-weight: 500;"
        )
        header_layout.addWidget(self._summary)

        header_layout.addStretch()

        # Status badge (shows pending/done counts)
        self._status_badge = QLabel("")
        self._status_badge.setStyleSheet(
            f"color: {WARNING}; font-size: 10px; font-weight: 600;"
            f" background: rgba(245,158,11,0.12); border-radius: 8px;"
            f" padding: 2px 6px;"
        )
        self._status_badge.setVisible(False)
        header_layout.addWidget(self._status_badge)

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

    def _update_summary(self) -> None:
        n = len(self._entry_list)
        names = ", ".join(self._entry_list[-3:])
        if n > 3:
            names += f" +{n - 3} more"
        self._summary.setText(f"{n} action{'s' if n != 1 else ''} \u00b7 {names}")
        self._ts.setText(datetime.now().strftime("%H:%M"))

        # Update status badge
        if self._pending_count > 0:
            self._status_badge.setText(f"\u25cb {self._pending_count} running")
            self._status_badge.setStyleSheet(
                f"color: {WARNING}; font-size: 10px; font-weight: 600;"
                f" background: rgba(245,158,11,0.12); border-radius: 8px;"
                f" padding: 2px 6px;"
            )
            self._status_badge.setVisible(True)
            self._gear.setStyleSheet(f"color: {WARNING}; font-size: 13px;")
        elif self._error_count > 0:
            self._status_badge.setText(f"\u2717 {self._error_count} failed")
            self._status_badge.setStyleSheet(
                f"color: {ERROR}; font-size: 10px; font-weight: 600;"
                f" background: rgba(239,68,68,0.12); border-radius: 8px;"
                f" padding: 2px 6px;"
            )
            self._status_badge.setVisible(True)
            self._gear.setStyleSheet(f"color: {ERROR}; font-size: 13px;")
        else:
            self._status_badge.setVisible(False)
            self._gear.setStyleSheet(f"color: {SUCCESS}; font-size: 13px;")

    def start_tool_call(self, tool_name: str, args_str: str = "") -> None:
        """Add a tool call entry in 'pending' state with a spinner."""
        entry = _ToolEntry(tool_name, args_str)
        entry.setStyleSheet(
            "QWidget {"
            "  background: rgba(255,255,255,0.02);"
            "  border-radius: 6px;"
            "  margin: 1px 0px;"
            "}"
        )
        # Use a unique key to handle duplicate tool names
        key = f"{tool_name}_{len(self._entry_list)}"
        self._tool_entries[key] = entry
        self._entry_list.append(tool_name)
        self._pending_count += 1
        self._detail_layout.addWidget(entry)
        self._update_summary()

    def complete_tool_call(self, tool_name: str, result: str = "", success: bool = True) -> None:
        """Mark the most recent pending entry for this tool as complete."""
        # Find the last pending entry for this tool name
        completed = False
        for key in reversed(list(self._tool_entries.keys())):
            entry = self._tool_entries[key]
            if key.rsplit("_", 1)[0] == tool_name and entry._status == _ToolEntry.STATUS_PENDING:
                is_error = "error" in result.lower()[:50] if result else False
                entry.mark_complete(success=success and not is_error)
                self._pending_count = max(0, self._pending_count - 1)
                if not success or is_error:
                    self._error_count += 1
                else:
                    self._completed_count += 1
                completed = True
                break
        if not completed:
            # Fallback: add as a completed entry directly
            self.add_tool_call(tool_name, result)
        self._update_summary()

    def add_tool_call(self, tool_name: str, detail: str) -> None:
        """Legacy: Add a tool call entry that is immediately complete."""
        entry = _ToolEntry(tool_name, detail)
        entry.mark_complete(success=True)
        entry.setStyleSheet(
            "QWidget {"
            "  background: rgba(255,255,255,0.02);"
            "  border-radius: 6px;"
            "  margin: 1px 0px;"
            "}"
        )
        key = f"{tool_name}_{len(self._entry_list)}"
        self._tool_entries[key] = entry
        self._entry_list.append(tool_name)
        self._completed_count += 1
        self._detail_layout.addWidget(entry)
        self._update_summary()

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
