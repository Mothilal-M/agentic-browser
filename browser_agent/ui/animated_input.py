"""Animated chat input with embedded send button and glowing gradient border."""

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    DARK_TEXT,
    DARK_TEXT_MUTED,
    ERROR,
    FONT_BASE,
    FONT_FALLBACK,
    FONT_XS,
    GRADIENT_SPEED_FOCUS,
    GRADIENT_SPEED_IDLE,
    GLOW_FADE_IN,
    GLOW_FADE_OUT,
    HOVER_EASE,
    BTN_MD,
    RADIUS_XL,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)


class _InnerTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QTextEdit {{"
            f"  background: transparent; color: {DARK_TEXT}; border: none; padding: 0px;"
            f"  font-size: {FONT_BASE}px; font-family: {FONT_FALLBACK};"
            f"  selection-background-color: {ACCENT_PRIMARY}; selection-color: white;"
            f"}}"
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setPlaceholderText("Ask anything...")


class _SendButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("\u2191")
        self.setFixedSize(BTN_MD, BTN_MD)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self._hovered = False
        self._pressed = False
        self._pulse = 0.0
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
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False
        super().mouseReleaseEvent(e)

    def _tick(self):
        target = 1.0 if self._hovered else 0.0
        self._pulse += (target - self._pulse) * HOVER_EASE
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 1

        if self._pulse > 0.05 or self.isEnabled():
            grad = QConicalGradient(cx, cy, 45)
            alpha = 0.7 + 0.3 * self._pulse
            grad.setColorAt(0.0, QColor(59, 130, 246, int(255 * alpha)))
            grad.setColorAt(0.5, QColor(99, 102, 241, int(255 * alpha)))
            grad.setColorAt(1.0, QColor(59, 130, 246, int(255 * alpha)))
            p.setBrush(QBrush(grad) if self.isEnabled() else QBrush(QColor(40, 40, 50)))
        else:
            p.setBrush(QBrush(QColor(40, 40, 50)))
        p.setPen(Qt.PenStyle.NoPen)

        scale = 0.88 if self._pressed else 1.0 - 0.03 * (1 - self._pulse)
        sr = r * scale
        p.drawEllipse(QRectF(cx - sr, cy - sr, sr * 2, sr * 2))

        if self._pulse > 0.1:
            p.setPen(QPen(QColor(59, 130, 246, int(40 * self._pulse)), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            gr = sr + 3
            p.drawEllipse(QRectF(cx - gr, cy - gr, gr * 2, gr * 2))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 240 if self.isEnabled() else 80)))
        arrow = QPainterPath()
        arrow.moveTo(cx, cy - 7)
        arrow.lineTo(cx - 5, cy + 1)
        arrow.lineTo(cx - 1.5, cy + 1)
        arrow.lineTo(cx - 1.5, cy + 7)
        arrow.lineTo(cx + 1.5, cy + 7)
        arrow.lineTo(cx + 1.5, cy + 1)
        arrow.lineTo(cx + 5, cy + 1)
        arrow.closeSubpath()
        p.drawPath(arrow)
        p.end()


class AnimatedChatInput(QWidget):
    textChanged = pyqtSignal()
    sendClicked = pyqtSignal()

    COLORS = [
        QColor(59, 130, 246), QColor(99, 102, 241), QColor(148, 163, 184),
        QColor(56, 189, 248), QColor(99, 102, 241), QColor(59, 130, 246),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("animated_input_wrapper")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._focused = False
        self._angle = 0.0
        self._glow_intensity = 0.0
        self._border_width = 1.5

        self._edit = _InnerTextEdit()
        self._edit.setFixedHeight(INPUT_H := 44)
        self._edit.textChanged.connect(self.textChanged.emit)
        self._edit.installEventFilter(self)

        self._send_btn = _SendButton()
        self._send_btn.clicked.connect(self.sendClicked.emit)

        self._stop_btn = QPushButton("\u25a0")
        self._stop_btn.setFixedSize(BTN_MD, BTN_MD)
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(239,68,68,0.15); color: {ERROR};"
            f" border: 1px solid rgba(239,68,68,0.3); border-radius: {BTN_MD // 2}px;"
            f" font-size: {FONT_BASE}px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: rgba(239,68,68,0.25); }}"
        )
        self._stop_btn.hide()

