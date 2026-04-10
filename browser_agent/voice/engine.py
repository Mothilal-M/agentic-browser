"""Voice engine — speech-to-text and text-to-speech using system APIs.

Uses the Web Speech API via QtWebEngine for STT (no external deps),
and pyttsx3/system TTS for speech output.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

if TYPE_CHECKING:
    from browser_agent.browser.engine import BrowserEngine

logger = logging.getLogger(__name__)

# JS injected into a hidden page to use Web Speech API for STT
STT_START_JS = """
(function() {
    if (window.__stt_active) return JSON.stringify({status: 'already_listening'});

    window.__stt_result = null;
    window.__stt_active = true;
    window.__stt_error = null;

    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.onresult = (event) => {
        window.__stt_result = event.results[0][0].transcript;
        window.__stt_active = false;
    };
    recognition.onerror = (event) => {
        window.__stt_error = event.error;
        window.__stt_active = false;
    };
    recognition.onend = () => {
        window.__stt_active = false;
    };

    recognition.start();
    return JSON.stringify({status: 'listening'});
})()
"""

STT_POLL_JS = """
(function() {
    return JSON.stringify({
        active: !!window.__stt_active,
        result: window.__stt_result || null,
        error: window.__stt_error || null
    });
})()
"""

STT_STOP_JS = """
(function() {
    window.__stt_active = false;
    return JSON.stringify({status: 'stopped'});
})()
"""


class VoiceEngine(QObject):
    """Handles speech-to-text and text-to-speech."""

    transcript_ready = pyqtSignal(str)     # emitted when STT produces text
    listening_changed = pyqtSignal(bool)   # True when mic is active
    speaking_changed = pyqtSignal(bool)    # True when TTS is speaking

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._listening = False
        self._speaking = False
        self._stt_page = None
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_stt)

    @property
    def is_listening(self) -> bool:
        return self._listening

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def setup_stt_page(self, engine: BrowserEngine) -> None:
        """Create a hidden page for Web Speech API access."""
        from PyQt6.QtWebEngineCore import QWebEnginePage
        self._stt_page = QWebEnginePage(engine.profile)
        # Load a minimal page that supports Speech API
        self._stt_page.setHtml(
            "<html><body><script>"
            "window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;"
            "</script></body></html>"
        )

    async def start_listening(self) -> bool:
        """Start speech-to-text recognition."""
        if not self._stt_page or self._listening:
            return False

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def cb(result):
            if not future.done():
                loop.call_soon_threadsafe(future.set_result, result)

        self._stt_page.runJavaScript(STT_START_JS, cb)
        result = await future

        self._listening = True
        self.listening_changed.emit(True)
        self._poll_timer.start(300)
        logger.info("Voice: started listening")
        return True

    def stop_listening(self) -> None:
        """Stop speech recognition."""
        if self._stt_page:
            self._stt_page.runJavaScript(STT_STOP_JS)
        self._listening = False
        self._poll_timer.stop()
        self.listening_changed.emit(False)

    def _poll_stt(self) -> None:
        """Poll the STT page for results."""
        if not self._stt_page:
            return

        import json

        def cb(result):
            if not result or not isinstance(result, str):
                return
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                return

            if data.get("result"):
                self._listening = False
                self._poll_timer.stop()
                self.listening_changed.emit(False)
                self.transcript_ready.emit(data["result"])
                logger.info("Voice: transcript = %s", data["result"])

            elif data.get("error"):
                self._listening = False
                self._poll_timer.stop()
                self.listening_changed.emit(False)
                logger.warning("Voice: STT error = %s", data["error"])

            elif not data.get("active"):
                self._listening = False
                self._poll_timer.stop()
                self.listening_changed.emit(False)

        self._stt_page.runJavaScript(STT_POLL_JS, cb)

    def speak(self, text: str) -> None:
        """Speak text using system TTS (non-blocking)."""
        self._speaking = True
        self.speaking_changed.emit(True)

        # Use platform TTS
        if sys.platform == "win32":
            self._speak_windows(text)
        elif sys.platform == "darwin":
            self._speak_macos(text)
        else:
            self._speak_linux(text)

    def _speak_windows(self, text: str) -> None:
        """Use Windows SAPI via PowerShell."""
        safe = text.replace("'", "''").replace('"', '\\"')[:500]
        cmd = f'powershell -Command "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak(\'{safe}\')"'
        self._run_tts_process(cmd)

    def _speak_macos(self, text: str) -> None:
        safe = text.replace("'", "'\\''")[:500]
        self._run_tts_process(f"say '{safe}'")

    def _speak_linux(self, text: str) -> None:
        safe = text.replace("'", "'\\''")[:500]
        self._run_tts_process(f"espeak '{safe}'")

    def _run_tts_process(self, cmd: str) -> None:
        """Run TTS in background subprocess."""
        import threading

        def _run():
            try:
                subprocess.run(cmd, shell=True, timeout=30,
                               capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except Exception as e:
                logger.warning("TTS failed: %s", e)
            finally:
                self._speaking = False
                self.speaking_changed.emit(False)

        threading.Thread(target=_run, daemon=True).start()
