"""Predictive browsing — learns user's browsing patterns and suggests actions.

Tracks: which URLs visited, at what time of day, what actions performed.
Uses this to predict what the user wants to do next and pre-suggest actions.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class BrowsingPattern:
    url: str
    title: str
    hour: int        # 0-23, hour of day when visited
    day_of_week: int # 0=Monday, 6=Sunday
    visit_count: int
    last_visited: float


@dataclass
class Suggestion:
    text: str        # "Open LinkedIn — you usually check it around 10am"
    url: str
    confidence: float  # 0-1
    reason: str


class PatternTracker:
    """Learns browsing patterns and generates suggestions."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS page_visits (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT NOT NULL,
                title       TEXT NOT NULL DEFAULT '',
                hour        INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL,
                timestamp   REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS action_patterns (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                context     TEXT NOT NULL DEFAULT '',
                hour        INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL,
                timestamp   REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_visits_url ON page_visits(url);
            CREATE INDEX IF NOT EXISTS idx_visits_hour ON page_visits(hour);
        """)
        self._conn.commit()

    def track_visit(self, url: str, title: str = "") -> None:
        """Record a page visit."""
        now = datetime.now()
        self._conn.execute(
            "INSERT INTO page_visits (url, title, hour, day_of_week, timestamp) VALUES (?, ?, ?, ?, ?)",
            (url, title, now.hour, now.weekday(), time.time()),
        )
        self._conn.commit()

    def track_action(self, action_type: str, context: str = "") -> None:
        """Record an action pattern (e.g., 'apply_job', 'check_email')."""
        now = datetime.now()
        self._conn.execute(
            "INSERT INTO action_patterns (action_type, context, hour, day_of_week, timestamp) VALUES (?, ?, ?, ?, ?)",
            (action_type, context, now.hour, now.weekday(), time.time()),
        )
        self._conn.commit()

    def get_suggestions(self, limit: int = 5) -> list[Suggestion]:
        """Generate suggestions based on current time and past patterns."""
        now = datetime.now()
        current_hour = now.hour
        current_dow = now.weekday()
        suggestions = []

        # Find URLs commonly visited at this hour (±1 hour)
        rows = self._conn.execute(
            """SELECT url, title, COUNT(*) as cnt, MAX(timestamp) as last_ts
               FROM page_visits
               WHERE hour BETWEEN ? AND ?
               GROUP BY url
               ORDER BY cnt DESC
               LIMIT ?""",
            (current_hour - 1, current_hour + 1, limit),
        ).fetchall()

        for row in rows:
            cnt = row["cnt"]
            if cnt < 2:
                continue
            confidence = min(cnt / 10, 1.0)

            hour_str = f"{current_hour}:00"
            suggestions.append(Suggestion(
                text=f"Open {row['title'] or row['url']} — you visit this around {hour_str}",
                url=row["url"],
                confidence=confidence,
                reason=f"Visited {cnt} times at this hour",
            ))

        # Find URLs commonly visited on this day of week
        rows = self._conn.execute(
            """SELECT url, title, COUNT(*) as cnt
               FROM page_visits
               WHERE day_of_week = ?
               GROUP BY url
               ORDER BY cnt DESC
               LIMIT ?""",
            (current_dow, 3),
        ).fetchall()

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for row in rows:
            cnt = row["cnt"]
            if cnt < 3:
                continue
            # Skip if already suggested
            if any(s.url == row["url"] for s in suggestions):
                continue
            suggestions.append(Suggestion(
                text=f"Open {row['title'] or row['url']} — you often visit on {day_names[current_dow]}s",
                url=row["url"],
                confidence=min(cnt / 15, 0.8),
                reason=f"Visited {cnt} times on {day_names[current_dow]}",
            ))

        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:limit]

    def get_top_sites(self, limit: int = 10) -> list[BrowsingPattern]:
        """Get most visited sites with pattern info."""
        rows = self._conn.execute(
            """SELECT url, title,
                      CAST(AVG(hour) AS INTEGER) as avg_hour,
                      CAST(AVG(day_of_week) AS INTEGER) as avg_dow,
                      COUNT(*) as cnt,
                      MAX(timestamp) as last_ts
               FROM page_visits
               GROUP BY url
               ORDER BY cnt DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            BrowsingPattern(
                url=r["url"], title=r["title"],
                hour=r["avg_hour"], day_of_week=r["avg_dow"],
                visit_count=r["cnt"], last_visited=r["last_ts"],
            )
            for r in rows
        ]

    def format_suggestions_for_prompt(self) -> str:
        """Format suggestions as text to optionally inject into agent context."""
        suggestions = self.get_suggestions(limit=3)
        if not suggestions:
            return ""
        lines = ["## Browsing suggestions (based on your patterns):"]
        for s in suggestions:
            lines.append(f"- {s.text} (confidence: {s.confidence:.0%})")
        return "\n".join(lines)

    def close(self) -> None:
        self._conn.close()
