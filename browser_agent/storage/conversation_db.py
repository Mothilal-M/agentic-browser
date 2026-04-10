"""SQLite-backed persistent conversation storage.

Stores all chat messages (user, assistant, tool) across sessions.
Supports multiple threads with search and resume.
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StoredMessage:
    id: int
    thread_id: str
    role: str          # user, assistant, tool, error, thinking
    content: str
    detail: str = ""   # tool result detail
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class Thread:
    thread_id: str
    title: str
    created_at: float
    updated_at: float
    message_count: int = 0


class ConversationDB:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS threads (
                thread_id   TEXT PRIMARY KEY,
                title       TEXT NOT NULL DEFAULT 'New Chat',
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id   TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL DEFAULT '',
                detail      TEXT NOT NULL DEFAULT '',
                timestamp   REAL NOT NULL,
                metadata    TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (thread_id) REFERENCES threads(thread_id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_thread
                ON messages(thread_id, timestamp);

            CREATE INDEX IF NOT EXISTS idx_messages_search
                ON messages(content);
        """)
        self._conn.commit()

    # ── Thread operations ──

    def create_thread(self, title: str = "New Chat") -> Thread:
        now = time.time()
        thread_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO threads (thread_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (thread_id, title, now, now),
        )
        self._conn.commit()
        return Thread(thread_id=thread_id, title=title, created_at=now, updated_at=now)

    def list_threads(self, limit: int = 50) -> list[Thread]:
        rows = self._conn.execute(
            """SELECT t.*, COUNT(m.id) as msg_count
               FROM threads t LEFT JOIN messages m ON t.thread_id = m.thread_id
               GROUP BY t.thread_id
               ORDER BY t.updated_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            Thread(
                thread_id=r["thread_id"],
                title=r["title"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                message_count=r["msg_count"],
            )
            for r in rows
        ]

    def update_thread_title(self, thread_id: str, title: str) -> None:
        self._conn.execute(
            "UPDATE threads SET title = ?, updated_at = ? WHERE thread_id = ?",
            (title, time.time(), thread_id),
        )
        self._conn.commit()

    def delete_thread(self, thread_id: str) -> None:
        self._conn.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
        self._conn.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))
        self._conn.commit()

    # ── Message operations ──

    def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        detail: str = "",
        metadata: dict | None = None,
    ) -> StoredMessage:
        now = time.time()
        meta_json = json.dumps(metadata or {})
        cursor = self._conn.execute(
            "INSERT INTO messages (thread_id, role, content, detail, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (thread_id, role, content, detail, now, meta_json),
        )
        self._conn.execute(
            "UPDATE threads SET updated_at = ? WHERE thread_id = ?",
            (now, thread_id),
        )
        self._conn.commit()
        return StoredMessage(
            id=cursor.lastrowid,
            thread_id=thread_id,
            role=role,
            content=content,
            detail=detail,
            timestamp=now,
            metadata=metadata or {},
        )

    def get_messages(self, thread_id: str, limit: int = 200) -> list[StoredMessage]:
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE thread_id = ? ORDER BY timestamp ASC LIMIT ?",
            (thread_id, limit),
        ).fetchall()
        return [
            StoredMessage(
                id=r["id"],
                thread_id=r["thread_id"],
                role=r["role"],
                content=r["content"],
                detail=r["detail"],
                timestamp=r["timestamp"],
                metadata=json.loads(r["metadata"]),
            )
            for r in rows
        ]

    def search_messages(self, query: str, limit: int = 30) -> list[StoredMessage]:
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [
            StoredMessage(
                id=r["id"],
                thread_id=r["thread_id"],
                role=r["role"],
                content=r["content"],
                detail=r["detail"],
                timestamp=r["timestamp"],
                metadata=json.loads(r["metadata"]),
            )
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()
