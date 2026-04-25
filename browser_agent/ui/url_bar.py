"""Animated URL bar with gradient focus border, security indicator, and domain highlight."""

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    DARK_TEXT,
    DARK_TEXT_MUTED,
    DARK_TEXT_SECONDARY,
    FONT_BASE,
    FONT_FALLBACK,
    FONT_SM,
    GRADIENT_SPEED_FOCUS,
    GRADIENT_SPEED_IDLE,
    GLOW_FADE_IN,
    GLOW_FADE_OUT,
    INPUT_H,
    RADIUS_SM,
    SPACE_2,
    SPACE_4,
    SUCCESS,
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
        self.setFixedHeight(INPUT_H - 6)

        self._focused = False
        self._angle = 0.0
        self._glow = 0.0
        self._is_secure = False

        # Security lock icon
        self._lock_icon = QLabel("\U0001f512")
        self._lock_icon.setFixedWidth(20)
        self._lock_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lock_icon.setStyleSheet(
            f"color: {SUCCESS}; font-size: 12px; background: transparent;"
        )
        self._lock_icon.setVisible(False)

        # URL input
        self._edit = _InnerLineEdit()
        self._edit.setPlaceholderText("Search or enter URL...")
        self._edit.installEventFilter(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, SPACE_4, 0)
        layout.setSpacing(4)
        layout.addWidget(self._lock_icon)
        layout.addWidget(self._edit, 1)

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
        self._update_security_indicator(text)

    def _update_security_indicator(self, url: str) -> None:
        """Show/hide lock icon based on URL scheme."""
        if url.startswith("https://"):
            self._is_secure = True
            self._lock_icon.setText("\U0001f512")
            self._lock_icon.setStyleSheet(
                f"color: {SUCCESS}; font-size: 12px; background: transparent;"
            )
            self._lock_icon.setVisible(True)
        elif url.startswith("http://"):
            self._is_secure = False
            self._lock_icon.setText("\u26a0")
            self._lock_icon.setStyleSheet(
                f"color: {DARK_TEXT_MUTED}; font-size: 12px; background: transparent;"
            )
            self._lock_icon.setVisible(True)
        else:
            self._lock_icon.setVisible(False)

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
            self._glow = max(self._glow - GLOW_FADE_OUT * 1.2, 0.25)
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
        p.fillPath(path, QBrush(QColor(255, 255, 255, 10 if self._focused else 6)))

        intensity = self._glow
        if intensity > 0.01:
            cx, cy = w / 2, h / 2
            grad = QConicalGradient(cx, cy, self._angle)
            for pos, c in [(0.0, QColor(108, 92, 231)), (0.25, QColor(168, 85, 247)),
                           (0.5, QColor(59, 130, 246)), (0.75, QColor(168, 85, 247)),
                           (1.0, QColor(108, 92, 231))]:
                cc = QColor(c)
                cc.setAlphaF(0.20 + 0.60 * intensity)
                grad.setColorAt(pos, cc)
            p.setPen(QPen(QBrush(grad), 1.0 + 0.4 * intensity))
            p.drawRoundedRect(rect, radius, radius)
        else:
            p.setPen(QPen(QColor(255, 255, 255, 10), 1.0))
            p.drawRoundedRect(rect, radius, radius)
        p.end()
