"""Custom tab bar with animated add button and smooth interactions."""

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QPushButton, QTabBar


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

        self._add_btn = _AddTabButton(self)
        self._add_btn.clicked.connect(self.new_tab_requested.emit)
        self.tabCloseRequested.connect(self.tab_close_requested.emit)

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
