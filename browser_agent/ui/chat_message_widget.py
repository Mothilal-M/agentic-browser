"""Individual chat message bubble with rich HTML rendering that wraps on resize."""

from datetime import datetime

from PyQt6.QtCore import QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTextBrowser,
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
    GLASS_BORDER,
    slide_fade_in,
)


class _AutoSizeTextBrowser(QTextBrowser):
    """QTextBrowser that shrinks to fit its content with no internal scrolling.

    The key trick: we set the document's textWidth to the viewport width
    on every resize, then fix our height to match the document height.
    A deferred timer handles the initial layout pass where width is 0.
    """

    def __init__(self, font_size: float = FONT_BASE, color: str = DARK_TEXT, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(lambda url: QDesktopServices.openUrl(url))

        # No scrollbars — we size to content
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            f"QTextBrowser {{"
            f"  background: transparent; border: none;"
            f"  color: {color}; font-size: {font_size}px;"
            f"  font-family: {FONT_FALLBACK};"
            f"  selection-background-color: rgba(59,130,246,0.3);"
            f"  padding: 0px; margin: 0px;"
            f"}}"
        )
        self.document().setDocumentMargin(0)
        # Deferred reflow handles initial 0-width
        self._reflow_timer = QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.setInterval(0)
        self._reflow_timer.timeout.connect(self._reflow)

    def setHtml(self, html: str) -> None:
        super().setHtml(html)
        self._reflow_timer.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self) -> None:
        # Use the viewport width (actual usable area)
        w = self.viewport().width()
        if w < 30:
            # Not laid out yet — try again next event loop tick
            self._reflow_timer.start()
            return
        doc = self.document()
        doc.setTextWidth(w)
        h = int(doc.size().height()) + 2
        if h != self.height():
            self.setFixedHeight(h)


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

        # Header
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

        # Content
        self._raw_text_store = text
        self._rich_view: _AutoSizeTextBrowser | None = None
        self._text_label: QLabel | None = None

        if role in ("assistant", "error"):
            self._rich_view = _AutoSizeTextBrowser(FONT_BASE, DARK_TEXT)
            self._rich_view.setHtml(md_to_html(text))
            layout.addWidget(self._rich_view)
        else:
            self._text_label = QLabel(text)
            self._text_label.setObjectName("msg_text")
            self._text_label.setWordWrap(True)
            self._text_label.setTextFormat(Qt.TextFormat.PlainText)
            self._text_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self._text_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            layout.addWidget(self._text_label)

        # Detail
        if detail:
            dv = _AutoSizeTextBrowser(FONT_SM, DARK_TEXT_SECONDARY)
            dv.setHtml(md_to_html(detail))
            layout.addWidget(dv)

        self._anim = slide_fade_in(self, duration=300)

    def append_text(self, text: str) -> None:
        self._raw_text_store += text
        if self._rich_view:
            self._rich_view.setHtml(md_to_html(self._raw_text_store))
        elif self._text_label:
            self._text_label.setText(self._text_label.text() + text)

    def set_text(self, text: str) -> None:
        self._raw_text_store = text
        if self._rich_view:
            self._rich_view.setHtml(md_to_html(text))
        elif self._text_label:
            self._text_label.setText(text)
