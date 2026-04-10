"""Screenshot capture — QWebEngineView.grab() to base64 JPEG."""

import base64

from PyQt6.QtCore import QBuffer, QIODevice, Qt
from PyQt6.QtWidgets import QWidget

from browser_agent.config import AppConfig


class ScreenshotCapture:
    def __init__(self, config: AppConfig) -> None:
        self._quality = config.screenshot_quality
        self._max_dim = config.max_screenshot_dimension

    def capture(self, view: QWidget) -> str:
        """Synchronously capture a view and return base64-encoded JPEG."""
        pixmap = view.grab()
        return self._pixmap_to_base64(pixmap)

    def _pixmap_to_base64(self, pixmap) -> str:
        if pixmap.width() > self._max_dim or pixmap.height() > self._max_dim:
            pixmap = pixmap.scaled(
                self._max_dim,
                self._max_dim,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buf, "JPEG", self._quality)
        raw = buf.data().data()
        buf.close()

        return base64.b64encode(raw).decode("utf-8")
