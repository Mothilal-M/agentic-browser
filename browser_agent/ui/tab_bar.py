"""Custom tab bar with animated add button, favicons, loading indicator, and scroll."""

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QPushButton, QTabBar


# Simple loading spinner icon generator
_SPINNER_CHARS = ["\u25dc", "\u25dd", "\u25de", "\u25df"]  # ◜◝◞◟


class _AddTabButton(QPushButton):
    """Circular + button with hover glow animation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("+")
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")

        self._hover = 0.0
        self._hovered = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def enterEvent(self, e):
        self._hovered = True
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        super().leaveEvent(e)

    def _tick(self):
        target = 1.0 if self._hovered else 0.0
        self._hover += (target - self._hover) * 0.15
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 2
        t = self._hover

        # Background
        if t > 0.01:
            p.setBrush(QBrush(QColor(255, 255, 255, int(15 * t))))
            p.setPen(QPen(QColor(108, 92, 231, int(40 * t)), 1.0))
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Plus sign
        alpha = int(80 + 175 * t)
        p.setPen(QPen(QColor(255, 255, 255, alpha), 1.8))
        p.drawLine(int(cx - 5), int(cy), int(cx + 5), int(cy))
        p.drawLine(int(cx), int(cy - 5), int(cx), int(cy + 5))

        p.end()


class BrowserTabBar(QTabBar):
    new_tab_requested = pyqtSignal()
    tab_close_requested = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setExpanding(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setDocumentMode(True)
        self.setUsesScrollButtons(True)
        self.setIconSize(QSize(16, 16))

        self._add_btn = _AddTabButton(self)
        self._add_btn.clicked.connect(self.new_tab_requested.emit)
        self.tabCloseRequested.connect(self.tab_close_requested.emit)

        # Track loading state per tab
        self._loading_tabs: set[int] = set()
        self._saved_icons: dict[int, QIcon] = {}

        # Loading spinner animation timer
        self._spin_tick = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._animate_loading)

    def set_tab_loading(self, index: int, loading: bool) -> None:
        """Show or hide a loading indicator for the given tab."""
        if loading:
            if index not in self._loading_tabs:
                self._saved_icons[index] = self.tabIcon(index)
            self._loading_tabs.add(index)
            if not self._spinner_timer.isActive():
                self._spinner_timer.start(150)
        else:
            self._loading_tabs.discard(index)
            # Restore saved icon (or clear if none was saved)
            saved = self._saved_icons.pop(index, QIcon())
            if not saved.isNull():
                self.setTabIcon(index, saved)
            if not self._loading_tabs:
                self._spinner_timer.stop()

    def set_tab_favicon(self, index: int, icon: QIcon) -> None:
        """Set the favicon for a tab. If tab is loading, save for later."""
        if index in self._loading_tabs:
            self._saved_icons[index] = icon
        else:
            self.setTabIcon(index, icon)

    def _animate_loading(self) -> None:
        self._spin_tick += 1
        char = _SPINNER_CHARS[self._spin_tick % 4]
        # Create a text-based icon for loading tabs
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(59, 130, 246))
        font = painter.font()
        font.setPixelSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, char)
        painter.end()
        loading_icon = QIcon(pixmap)
        for idx in list(self._loading_tabs):
            if idx < self.count():
                self.setTabIcon(idx, loading_icon)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_add_button()

    def tabLayoutChange(self) -> None:
        super().tabLayoutChange()
        self._position_add_button()

    def _position_add_button(self) -> None:
        if not hasattr(self, "_add_btn"):
            return
        last = self.count() - 1
        if last >= 0:
            rect = self.tabRect(last)
            x = rect.right() + 8
        else:
            x = 8
        y = (self.height() - self._add_btn.height()) // 2
        self._add_btn.move(x, max(y, 0))

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            idx = self.tabAt(event.pos())
            if idx >= 0:
                self.tab_close_requested.emit(idx)
        super().mouseReleaseEvent(event)
