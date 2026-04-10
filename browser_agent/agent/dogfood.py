"""Exploratory QA / Dogfood mode — systematically test a web app and report bugs.

The agent crawls the target URL, clicks every link/button, fills forms,
and documents issues with repro steps and screenshots.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class QAIssue:
    severity: str       # critical, high, medium, low
    title: str
    description: str
    repro_steps: list[str]
    url: str
    screenshot_b64: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class QAReport:
    target_url: str
    started_at: float = field(default_factory=time.time)
    ended_at: float = 0.0
    pages_tested: int = 0
    elements_tested: int = 0
    issues: list[QAIssue] = field(default_factory=list)

    @property
    def duration_sec(self) -> float:
        return (self.ended_at or time.time()) - self.started_at

    def to_markdown(self) -> str:
        lines = [
            f"# QA Report: {self.target_url}",
            f"",
            f"**Duration**: {self.duration_sec:.0f}s | "
            f"**Pages tested**: {self.pages_tested} | "
            f"**Elements tested**: {self.elements_tested} | "
            f"**Issues found**: {len(self.issues)}",
            f"",
        ]

        if not self.issues:
            lines.append("No issues found! The application passed exploratory testing.")
            return "\n".join(lines)

        # Group by severity
        for sev in ("critical", "high", "medium", "low"):
            sev_issues = [i for i in self.issues if i.severity == sev]
            if not sev_issues:
                continue
            icon = {"critical": "\U0001f534", "high": "\U0001f7e0", "medium": "\U0001f7e1", "low": "\U0001f535"}[sev]
            lines.append(f"## {icon} {sev.upper()} ({len(sev_issues)})")
            lines.append("")
            for idx, issue in enumerate(sev_issues, 1):
                lines.append(f"### {idx}. {issue.title}")
                lines.append(f"**URL**: {issue.url}")
                lines.append(f"**Description**: {issue.description}")
                lines.append(f"**Repro steps**:")
                for step_idx, step in enumerate(issue.repro_steps, 1):
                    lines.append(f"  {step_idx}. {step}")
                lines.append("")

        return "\n".join(lines)


def build_dogfood_prompt(target_url: str, focus: str = "") -> str:
    """Build the prompt that tells the agent to systematically test an app."""
    focus_line = f"\n\nFocus area: {focus}" if focus else ""

    return (
        f"You are now in EXPLORATORY QA MODE. Your job is to systematically test "
        f"the web application at {target_url} and find bugs, broken features, and UX issues.\n\n"
        f"## Testing procedure:\n"
        f"1. Navigate to {target_url}\n"
        f"2. Take a screenshot and understand the page layout\n"
        f"3. Test EVERY visible interactive element:\n"
        f"   - Click all buttons and links\n"
        f"   - Fill and submit all forms (use test data)\n"
        f"   - Test navigation (back/forward, breadcrumbs, menus)\n"
        f"   - Scroll to find hidden content\n"
        f"   - Check for broken images, missing text, layout issues\n"
        f"4. For each page you visit:\n"
        f"   - Take a screenshot\n"
        f"   - List all interactive elements\n"
        f"   - Test each one\n"
        f"   - Note any errors, broken UI, or unexpected behavior\n"
        f"5. Document EVERY issue you find with:\n"
        f"   - Severity: critical (crash/data loss), high (broken feature), "
        f"medium (UX issue), low (cosmetic)\n"
        f"   - Clear title\n"
        f"   - Step-by-step repro instructions\n"
        f"   - What you expected vs what happened\n\n"
        f"## What counts as a bug:\n"
        f"- Buttons that don't work\n"
        f"- Forms that fail to submit\n"
        f"- Broken links (404 pages)\n"
        f"- Missing or garbled text\n"
        f"- Layout overflow or overlapping elements\n"
        f"- Slow page loads (> 5 seconds)\n"
        f"- Console errors (if visible in the page)\n"
        f"- Accessibility issues (missing labels, no keyboard navigation)\n\n"
        f"## Output format:\n"
        f"After testing, provide a structured QA report in markdown with all "
        f"issues grouped by severity.{focus_line}\n\n"
        f"Begin testing now. Start by navigating to {target_url}."
    )
