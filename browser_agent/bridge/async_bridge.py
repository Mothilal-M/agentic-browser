"""Async bridge — installs qasync event loop for PyQt6 + asyncio integration."""

import asyncio
import sys

from PyQt6.QtWidgets import QApplication
from qasync import QEventLoop


def create_app_and_loop() -> tuple[QApplication, QEventLoop]:
    """Create QApplication and install qasync event loop.

    Must be called before any other Qt or asyncio operations.
    """
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    return app, loop
