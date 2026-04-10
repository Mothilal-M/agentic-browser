"""User profile store — personal info for form auto-fill.

Stores key-value pairs like name, email, phone, address, resume path.
Injected into agent context so it can auto-fill forms.
"""

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProfileField:
    key: str        # e.g. "full_name", "email", "phone"
    value: str
    label: str      # human-readable: "Full Name", "Email Address"
    updated_at: float


# Default fields to create on first run
DEFAULT_FIELDS = [
    ("full_name", "", "Full Name"),
    ("email", "", "Email Address"),
    ("phone", "", "Phone Number"),
    ("address", "", "Street Address"),
    ("city", "", "City"),
    ("state", "", "State / Province"),
    ("zip_code", "", "ZIP / Postal Code"),
    ("country", "", "Country"),
    ("date_of_birth", "", "Date of Birth"),
    ("linkedin_url", "", "LinkedIn URL"),
    ("github_url", "", "GitHub URL"),
    ("resume_path", "", "Resume File Path"),
    ("current_company", "", "Current Company"),
    ("current_title", "", "Current Job Title"),
    ("years_experience", "", "Years of Experience"),
]


class UserProfile:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL DEFAULT '',
                label       TEXT NOT NULL DEFAULT '',
                updated_at  REAL NOT NULL
            )
        """)
        self._conn.commit()

        # Insert defaults if empty
        count = self._conn.execute("SELECT COUNT(*) FROM profile").fetchone()[0]
        if count == 0:
            now = time.time()
            self._conn.executemany(
                "INSERT INTO profile (key, value, label, updated_at) VALUES (?, ?, ?, ?)",
                [(k, v, l, now) for k, v, l in DEFAULT_FIELDS],
            )
            self._conn.commit()

    def get(self, key: str) -> str:
        row = self._conn.execute("SELECT value FROM profile WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else ""

    def set(self, key: str, value: str, label: str = "") -> None:
        now = time.time()
        existing = self._conn.execute("SELECT key FROM profile WHERE key = ?", (key,)).fetchone()
        if existing:
            self._conn.execute(
                "UPDATE profile SET value = ?, updated_at = ? WHERE key = ?",
                (value, now, key),
            )
        else:
            self._conn.execute(
                "INSERT INTO profile (key, value, label, updated_at) VALUES (?, ?, ?, ?)",
                (key, value, label or key, now),
            )
        self._conn.commit()

    def get_all(self) -> list[ProfileField]:
        rows = self._conn.execute("SELECT * FROM profile ORDER BY rowid").fetchall()
        return [
            ProfileField(key=r["key"], value=r["value"], label=r["label"], updated_at=r["updated_at"])
            for r in rows
        ]

    def get_filled(self) -> list[ProfileField]:
        """Only return fields that have a value."""
        return [f for f in self.get_all() if f.value.strip()]

    def to_dict(self) -> dict[str, str]:
        """Return all filled fields as {key: value}."""
        return {f.key: f.value for f in self.get_filled()}

    def format_for_prompt(self) -> str:
        """Format profile as text for the agent's system prompt."""
        filled = self.get_filled()
        if not filled:
            return ""
        lines = ["## User profile (for auto-filling forms):"]
        for f in filled:
            lines.append(f"- {f.label}: {f.value}")
        return "\n".join(lines)

    def close(self) -> None:
        self._conn.close()
