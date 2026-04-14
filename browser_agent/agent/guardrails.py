"""Action confirmation guardrails — classify sensitive operations."""

from __future__ import annotations

from dataclasses import dataclass
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
    "click_text",
}


@dataclass
class GuardrailDecision:
    blocker_type: str
    severity: str
    tool_name: str
    keyword: str
    message: str
    args: dict


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

    def check(self, tool_name: str, args: dict) -> GuardrailDecision | None:
        """Check if a tool call needs confirmation.

        Returns a structured decision if confirmation is needed, or None if safe.
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
                return GuardrailDecision(
                    blocker_type="confirmation_required",
                    severity="critical",
                    tool_name=tool_name,
                    keyword=kw,
                    args=args,
                    message=(
                        f"About to perform a sensitive action — detected '{kw}' in "
                        f"{tool_name}({_format_args(args)}). Confirm before proceeding."
                    ),
                )

        # Check warning keywords (medium+ sensitivity)
        if self._sensitivity in ("medium", "high"):
            for kw in WARNING_KEYWORDS:
                if re.search(rf'\b{re.escape(kw)}\b', scan_text):
                    return GuardrailDecision(
                        blocker_type="confirmation_required",
                        severity="warning",
                        tool_name=tool_name,
                        keyword=kw,
                        args=args,
                        message=(
                            f"About to {tool_name} — detected '{kw}' in the action. "
                            f"Ask the user to confirm before proceeding."
                        ),
                    )

        # High sensitivity — flag all monitored tool calls
        if self._sensitivity == "high":
            return GuardrailDecision(
                blocker_type="confirmation_required",
                severity="info",
                tool_name=tool_name,
                keyword="monitored_action",
                args=args,
                message=(
                    f"About to {tool_name}({_format_args(args)}). "
                    f"High-sensitivity mode requires confirmation."
                ),
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
