"""Skill data models — a recorded workflow that can be replayed."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class SkillStep:
    """A single action in a skill workflow."""
    tool_name: str          # e.g. "navigate_to", "click_element", "type_text"
    args: dict              # e.g. {"url": "https://..."} or {"selector": "#btn", "text": "hello"}
    description: str = ""   # human-readable: "Navigate to LinkedIn"
    wait_after_ms: int = 500


@dataclass
class Skill:
    """A named, replayable workflow made of ordered steps."""
    skill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: list[SkillStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    run_count: int = 0

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "steps": [
                {"tool_name": s.tool_name, "args": s.args,
                 "description": s.description, "wait_after_ms": s.wait_after_ms}
                for s in self.steps
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "run_count": self.run_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Skill:
        steps = [
            SkillStep(
                tool_name=s["tool_name"],
                args=s.get("args", {}),
                description=s.get("description", ""),
                wait_after_ms=s.get("wait_after_ms", 500),
            )
            for s in data.get("steps", [])
        ]
        return cls(
            skill_id=data.get("skill_id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=steps,
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            run_count=data.get("run_count", 0),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> Skill:
        return cls.from_dict(json.loads(text))
