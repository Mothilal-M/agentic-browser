"""Animated navigation button with hover glow and press scale."""

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QPushButton

from browser_agent.ui.styles import ACCENT_PRIMARY, BTN_MD, FONT_LG, HOVER_EASE


class NavButton(QPushButton):
    def __init__(self, icon_text: str, tooltip: str = "", parent=None):
        super().__init__(parent)
        self._icon_text = icon_text
        self.setToolTip(tooltip)
        self.setFixedSize(BTN_MD + 2, BTN_MD + 2)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self._hovered = False
        self._pressed = False
        self._hover_anim = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def enterEvent(self, e):
        self._hovered = True
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True
        self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(e)

    def _tick(self):
        target = 1.0 if self._hovered else 0.0
        self._hover_anim += (target - self._hover_anim) * HOVER_EASE
        if abs(self._hover_anim - target) < 0.005:
            self._hover_anim = target
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 2
        t = self._hover_anim

        if t > 0.01:
            p.setBrush(QBrush(QColor(255, 255, 255, int(20 * t))))
            p.setPen(Qt.PenStyle.NoPen)
            scale = 0.92 if self._pressed else 1.0
            sr = r * scale
            p.drawEllipse(QRectF(cx - sr, cy - sr, sr * 2, sr * 2))
            if t > 0.3:
                p.setPen(QPen(QColor(108, 92, 231, int(20 * t)), 1.0))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QRectF(cx - sr, cy - sr, sr * 2, sr * 2))

        text_alpha = int(120 + 135 * t)
        color = QColor(108, 92, 231, 255) if self._pressed else QColor(255, 255, 255, text_alpha)
        p.setPen(color)
        font = p.font()
        font.setPixelSize(FONT_LG)
        font.setWeight(font.Weight.DemiBold)
        p.setFont(font)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self._icon_text)
        p.end()
