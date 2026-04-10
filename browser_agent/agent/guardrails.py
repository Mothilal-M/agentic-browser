"""Action confirmation guardrails — pause agent on sensitive operations.

Detects dangerous keywords in tool arguments and requests user confirmation
before executing. Prevents accidental deletions, payments, and data loss.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Keywords that trigger confirmation for different severity levels
CRITICAL_KEYWORDS = [
    "delete account", "remove account", "close account", "deactivate account",
    "confirm payment", "place order", "submit order", "complete purchase",
    "pay now", "checkout", "send money", "transfer funds", "wire transfer",
    "confirm delete", "permanently delete", "remove all",
    "unsubscribe", "cancel subscription", "terminate",
]

WARNING_KEYWORDS = [
    "delete", "remove", "submit", "send", "post", "publish",
    "sign out", "log out", "logout", "signout",
    "apply", "confirm", "accept", "agree",
    "share", "invite", "follow", "connect",
    "change password", "update email", "update phone",
]

# Tools that should always be checked
MONITORED_TOOLS = {
    "click_element", "smart_click", "click_by_description",
    "click_shadow_element", "click_at_coordinates", "press_key",
}


class Guardrails:
    """Checks tool calls for sensitive actions and returns a warning if needed."""

    def __init__(self, sensitivity: str = "medium") -> None:
        """
        sensitivity:
            'low'    — only critical actions (payment, delete account)
            'medium' — critical + warning actions (submit, delete, send)
            'high'   — all monitored tool calls ask for confirmation
        """
        self._sensitivity = sensitivity

    @property
    def sensitivity(self) -> str:
        return self._sensitivity

    @sensitivity.setter
    def sensitivity(self, value: str) -> None:
        if value in ("low", "medium", "high"):
            self._sensitivity = value

    def check(self, tool_name: str, args: dict) -> str | None:
        """Check if a tool call needs confirmation.

        Returns a warning message string if confirmation is needed, or None if safe.
        """
        if tool_name not in MONITORED_TOOLS:
            return None

        # Build text to scan from all string args
        text_parts = []
        for v in args.values():
            if isinstance(v, str):
                text_parts.append(v.lower())
        scan_text = " ".join(text_parts)

        if not scan_text:
            return None

        # Check critical keywords (always flagged)
        for kw in CRITICAL_KEYWORDS:
            if kw in scan_text:
                return (
                    f"\u26a0\ufe0f **CRITICAL**: About to perform a sensitive action — "
                    f"detected '{kw}' in {tool_name}({_format_args(args)}). "
                    f"Please confirm: should I proceed? (Reply 'yes' to continue)"
                )

        # Check warning keywords (medium+ sensitivity)
        if self._sensitivity in ("medium", "high"):
            for kw in WARNING_KEYWORDS:
                if re.search(rf'\b{re.escape(kw)}\b', scan_text):
                    return (
                        f"\u26a0\ufe0f About to {tool_name} — detected '{kw}' in the action. "
                        f"Confirm? (Reply 'yes' to continue)"
                    )

        # High sensitivity — flag all monitored tool calls
        if self._sensitivity == "high":
            return (
                f"\u2139\ufe0f About to {tool_name}({_format_args(args)}). "
                f"Confirm? (Reply 'yes' to continue)"
            )

        return None


def _format_args(args: dict) -> str:
    """Short-format args for display."""
    parts = []
    for k, v in args.items():
        sv = str(v)
        if len(sv) > 40:
            sv = sv[:40] + "..."
        parts.append(f"{k}={sv!r}")
    return ", ".join(parts)
