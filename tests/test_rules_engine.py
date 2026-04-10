"""Tests for the autonomous rules engine."""

import pytest

from browser_agent.autonomous.rules_engine import RulesEngine


class TestRulesEngineCRUD:
    @pytest.fixture()
    def engine(self, tmp_path):
        e = RulesEngine(tmp_path / "rules.db")
        yield e
        e.close()

    def test_add_rule(self, engine):
        rule = engine.add_rule("Check email", "schedule:30m", "Check my email inbox")
        assert rule.name == "Check email"
        assert rule.trigger == "schedule:30m"
        assert rule.enabled is True

    def test_list_rules(self, engine):
        engine.add_rule("Rule 1", "schedule:1h", "Do thing 1")
        engine.add_rule("Rule 2", "schedule:2h", "Do thing 2")
        rules = engine.list_rules()
        assert len(rules) == 2

    def test_toggle_rule(self, engine):
        rule = engine.add_rule("Toggle me", "schedule:30m", "Action")
        engine.toggle_rule(rule.rule_id, False)
        updated = engine.get_rule(rule.rule_id)
        assert updated.enabled is False

    def test_delete_rule(self, engine):
        rule = engine.add_rule("Delete me", "schedule:30m", "Action")
        engine.delete_rule(rule.rule_id)
        rules = engine.list_rules()
        assert len(rules) == 0

    def test_get_rule(self, engine):
        rule = engine.add_rule("Find me", "schedule:1h", "Action")
        found = engine.get_rule(rule.rule_id)
        assert found.name == "Find me"

    def test_get_nonexistent_rule(self, engine):
        result = engine.get_rule("nonexistent-id")
        assert result is None


class TestParseInterval:
    def test_minutes(self):
        assert RulesEngine._parse_interval("schedule:30m") == 1800

    def test_hours(self):
        assert RulesEngine._parse_interval("schedule:2h") == 7200

    def test_seconds(self):
        assert RulesEngine._parse_interval("schedule:60s") == 60

    def test_plain_number(self):
        assert RulesEngine._parse_interval("schedule:120") == 120

    def test_invalid(self):
        assert RulesEngine._parse_interval("schedule:abc") is None

    def test_no_colon(self):
        assert RulesEngine._parse_interval("bad") is None