        edit_row = QHBoxLayout()
        edit_row.setContentsMargins(0, 0, 0, 0)
        edit_row.setSpacing(SPACE_2)
        edit_row.addWidget(self._edit, 1)
        edit_row.addWidget(self._send_btn)
        edit_row.addWidget(self._stop_btn)

        hint = QLabel("Enter to send \u00b7 Shift+Enter for new line")
        hint.setStyleSheet(f"color: rgba(255,255,255,0.12); font-size: {FONT_XS}px; padding: 0 {SPACE_1}px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_4, SPACE_3, SPACE_3, SPACE_2)
        layout.setSpacing(SPACE_1)
        layout.addLayout(edit_row)
        layout.addWidget(hint)
        self.setFixedHeight(82)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def toPlainText(self) -> str:
        return self._edit.toPlainText()

    def clear(self) -> None:
        self._edit.clear()

    def setEnabled(self, enabled: bool) -> None:
        self._edit.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        super().setEnabled(enabled)

    def setFocus(self) -> None:
        self._edit.setFocus()

    def set_busy(self, busy: bool) -> None:
        self._edit.setEnabled(not busy)
        self._send_btn.setVisible(not busy)
        self._send_btn.setEnabled(not busy)
        self._stop_btn.setVisible(busy)

    def installEventFilter(self, obj) -> None:
        if obj is not self:
            self._edit.installEventFilter(obj)
        else:
            super().installEventFilter(obj)

    @property
    def edit(self) -> QTextEdit:
        return self._edit

    @property
    def send_btn(self) -> QPushButton:
        return self._send_btn

    @property
    def stop_btn(self) -> QPushButton:
        return self._stop_btn

    def eventFilter(self, obj, event) -> bool:
        if obj is self._edit:
            if event.type() == event.Type.FocusIn:
                self._focused = True
            elif event.type() == event.Type.FocusOut:
                self._focused = False
        return super().eventFilter(obj, event)

    def _tick(self) -> None:
        if self._focused:
            self._angle = (self._angle + GRADIENT_SPEED_FOCUS) % 360.0
            self._glow_intensity = min(self._glow_intensity + GLOW_FADE_IN, 1.0)
        else:
            self._angle = (self._angle + GRADIENT_SPEED_IDLE * 1.5) % 360.0
            # Keep a visible baseline glow even when unfocused
            self._glow_intensity = max(self._glow_intensity - GLOW_FADE_OUT, 0.35)
        self._border_width = 1.5 + self._glow_intensity * 0.5
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        radius = float(RADIUS_XL)
        m = 1.5
        rect = QRectF(m, m, w - 2 * m, h - 2 * m)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        painter.fillPath(path, QBrush(QColor(255, 255, 255, 10 if self._focused else 5)))

        intensity = self._glow_intensity
        if intensity > 0.01:
            cx, cy = w / 2, h / 2
            grad = QConicalGradient(cx, cy, self._angle)
            for i, color in enumerate(self.COLORS):
                pos = i / (len(self.COLORS) - 1)
                c = QColor(color)
                c.setAlphaF(0.3 + 0.7 * intensity)
                grad.setColorAt(pos, c)
            painter.setPen(QPen(QBrush(grad), self._border_width))
            painter.drawRoundedRect(rect, radius, radius)
            if intensity > 0.3:
                for i in range(3):
                    gr = QRectF(m - i - 1, m - i - 1, w - 2 * (m - i - 1), h - 2 * (m - i - 1))
                    painter.setPen(QPen(QColor(108, 92, 231, int(15 * intensity * (3 - i) / 3)), 1.0))
                    painter.drawRoundedRect(gr, radius + i + 1, radius + i + 1)
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 15), 1.0))
            painter.drawRoundedRect(rect, radius, radius)
        painter.end()
