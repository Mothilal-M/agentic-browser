"""Animated URL bar with gradient focus border."""

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QConicalGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    DARK_TEXT,
    DARK_TEXT_SECONDARY,
    FONT_BASE,
    FONT_FALLBACK,
    GRADIENT_SPEED_FOCUS,
    GRADIENT_SPEED_IDLE,
    GLOW_FADE_IN,
    GLOW_FADE_OUT,
    INPUT_H,
    RADIUS_PILL,
    SPACE_4,
)


class _InnerLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QLineEdit {{ background: transparent; color: {DARK_TEXT_SECONDARY};"
            f" border: none; padding: 0px; font-size: {FONT_BASE}px;"
            f" font-family: {FONT_FALLBACK};"
            f" selection-background-color: {ACCENT_PRIMARY}; selection-color: white; }}"
        )


class AnimatedUrlBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(INPUT_H - 4)

        self._focused = False
        self._angle = 0.0
        self._glow = 0.0

        self._edit = _InnerLineEdit()
        self._edit.setPlaceholderText("\U0001f50d  Search or enter URL...")
        self._edit.installEventFilter(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_4, 0, SPACE_4, 0)
        layout.setSpacing(0)
        layout.addWidget(self._edit)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    @property
    def returnPressed(self):
        return self._edit.returnPressed

    def text(self) -> str:
        return self._edit.text()

    def setText(self, text: str):
        self._edit.setText(text)

    def eventFilter(self, obj, event):
        if obj is self._edit:
            if event.type() == event.Type.FocusIn:
                self._focused = True
                self._edit.selectAll()
            elif event.type() == event.Type.FocusOut:
                self._focused = False
        return super().eventFilter(obj, event)

    def _tick(self):
        if self._focused:
            self._angle = (self._angle + GRADIENT_SPEED_FOCUS * 0.75) % 360.0
            self._glow = min(self._glow + GLOW_FADE_IN, 1.0)
        else:
            self._angle = (self._angle + GRADIENT_SPEED_IDLE * 1.2) % 360.0
            # Keep a visible baseline glow even when unfocused
            self._glow = max(self._glow - GLOW_FADE_OUT * 1.2, 0.3)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        radius = h / 2.0
        m = 1.0
        rect = QRectF(m, m, w - 2 * m, h - 2 * m)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        p.fillPath(path, QBrush(QColor(255, 255, 255, 12 if self._focused else 8)))

        intensity = self._glow
        if intensity > 0.01:
            cx, cy = w / 2, h / 2
            grad = QConicalGradient(cx, cy, self._angle)
            for pos, c in [(0.0, QColor(108, 92, 231)), (0.25, QColor(168, 85, 247)),
                           (0.5, QColor(59, 130, 246)), (0.75, QColor(168, 85, 247)),
                           (1.0, QColor(108, 92, 231))]:
                cc = QColor(c)
                cc.setAlphaF(0.25 + 0.75 * intensity)
                grad.setColorAt(pos, cc)
            p.setPen(QPen(QBrush(grad), 1.0 + 0.5 * intensity))
            p.drawRoundedRect(rect, radius, radius)
            if intensity > 0.4:
                p.setPen(QPen(QColor(108, 92, 231, int(12 * intensity)), 1.0))
                p.drawRoundedRect(QRectF(m - 1, m - 1, w - 2 * (m - 1), h - 2 * (m - 1)), radius + 1, radius + 1)
        else:
            p.setPen(QPen(QColor(255, 255, 255, 12), 1.0))
            p.drawRoundedRect(rect, radius, radius)
        p.end()
