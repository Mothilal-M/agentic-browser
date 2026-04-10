"""Tests for the action confirmation guardrails."""

import pytest

from browser_agent.agent.guardrails import Guardrails


class TestGuardrailsCritical:
    """Critical keywords should always be flagged regardless of sensitivity."""

    @pytest.fixture()
    def guardrails(self):
        return Guardrails(sensitivity="low")

    def test_detects_payment_keyword(self, guardrails):
        result = guardrails.check("click_element", {"selector": "confirm payment"})
        assert result is not None
        assert "CRITICAL" in result

    def test_detects_delete_account(self, guardrails):
        result = guardrails.check("smart_click", {"selector": "delete account"})
        assert result is not None
        assert "CRITICAL" in result

    def test_detects_case_insensitive(self, guardrails):
        result = guardrails.check("click_element", {"selector": "CONFIRM PAYMENT"})
        assert result is not None

    def test_safe_action_passes(self, guardrails):
        result = guardrails.check("click_element", {"selector": "#next-button"})
        assert result is None


class TestGuardrailsWarning:
    """Warning keywords should be flagged at medium+ sensitivity."""

    def test_medium_flags_submit(self):
        g = Guardrails(sensitivity="medium")
        result = g.check("click_element", {"selector": "submit"})
        assert result is not None

    def test_low_ignores_submit(self):
        g = Guardrails(sensitivity="low")
        result = g.check("click_element", {"selector": "submit"})
        assert result is None

    def test_medium_flags_delete(self):
        g = Guardrails(sensitivity="medium")
        result = g.check("smart_click", {"selector": "delete"})
        assert result is not None


class TestGuardrailsHigh:
    """High sensitivity should flag all monitored tool calls."""

    def test_flags_any_monitored_tool(self):
        g = Guardrails(sensitivity="high")
        result = g.check("click_element", {"selector": "#harmless-button"})
        assert result is not None

    def test_ignores_unmonitored_tool(self):
        g = Guardrails(sensitivity="high")
        result = g.check("navigate_to", {"url": "https://google.com"})
        assert result is None


class TestGuardrailsSensitivitySetter:
    def test_set_valid_sensitivity(self):
        g = Guardrails(sensitivity="low")
        g.sensitivity = "high"
        assert g.sensitivity == "high"

    def test_set_invalid_sensitivity_ignored(self):
        g = Guardrails(sensitivity="medium")
        g.sensitivity = "invalid"
        assert g.sensitivity == "medium"
