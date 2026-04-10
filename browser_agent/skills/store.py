"""SQLite-backed skill store — CRUD for saved workflows."""

import json
import sqlite3
import time
from pathlib import Path

from browser_agent.skills.models import Skill


class SkillStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id    TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                steps_json  TEXT NOT NULL DEFAULT '[]',
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL,
                run_count   INTEGER NOT NULL DEFAULT 0
            );
        """)
        self._conn.commit()

    def save(self, skill: Skill) -> Skill:
        skill.updated_at = time.time()
        self._conn.execute(
            """INSERT OR REPLACE INTO skills
               (skill_id, name, description, steps_json, created_at, updated_at, run_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                skill.skill_id, skill.name, skill.description,
                json.dumps([s.__dict__ for s in skill.steps]),
                skill.created_at, skill.updated_at, skill.run_count,
            ),
        )
        self._conn.commit()
        return skill

    def get(self, skill_id: str) -> Skill | None:
        row = self._conn.execute(
            "SELECT * FROM skills WHERE skill_id = ?", (skill_id,)
        ).fetchone()
        return self._row_to_skill(row) if row else None

    def get_by_name(self, name: str) -> Skill | None:
        row = self._conn.execute(
            "SELECT * FROM skills WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        return self._row_to_skill(row) if row else None

    def list_all(self, limit: int = 50) -> list[Skill]:
        rows = self._conn.execute(
            "SELECT * FROM skills ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_skill(r) for r in rows]

    def delete(self, skill_id: str) -> None:
        self._conn.execute("DELETE FROM skills WHERE skill_id = ?", (skill_id,))
        self._conn.commit()

    def increment_run_count(self, skill_id: str) -> None:
        self._conn.execute(
            "UPDATE skills SET run_count = run_count + 1, updated_at = ? WHERE skill_id = ?",
            (time.time(), skill_id),
        )
        self._conn.commit()

    def _row_to_skill(self, row: sqlite3.Row) -> Skill:
        data = {
            "skill_id": row["skill_id"],
            "name": row["name"],
            "description": row["description"],
            "steps": json.loads(row["steps_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "run_count": row["run_count"],
        }
        return Skill.from_dict(data)

    # ── Import / Export ──

    def export_skill(self, skill_id: str, output_path: str) -> str | None:
        """Export a skill as a JSON file. Returns the path or None."""
        from pathlib import Path as P

        skill = self.get(skill_id)
        if not skill:
            return None
        p = P(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(skill.to_json(), encoding="utf-8")
        return str(p)

    def import_skill(self, file_path: str) -> Skill | None:
        """Import a skill from a JSON file. Returns the skill or None."""
        from pathlib import Path as P

        p = P(file_path)
        if not p.exists():
            return None
        try:
            skill = Skill.from_json(p.read_text(encoding="utf-8"))
            # Avoid ID collision — generate new ID on import
            import uuid
            skill.skill_id = str(uuid.uuid4())
            return self.save(skill)
        except (json.JSONDecodeError, KeyError):
            return None

    def export_all(self, output_dir: str) -> list[str]:
        """Export all skills as individual JSON files. Returns list of paths."""
        from pathlib import Path as P

        out = P(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = []
        for skill in self.list_all():
            safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in skill.name)
            path = out / f"{safe_name}.json"
            path.write_text(skill.to_json(), encoding="utf-8")
            paths.append(str(path))
        return paths

    def close(self) -> None:
        self._conn.close()
