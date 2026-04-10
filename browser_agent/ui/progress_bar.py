"""Animated gradient progress bar for page loading — sits under the nav bar."""

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter
from PyQt6.QtWidgets import QWidget


class LoadingProgressBar(QWidget):
    """Thin animated gradient bar that shows during page load.

    - Indeterminate shimmer when loading
    - Fades out smoothly when done
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(3)
        self._loading = False
        self._progress = 0.0   # shimmer position 0→1
        self._opacity = 0.0    # fade in/out

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def start(self):
        self._loading = True
        self._progress = 0.0

    def stop(self):
        self._loading = False

    def _tick(self):
        if self._loading:
            self._progress = (self._progress + 0.012) % 1.0
            self._opacity = min(self._opacity + 0.1, 1.0)
        else:
            self._opacity = max(self._opacity - 0.06, 0.0)
        self.update()

    def paintEvent(self, event):
        if self._opacity < 0.01:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setOpacity(self._opacity)

        w, h = self.width(), self.height()

        # Shimmer gradient that slides across
        shimmer_w = w * 0.4
        x = self._progress * (w + shimmer_w) - shimmer_w

        grad = QLinearGradient(x, 0, x + shimmer_w, 0)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.3, QColor(108, 92, 231, 200))
        grad.setColorAt(0.5, QColor(168, 85, 247, 255))
        grad.setColorAt(0.7, QColor(59, 130, 246, 200))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        p.fillRect(QRectF(0, 0, w, h), QBrush(grad))
        p.end()
