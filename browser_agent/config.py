"""Application configuration loaded from environment and .env file."""

import os
import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


def _default_storage_path() -> str:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return str(Path(base) / "BrowserAgent" / "profile")


class AppConfig(BaseSettings):
    # LLM
    model: str = "gemini-3-flash-preview"
    provider: str = "google"
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    base_url: str = ""  # For local models: http://localhost:11434/v1

    # Browser
    viewport_width: int = 1280
    viewport_height: int = 900
    persistent_storage_path: str = Field(default_factory=_default_storage_path)
    home_url: str = "https://www.google.com"

    # Screenshot
    screenshot_quality: int = 70
    max_screenshot_dimension: int = 1280

    # UI
    sidebar_width_ratio: float = 0.3
    theme: str = "dark"
    window_width: int = 1400
    window_height: int = 900

    # Agent
    recursion_limit: int = 100
    reasoning_effort: str = "medium"

    # Security
    guardrail_sensitivity: str = "medium"  # low, medium, high

    model_config = {
        "env_prefix": "BROWSER_AGENT_",
        "env_file": ".env",
        "extra": "ignore",
    }

    @property
    def is_local_model(self) -> bool:
        """True when using a local model via Ollama/llama.cpp."""
        return bool(self.base_url)


# ── Preset configs for local models ──
# Set these in .env to use local models with NO data sent to cloud:
#
#   BROWSER_AGENT_MODEL=llava:13b
#   BROWSER_AGENT_PROVIDER=openai
#   BROWSER_AGENT_BASE_URL=http://localhost:11434/v1
#   BROWSER_AGENT_REASONING_EFFORT=low
#
# Or for LM Studio:
#   BROWSER_AGENT_BASE_URL=http://localhost:1234/v1
