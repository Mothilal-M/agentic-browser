"""Individual chat message bubble with rich HTML rendering that wraps on resize."""

from datetime import datetime

from PyQt6.QtCore import QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QTextDocument
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from browser_agent.ui.markdown_renderer import md_to_html
from browser_agent.ui.styles import (
    DARK_TEXT,
    DARK_TEXT_SECONDARY,
    FONT_BASE,
    FONT_FALLBACK,
    FONT_SM,
    slide_fade_in,
)


class _RichTextLabel(QWidget):
    """A widget that renders HTML via QTextDocument and reflows on resize.

    Unlike QTextBrowser, this directly paints the document and uses
    heightForWidth() so the layout system always gives it the right size.
    No scrollbars, no fixed heights — purely driven by available width.
    """

    def __init__(self, font_size: float = FONT_BASE, color: str = DARK_TEXT, parent=None):
        super().__init__(parent)
        self._doc = QTextDocument(self)
        self._doc.setDocumentMargin(0)
        self._doc.setDefaultStyleSheet(
            f"body {{ color: {color}; font-size: {font_size}px;"
            f" font-family: {FONT_FALLBACK}; }}"
            f" a {{ color: #60a5fa; text-decoration: none; }}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMouseTracking(True)

    def setHtml(self, html: str) -> None:
        self._doc.setHtml(html)
        self.updateGeometry()
        self.update()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        self._doc.setTextWidth(max(width, 50))
        return int(self._doc.size().height()) + 2

    def sizeHint(self) -> QSize:
        w = self.width() if self.width() > 50 else 300
        self._doc.setTextWidth(w)
        return QSize(w, int(self._doc.size().height()) + 2)

    def minimumSizeHint(self) -> QSize:
        return QSize(50, 20)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._doc.setTextWidth(max(event.size().width(), 50))
        self.updateGeometry()
        self.update()

    def paintEvent(self, event) -> None:
        from PyQt6.QtGui import QAbstractTextDocumentLayout, QPainter

        painter = QPainter(self)
        ctx = QAbstractTextDocumentLayout.PaintContext()
        self._doc.documentLayout().draw(painter, ctx)
        painter.end()

    def mousePressEvent(self, event) -> None:
        anchor = self._doc.documentLayout().anchorAt(event.pos())
        if anchor:
            QDesktopServices.openUrl(QUrl(anchor))
        super().mousePressEvent(event)


class ChatMessageWidget(QFrame):
    """A single message bubble in the chat panel."""

    ROLE_CONFIG = {
        "user": {"label": "You", "role_obj": "role_label_user"},
        "assistant": {"label": "Browser Agent", "role_obj": "role_label_assistant"},
        "tool": {"label": "System Tool", "role_obj": "role_label_tool"},
        "error": {"label": "System Error", "role_obj": "role_label_error"},
        "thinking": {"label": "Thinking", "role_obj": "role_label_thinking"},
    }

    def __init__(self, role: str, text: str, detail: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(f"msg_{role}")
        self._role = role
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        cfg = self.ROLE_CONFIG.get(role, {"label": role.title(), "role_obj": "role_label"})

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(6)
        header.setContentsMargins(0, 0, 0, 0)

        role_label = QLabel(cfg["label"])
        role_label.setObjectName(cfg["role_obj"])
        role_label.setStyleSheet("font-weight: 600; letter-spacing: 0.5px;")
        header.addWidget(role_label)

        header.addStretch()

        ts = QLabel(datetime.now().strftime("%H:%M"))
        ts.setObjectName("msg_timestamp")
        header.addWidget(ts)

        layout.addLayout(header)

        # Message content
        self._raw_text_store = text
        self._rich_label: _RichTextLabel | None = None
        self._text_label: QLabel | None = None

        if role in ("assistant", "error"):
            self._rich_label = _RichTextLabel(FONT_BASE, DARK_TEXT)
            self._rich_label.setHtml(md_to_html(text))
            layout.addWidget(self._rich_label)
        else:
            self._text_label = QLabel(text)
            self._text_label.setObjectName("msg_text")
            self._text_label.setWordWrap(True)
            self._text_label.setTextFormat(Qt.TextFormat.PlainText)
            self._text_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self._text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            layout.addWidget(self._text_label)

        # Detail (tool results)
        if detail:
            detail_label = _RichTextLabel(FONT_SM, DARK_TEXT_SECONDARY)
            detail_label.setHtml(md_to_html(detail))
            layout.addWidget(detail_label)

        # Entrance animation
        self._anim = slide_fade_in(self, duration=300)

    def append_text(self, text: str) -> None:
        self._raw_text_store += text
        if self._rich_label:
            self._rich_label.setHtml(md_to_html(self._raw_text_store))
        elif self._text_label:
            self._text_label.setText(self._text_label.text() + text)

    def set_text(self, text: str) -> None:
        self._raw_text_store = text
        if self._rich_label:
            self._rich_label.setHtml(md_to_html(text))
        elif self._text_label:
            self._text_label.setText(text)
