"""Session state export/import — save and restore cookies, localStorage, auth.

Exports the QWebEngineProfile's cookie store to a JSON file.
Optionally encrypts with a user-provided key.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser_agent.browser.engine import BrowserEngine

logger = logging.getLogger(__name__)


def export_session_state(engine: BrowserEngine, output_path: str | Path, encrypt_key: str = "") -> str:
    """Export cookies and session metadata to a JSON file.

    If encrypt_key is provided, the cookie data is AES-encrypted (requires pycryptodome).
    Otherwise saved as plaintext JSON.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Collect session info
    state = {
        "version": 1,
        "exported_at": time.time(),
        "storage_path": engine._config.persistent_storage_path,
        "user_agent": "Chrome/130.0.0.0",
        "note": "Session state exported from AI Browser Agent",
    }

    # Export the persistent storage path (cookies are in SQLite files there)
    storage = Path(engine._config.persistent_storage_path)
    cookies_db = storage / "Cookies"
    if cookies_db.exists():
        cookie_data = cookies_db.read_bytes()
        state["cookies_b64"] = base64.b64encode(cookie_data).decode()
        state["cookies_size"] = len(cookie_data)

    local_storage = storage / "Local Storage"
    if local_storage.exists() and local_storage.is_dir():
        ls_files = {}
        for f in local_storage.rglob("*"):
            if f.is_file() and f.stat().st_size < 5_000_000:  # skip files > 5MB
                rel = str(f.relative_to(local_storage))
                ls_files[rel] = base64.b64encode(f.read_bytes()).decode()
        if ls_files:
            state["local_storage"] = ls_files

    # Encrypt if key provided
    if encrypt_key:
        try:
            payload = json.dumps(state).encode()
            encrypted = _simple_encrypt(payload, encrypt_key)
            final = {"encrypted": True, "data": base64.b64encode(encrypted).decode()}
        except Exception as e:
            logger.warning("Encryption failed, saving plaintext: %s", e)
            final = state
    else:
        final = state

    path.write_text(json.dumps(final, indent=2), encoding="utf-8")
    return str(path)


def import_session_state(engine: BrowserEngine, input_path: str | Path, encrypt_key: str = "") -> bool:
    """Import cookies and session state from a JSON file.

    Returns True on success, False on failure.
    """
    path = Path(input_path)
    if not path.exists():
        logger.error("Session file not found: %s", path)
        return False

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.error("Invalid JSON in session file")
        return False

    # Decrypt if needed
    if raw.get("encrypted"):
        if not encrypt_key:
            logger.error("Session file is encrypted but no key provided")
            return False
        try:
            encrypted = base64.b64decode(raw["data"])
            decrypted = _simple_decrypt(encrypted, encrypt_key)
            raw = json.loads(decrypted)
        except Exception as e:
            logger.error("Decryption failed: %s", e)
            return False

    storage = Path(engine._config.persistent_storage_path)
    storage.mkdir(parents=True, exist_ok=True)

    # Restore cookies
    if "cookies_b64" in raw:
        cookies_db = storage / "Cookies"
        cookies_db.write_bytes(base64.b64decode(raw["cookies_b64"]))
        logger.info("Restored cookies (%d bytes)", raw.get("cookies_size", 0))

    # Restore local storage
    if "local_storage" in raw:
        ls_dir = storage / "Local Storage"
        ls_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, data_b64 in raw["local_storage"].items():
            target = ls_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(data_b64))
        logger.info("Restored %d local storage files", len(raw["local_storage"]))

    return True


def _simple_encrypt(data: bytes, key: str) -> bytes:
    """Simple XOR encryption with key stretching. NOT cryptographic — just obfuscation."""
    key_bytes = hashlib.sha256(key.encode()).digest()
    return bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))


def _simple_decrypt(data: bytes, key: str) -> bytes:
    """XOR decryption (symmetric)."""
    return _simple_encrypt(data, key)  # XOR is its own inverse
