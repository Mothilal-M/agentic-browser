"""SQLite-backed long-term agent memory.

Stores facts the agent learns about the user across sessions.
Injected into the system prompt so the agent always has context.
"""

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MemoryEntry:
    id: int
    fact: str
    category: str    # preference, credential, personal, behavior, other
    created_at: float
    last_used: float
    use_count: int


class MemoryDB:
    CATEGORIES = ("preference", "credential", "personal", "behavior", "other")

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fact        TEXT NOT NULL,
                category    TEXT NOT NULL DEFAULT 'other',
                created_at  REAL NOT NULL,
                last_used   REAL NOT NULL,
                use_count   INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_memories_category
                ON memories(category);

            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(fact, content=memories, content_rowid=id);

            -- Triggers to keep FTS in sync
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, fact) VALUES (new.id, new.fact);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, fact) VALUES('delete', old.id, old.fact);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, fact) VALUES('delete', old.id, old.fact);
                INSERT INTO memories_fts(rowid, fact) VALUES (new.id, new.fact);
            END;
        """)
        self._conn.commit()

    def remember(self, fact: str, category: str = "other") -> MemoryEntry:
        """Store a new fact. Deduplicates if a very similar fact exists."""
        if category not in self.CATEGORIES:
            category = "other"

        # Check for near-duplicate
        existing = self.recall(fact, limit=1)
        if existing and existing[0].fact.lower().strip() == fact.lower().strip():
            # Update existing instead of creating duplicate
            self._conn.execute(
                "UPDATE memories SET last_used = ?, use_count = use_count + 1 WHERE id = ?",
                (time.time(), existing[0].id),
            )
            self._conn.commit()
            existing[0].use_count += 1
            return existing[0]

        now = time.time()
        cursor = self._conn.execute(
            "INSERT INTO memories (fact, category, created_at, last_used, use_count) VALUES (?, ?, ?, ?, 0)",
            (fact, category, now, now),
        )
        self._conn.commit()
        return MemoryEntry(
            id=cursor.lastrowid, fact=fact, category=category,
            created_at=now, last_used=now, use_count=0,
        )

    def recall(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """Search memories using full-text search."""
        try:
            rows = self._conn.execute(
                """SELECT m.* FROM memories m
                   JOIN memories_fts f ON m.id = f.rowid
                   WHERE memories_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # Fallback to LIKE if FTS query syntax is invalid
            rows = self._conn.execute(
                "SELECT * FROM memories WHERE fact LIKE ? ORDER BY last_used DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()

        entries = [self._row_to_entry(r) for r in rows]

        # Update last_used for recalled memories
        now = time.time()
        for e in entries:
            self._conn.execute(
                "UPDATE memories SET last_used = ?, use_count = use_count + 1 WHERE id = ?",
                (now, e.id),
            )
        if entries:
            self._conn.commit()

        return entries

    def get_all(self, limit: int = 100) -> list[MemoryEntry]:
        """Get all memories ordered by most recently used."""
        rows = self._conn.execute(
            "SELECT * FROM memories ORDER BY last_used DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def get_by_category(self, category: str, limit: int = 50) -> list[MemoryEntry]:
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE category = ? ORDER BY last_used DESC LIMIT ?",
            (category, limit),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def forget(self, memory_id: int) -> None:
        """Delete a specific memory."""
        self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._conn.commit()

    def format_for_prompt(self, limit: int = 30) -> str:
        """Format memories as text to inject into the agent's system prompt."""
        entries = self.get_all(limit=limit)
        if not entries:
            return ""

        lines = ["## What I remember about the user:"]
        for e in entries:
            lines.append(f"- [{e.category}] {e.fact}")
        return "\n".join(lines)

    def _row_to_entry(self, r: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=r["id"], fact=r["fact"], category=r["category"],
            created_at=r["created_at"], last_used=r["last_used"],
            use_count=r["use_count"],
        )

    def close(self) -> None:
        self._conn.close()
