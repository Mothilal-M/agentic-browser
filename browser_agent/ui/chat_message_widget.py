"""Individual chat message bubble with rich HTML rendering that wraps on resize."""

from datetime import datetime

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
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


class _RichTextView(QTextBrowser):
    """QTextBrowser that reflows HTML content when its width changes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(lambda url: QDesktopServices.openUrl(url))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            f"QTextBrowser {{"
            f"  background: transparent; border: none; padding: 0px; margin: 0px;"
            f"  color: {DARK_TEXT}; font-size: {FONT_BASE}px; font-family: {FONT_FALLBACK};"
            f"  selection-background-color: rgba(108,92,231,0.3);"
            f"}}"
        )
        self.document().setDocumentMargin(0)

    def _reflow(self) -> None:
        """Recompute document layout at current viewport width, then fix height."""
        vw = self.viewport().width()
        if vw > 20:
            self.document().setTextWidth(vw)
        doc_h = int(self.document().size().height()) + 4
        self.setFixedHeight(max(doc_h, 20))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()

    def setHtml(self, html: str) -> None:
        super().setHtml(html)
        # Defer reflow so viewport width is settled
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._reflow)


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
        self._text_view: _RichTextView | None = None
        self._text_label: QLabel | None = None

        if role in ("assistant", "error"):
            self._text_view = _RichTextView()
            self._text_view.setHtml(md_to_html(text))
            layout.addWidget(self._text_view)
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
            detail_view = _RichTextView()
            detail_view.setStyleSheet(
                f"QTextBrowser {{"
                f"  background: transparent; border: none; padding: 0px;"
                f"  color: {DARK_TEXT_SECONDARY}; font-size: {FONT_SM}px;"
                f"  font-family: {FONT_FALLBACK};"
                f"}}"
            )
            detail_view.setHtml(md_to_html(detail))
            layout.addWidget(detail_view)

        # Entrance animation
        self._anim = slide_fade_in(self, duration=300)

    def append_text(self, text: str) -> None:
        self._raw_text_store += text
        if self._text_view:
            self._text_view.setHtml(md_to_html(self._raw_text_store))
        elif self._text_label:
            self._text_label.setText(self._text_label.text() + text)

    def set_text(self, text: str) -> None:
        self._raw_text_store = text
        if self._text_view:
            self._text_view.setHtml(md_to_html(text))
        elif self._text_label:
            self._text_label.setText(text)
