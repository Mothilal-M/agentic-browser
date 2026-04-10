"""Thread selector — dropdown/list to switch between conversation threads."""

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

from browser_agent.storage.conversation_db import Thread
from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    ACCENT_SECONDARY,
    DARK_BG,
    DARK_BORDER,
    DARK_SURFACE,
    DARK_TEXT,
    DARK_TEXT_MUTED,
    DARK_TEXT_SECONDARY,
    ERROR,
    fade_in,
)


class _ThreadItem(QFrame):
    """A single thread row in the selector."""

    clicked = pyqtSignal(str)   # thread_id
    deleted = pyqtSignal(str)   # thread_id

    def __init__(self, thread: Thread, is_active: bool = False, parent=None):
        super().__init__(parent)
        self._thread_id = thread.thread_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("thread_active" if is_active else "thread_item")
        self.setFixedHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(8)

        # Chat icon
        icon = QLabel("\u25ac" if is_active else "\u25ab")
        icon.setStyleSheet(
            f"color: {ACCENT_PRIMARY if is_active else DARK_TEXT_MUTED}; font-size: 10px;"
        )
        icon.setFixedWidth(12)
        layout.addWidget(icon)

        # Title + meta
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setContentsMargins(0, 0, 0, 0)

        title = QLabel(thread.title)
        title.setStyleSheet(
            f"color: {DARK_TEXT if is_active else DARK_TEXT_SECONDARY}; "
            f"font-size: 12px; font-weight: {'600' if is_active else '400'};"
        )
        title.setWordWrap(False)
        text_col.addWidget(title)

        ts = datetime.fromtimestamp(thread.updated_at).strftime("%b %d, %H:%M")
        meta = QLabel(f"{thread.message_count} msgs \u00b7 {ts}")
        meta.setStyleSheet(f"color: {DARK_TEXT_MUTED}; font-size: 10px;")
        text_col.addWidget(meta)

        layout.addLayout(text_col, 1)

        # Delete button (shown on hover via stylesheet)
        del_btn = QPushButton("\u2715")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {DARK_TEXT_MUTED}; "
            f"border: none; border-radius: 4px; font-size: 11px; }}"
            f"QPushButton:hover {{ background: rgba(239,68,68,0.15); color: {ERROR}; }}"
        )
        del_btn.clicked.connect(lambda: self.deleted.emit(self._thread_id))
        layout.addWidget(del_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._thread_id)
        super().mousePressEvent(event)


class ThreadSelector(QWidget):
    """Panel showing list of conversation threads with new/switch/delete."""

    thread_selected = pyqtSignal(str)     # thread_id
    new_thread_requested = pyqtSignal()
    thread_deleted = pyqtSignal(str)      # thread_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("thread_selector")
        self._active_thread_id = ""

        # New chat button
        new_btn = QPushButton("\u2726  New Chat")
        new_btn.setObjectName("new_chat_btn")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setFixedHeight(36)
        new_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(108,92,231,0.12); color: {ACCENT_PRIMARY}; "
            f"border: 1px solid rgba(108,92,231,0.2); border-radius: 10px; "
            f"font-size: 12px; font-weight: 600; padding: 0 16px; }}"
            f"QPushButton:hover {{ background: rgba(108,92,231,0.20); "
            f"border-color: rgba(108,92,231,0.35); }}"
        )
        new_btn.clicked.connect(self.new_thread_requested.emit)

        # Thread list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._list_container)

        # Label
        label = QLabel("CONVERSATIONS")
        label.setStyleSheet(
            f"color: {DARK_TEXT_MUTED}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.2px; padding: 8px 12px 4px 12px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(new_btn)
        layout.addWidget(label)
        layout.addWidget(self._scroll, 1)

    def set_threads(self, threads: list[Thread], active_thread_id: str = "") -> None:
        """Rebuild the thread list."""
        self._active_thread_id = active_thread_id

        # Clear existing
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add threads
        for thread in threads:
            is_active = thread.thread_id == active_thread_id
            item = _ThreadItem(thread, is_active)
            item.clicked.connect(self.thread_selected.emit)
            item.deleted.connect(self.thread_deleted.emit)
            count = self._list_layout.count()
            self._list_layout.insertWidget(count - 1, item)
