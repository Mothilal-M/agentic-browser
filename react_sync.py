from pathlib import Path
import sys

from dotenv import load_dotenv
from agentflow.core import Agent, StateGraph, ToolNode
from agentflow.core.state import AgentState, Message
from agentflow.core.skills import SkillConfig
from agentflow.storage.checkpointer import InMemoryCheckpointer
from agentflow.utils.constants import END

load_dotenv()

checkpointer = InMemoryCheckpointer()
SKILLS_DIR = Path(__file__).parent / "generated_skills"

CODING_SKILLS: dict[str, str] = {
        "code-review": """---
name: code-review
description: Find bugs, regressions, and missing tests in code changes.
metadata:
    triggers:
        - review this pull request
        - do a code review
        - find issues in this code
    tags:
        - coding
        - quality
        - review
    priority: 90
---

Perform a code review focused on correctness and risk.

Checklist:
- Identify bugs and behavioral regressions.
- Validate error handling and edge cases.
- Call out missing tests and verification gaps.
- Prioritize findings by severity.
""",
        "debugger": """---
name: debugger
description: Debug stack traces, runtime errors, and broken flows.
metadata:
    triggers:
        - debug this error
        - fix this exception
        - why is this failing
    tags:
        - coding
        - debugging
    priority: 95
---

Use a structured debugging workflow.

Checklist:
- Reproduce the failure reliably.
- Narrow root cause to the smallest failing unit.
- Patch with minimal surface area.
- Verify the fix and look for nearby regressions.
""",
        "refactoring": """---
name: refactoring
description: Improve structure and readability without changing behavior.
metadata:
    triggers:
        - refactor this
        - clean up this code
        - improve maintainability
    tags:
        - coding
        - refactor
    priority: 70
---

Refactor conservatively while preserving behavior.

Checklist:
- Keep public APIs stable unless explicitly requested.
- Prefer small, testable transformations.
- Remove duplication and simplify control flow.
- Preserve performance characteristics unless improving them intentionally.
""",
        "test-generator": """---
name: test-generator
description: Create focused tests for edge cases and regressions.
metadata:
    triggers:
        - write tests
        - add unit tests
        - cover edge cases
    tags:
        - coding
        - testing
    priority: 85
---

Generate tests that prove behavior.

Checklist:
- Cover success path, error path, and edge cases.
- Prefer deterministic, isolated tests.
- Add regression tests for known failures.
- Keep tests readable and fast.
""",
        "security-review": """---
name: security-review
description: Identify and fix common security issues in application code.
metadata:
    triggers:
        - security review
        - find vulnerabilities
        - harden this code
    tags:
        - coding
        - security
    priority: 100
---

Run a lightweight secure coding review.

Checklist:
- Validate input handling and output encoding.
- Check authz/authn assumptions.
- Look for sensitive data leaks.
- Suggest concrete remediations with minimal code churn.
""",
}


def generate_coding_skills(skills_dir: Path = SKILLS_DIR) -> list[Path]:
        """Create a default set of coding skills as SKILL.md files."""
        created: list[Path] = []
        skills_dir.mkdir(parents=True, exist_ok=True)
        for skill_name, skill_md in CODING_SKILLS.items():
                skill_folder = skills_dir / skill_name
                skill_folder.mkdir(parents=True, exist_ok=True)
                skill_file = skill_folder / "SKILL.md"
                skill_file.write_text(skill_md.strip() + "\n", encoding="utf-8")
                created.append(skill_file)
        return created

def get_weather(location: str) -> str:
    """Get weather for a location."""
    return f"The weather in {location} is sunny"

tool_node = ToolNode([get_weather])

agent = Agent(
    model="gemini-3-flash-preview",
    provider="google",
    system_prompt=[{"role": "system", "content": "You are a helpful assistant. Your name is Jack."}],
    trim_context=True,
    reasoning_config=True,
    tool_node=tool_node,
    skills=SkillConfig(
        skills_dir=str(SKILLS_DIR),
        inject_trigger_table=True,
        hot_reload=True,
    ),
)

def should_use_tools(state: AgentState) -> str:
    if not state.context or len(state.context) == 0:
        return "TOOL"
    last_message = state.context[-1]
    if (
        hasattr(last_message, "tools_calls")
        and last_message.tools_calls
        and len(last_message.tools_calls) > 0
        and last_message.role == "assistant"
    ):
        return "TOOL"
    if last_message.role == "tool":
        return "MAIN"
    return END

graph = StateGraph()
graph.add_node("MAIN", agent)
graph.add_node("TOOL", tool_node)
graph.add_conditional_edges("MAIN", should_use_tools, {"TOOL": "TOOL", END: END})
graph.add_edge("TOOL", "MAIN")
graph.set_entry_point("MAIN")

app = graph.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].strip().lower() == "skill":
        files = generate_coding_skills()
        print("Generated coding skills:")
        for f in files:
            print(f"- {f}")
        raise SystemExit(0)

    inp = {"messages": [Message.text_message("What is the weather in New York City?")]}
    config = {"thread_id": "12345", "recursion_limit": 10}
    res = app.invoke(inp, config=config)

    for msg in res["messages"]:
        print(f"[{msg.role}] {msg}")
