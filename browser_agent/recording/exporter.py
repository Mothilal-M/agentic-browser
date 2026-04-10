"""Export session recordings as standalone HTML reports and JSON."""

from __future__ import annotations

import html
import json
import time
from datetime import datetime
from pathlib import Path

from browser_agent.recording.models import RecordedEvent, SessionRecording


def export_html(recording: SessionRecording, output_path: str | Path) -> Path:
    """Export a session recording as a beautiful standalone HTML report."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    events_html = []
    for i, ev in enumerate(recording.events):
        ts = datetime.fromtimestamp(ev.timestamp).strftime("%H:%M:%S")
        events_html.append(_render_event(ev, ts, i))

    started = datetime.fromtimestamp(recording.started_at).strftime("%Y-%m-%d %H:%M:%S")
    duration = f"{recording.duration_sec:.1f}s"

    report = _HTML_TEMPLATE.replace("{{TITLE}}", html.escape(recording.title))
    report = report.replace("{{SESSION_ID}}", recording.session_id[:8])
    report = report.replace("{{STARTED}}", started)
    report = report.replace("{{DURATION}}", duration)
    report = report.replace("{{EVENT_COUNT}}", str(recording.event_count))
    report = report.replace("{{SCREENSHOT_COUNT}}", str(recording.screenshot_count))
    report = report.replace("{{EVENTS}}", "\n".join(events_html))

    path.write_text(report, encoding="utf-8")
    return path


def export_json(recording: SessionRecording, output_path: str | Path) -> Path:
    """Export as JSON (without screenshots for smaller file size)."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "session_id": recording.session_id,
        "title": recording.title,
        "started_at": recording.started_at,
        "ended_at": recording.ended_at,
        "duration_sec": recording.duration_sec,
        "event_count": recording.event_count,
        "events": [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "tool_name": e.tool_name,
                "content": e.content,
                "detail": e.detail,
                "has_screenshot": bool(e.screenshot_b64),
            }
            for e in recording.events
        ],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _render_event(ev: RecordedEvent, ts: str, index: int) -> str:
    icon = {
        "user_msg": "\U0001f464",
        "assistant_msg": "\u2726",
        "tool_call": "\u2699",
        "tool_result": "\u2713",
        "screenshot": "\U0001f4f7",
        "error": "\u26a0",
    }.get(ev.event_type, "\u2022")

    color = {
        "user_msg": "#6c5ce7",
        "assistant_msg": "#a855f7",
        "tool_call": "#10b981",
        "tool_result": "#10b981",
        "error": "#ef4444",
    }.get(ev.event_type, "#888")

    label = {
        "user_msg": "USER",
        "assistant_msg": "AI AGENT",
        "tool_call": f"TOOL: {ev.tool_name}",
        "tool_result": f"RESULT: {ev.tool_name}",
        "error": "ERROR",
    }.get(ev.event_type, ev.event_type.upper())

    content_escaped = html.escape(ev.content[:500])

    screenshot_html = ""
    if ev.screenshot_b64:
        screenshot_html = (
            f'<div class="screenshot">'
            f'<img src="data:image/jpeg;base64,{ev.screenshot_b64}" '
            f'loading="lazy" onclick="this.classList.toggle(\'expanded\')" />'
            f'</div>'
        )

    return f"""
    <div class="event" style="--accent: {color}">
        <div class="event-header">
            <span class="event-icon">{icon}</span>
            <span class="event-label" style="color: {color}">{label}</span>
            <span class="event-time">{ts}</span>
        </div>
        <div class="event-content">{content_escaped}</div>
        {screenshot_html}
    </div>"""


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}} — Session Report</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Segoe UI', 'SF Pro Display', -apple-system, sans-serif;
    background: #08080f; color: #eeeef5; line-height: 1.6;
}
.container { max-width: 900px; margin: 0 auto; padding: 40px 24px; }

/* Header */
.header {
    text-align: center; padding: 40px 0 30px;
    border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 30px;
}
.header h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
.header .subtitle { color: #9898be; font-size: 14px; }
.meta {
    display: flex; justify-content: center; gap: 24px; margin-top: 16px;
    flex-wrap: wrap;
}
.meta-item {
    background: rgba(108,92,231,0.08); border: 1px solid rgba(108,92,231,0.15);
    border-radius: 10px; padding: 8px 16px; font-size: 12px; color: #a855f7;
}

/* Events */
.timeline { position: relative; padding-left: 24px; }
.timeline::before {
    content: ''; position: absolute; left: 11px; top: 0; bottom: 0;
    width: 2px; background: rgba(255,255,255,0.04);
}
.event {
    position: relative; margin-bottom: 16px; padding: 14px 18px;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);
    border-radius: 12px; border-left: 3px solid var(--accent);
}
.event::before {
    content: ''; position: absolute; left: -19px; top: 18px;
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent); border: 2px solid #08080f;
}
.event-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.event-icon { font-size: 14px; }
.event-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;
}
.event-time { margin-left: auto; color: rgba(255,255,255,0.2); font-size: 11px; }
.event-content {
    font-size: 13px; color: #c8c8e0; white-space: pre-wrap; word-break: break-word;
}

/* Screenshots */
.screenshot { margin-top: 10px; }
.screenshot img {
    max-width: 100%; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);
    cursor: pointer; transition: max-height 0.3s;
    max-height: 200px; object-fit: cover; object-position: top;
}
.screenshot img.expanded { max-height: none; }

/* Footer */
.footer {
    text-align: center; margin-top: 40px; padding-top: 20px;
    border-top: 1px solid rgba(255,255,255,0.04);
    color: rgba(255,255,255,0.15); font-size: 11px;
}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>{{TITLE}}</h1>
        <div class="subtitle">Session Recording Report</div>
        <div class="meta">
            <div class="meta-item">ID: {{SESSION_ID}}</div>
            <div class="meta-item">Started: {{STARTED}}</div>
            <div class="meta-item">Duration: {{DURATION}}</div>
            <div class="meta-item">{{EVENT_COUNT}} events</div>
            <div class="meta-item">{{SCREENSHOT_COUNT}} screenshots</div>
        </div>
    </div>
    <div class="timeline">
        {{EVENTS}}
    </div>
    <div class="footer">
        Generated by AI Browser Agent
    </div>
</div>
</body>
</html>"""
