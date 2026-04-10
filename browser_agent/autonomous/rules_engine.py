"""Autonomous web presence — rules engine for automated responses and actions.

Users define rules like:
- "When I get a WhatsApp message from Boss, reply 'I'll check and get back'"
- "When a new job matching 'Python' appears on LinkedIn, apply automatically"
- "Check email every 30 minutes, summarize unread"

Rules are stored in SQLite, evaluated by a scheduler, and executed by the agent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser_agent.bridge.agent_controller import AgentController

logger = logging.getLogger(__name__)


@dataclass
class AutoRule:
    rule_id: str
    name: str
    trigger: str           # "schedule:30m", "keyword:Boss", "url_change:linkedin.com"
    action_prompt: str     # what to tell the agent to do
    enabled: bool = True
    last_run: float = 0.0
    run_count: int = 0
    created_at: float = field(default_factory=time.time)


class RulesEngine:
    """Manages automation rules and executes them on schedule."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        self._running = False
        self._task: asyncio.Task | None = None

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                rule_id       TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                trigger       TEXT NOT NULL,
                action_prompt TEXT NOT NULL,
                enabled       INTEGER NOT NULL DEFAULT 1,
                last_run      REAL NOT NULL DEFAULT 0,
                run_count     INTEGER NOT NULL DEFAULT 0,
                created_at    REAL NOT NULL
            )
        """)
        self._conn.commit()

    # ── CRUD ──

    def add_rule(self, name: str, trigger: str, action_prompt: str) -> AutoRule:
        rule = AutoRule(
            rule_id=str(uuid.uuid4()),
            name=name,
            trigger=trigger,
            action_prompt=action_prompt,
        )
        self._conn.execute(
            "INSERT INTO rules (rule_id, name, trigger, action_prompt, enabled, last_run, run_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (rule.rule_id, rule.name, rule.trigger, rule.action_prompt,
             1, 0, 0, rule.created_at),
        )
        self._conn.commit()
        return rule

    def list_rules(self) -> list[AutoRule]:
        rows = self._conn.execute("SELECT * FROM rules ORDER BY created_at DESC").fetchall()
        return [self._row_to_rule(r) for r in rows]

    def get_rule(self, rule_id: str) -> AutoRule | None:
        row = self._conn.execute("SELECT * FROM rules WHERE rule_id = ?", (rule_id,)).fetchone()
        return self._row_to_rule(row) if row else None

    def toggle_rule(self, rule_id: str, enabled: bool) -> None:
        self._conn.execute(
            "UPDATE rules SET enabled = ? WHERE rule_id = ?",
            (1 if enabled else 0, rule_id),
        )
        self._conn.commit()

    def delete_rule(self, rule_id: str) -> None:
        self._conn.execute("DELETE FROM rules WHERE rule_id = ?", (rule_id,))
        self._conn.commit()

    def _mark_run(self, rule_id: str) -> None:
        self._conn.execute(
            "UPDATE rules SET last_run = ?, run_count = run_count + 1 WHERE rule_id = ?",
            (time.time(), rule_id),
        )
        self._conn.commit()

    # ── Scheduler ──

    def start(self, agent_controller: AgentController) -> None:
        """Start the background scheduler that evaluates rules.

        Defers task creation until the event loop is actually running.
        """
        if self._running:
            return
        self._running = True
        self._controller = agent_controller

        loop = asyncio.get_event_loop()
        loop.call_soon(self._create_task)
        logger.info("Rules engine scheduled to start")

    def _create_task(self) -> None:
        try:
            self._task = asyncio.create_task(self._scheduler_loop(self._controller))
            logger.info("Rules engine started")
        except RuntimeError:
            # Loop still not running — retry on next iteration
            asyncio.get_event_loop().call_soon(self._create_task)

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Rules engine stopped")

    async def _scheduler_loop(self, controller: AgentController) -> None:
        """Check schedule-based rules every 60 seconds."""
        while self._running:
            try:
                await self._evaluate_rules(controller)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Rules engine error")
            await asyncio.sleep(60)

    async def _evaluate_rules(self, controller: AgentController) -> None:
        """Check each enabled rule and execute if triggered."""
        rules = self.list_rules()
        now = time.time()

        for rule in rules:
            if not rule.enabled:
                continue

            if rule.trigger.startswith("schedule:"):
                interval = self._parse_interval(rule.trigger)
                if interval and (now - rule.last_run) >= interval:
                    logger.info("Executing scheduled rule: %s", rule.name)
                    self._mark_run(rule.rule_id)
                    await controller.handle_user_message(
                        f"[AUTO-RULE: {rule.name}] {rule.action_prompt}"
                    )

    @staticmethod
    def _parse_interval(trigger: str) -> float | None:
        """Parse 'schedule:30m' or 'schedule:2h' into seconds."""
        parts = trigger.split(":", 1)
        if len(parts) != 2:
            return None
        val = parts[1].strip()
        try:
            if val.endswith("m"):
                return float(val[:-1]) * 60
            if val.endswith("h"):
                return float(val[:-1]) * 3600
            if val.endswith("s"):
                return float(val[:-1])
            return float(val)
        except ValueError:
            return None

    def _row_to_rule(self, row: sqlite3.Row) -> AutoRule:
        return AutoRule(
            rule_id=row["rule_id"],
            name=row["name"],
            trigger=row["trigger"],
            action_prompt=row["action_prompt"],
            enabled=bool(row["enabled"]),
            last_run=row["last_run"],
            run_count=row["run_count"],
            created_at=row["created_at"],
        )

    def close(self) -> None:
        self.stop()
        self._conn.close()
