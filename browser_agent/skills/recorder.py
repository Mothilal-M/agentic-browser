"""Skill recorder — captures tool calls from an agent run into a Skill."""

from browser_agent.skills.models import Skill, SkillStep


class SkillRecorder:
    """Records tool calls during an agent run, then saves as a replayable Skill."""

    def __init__(self) -> None:
        self._recording = False
        self._steps: list[SkillStep] = []
        self._name = ""

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self, name: str = "") -> None:
        self._recording = True
        self._steps = []
        self._name = name

    def record_step(self, tool_name: str, args: dict, description: str = "") -> None:
        if not self._recording:
            return
        # Skip meta tools — don't record screenshot/recall/remember
        if tool_name in ("take_screenshot", "get_page_elements", "recall", "remember"):
            return
        self._steps.append(
            SkillStep(tool_name=tool_name, args=args, description=description)
        )

    def stop(self) -> Skill | None:
        self._recording = False
        if not self._steps:
            return None
        skill = Skill(name=self._name, steps=self._steps)
        # Auto-generate description from steps
        summaries = []
        for s in self._steps[:5]:
            summaries.append(f"{s.tool_name}({', '.join(f'{k}={v!r}' for k, v in s.args.items())})")
        if len(self._steps) > 5:
            summaries.append(f"...+{len(self._steps) - 5} more steps")
        skill.description = " → ".join(summaries)
        self._steps = []
        return skill
