"""Lightweight markdown-to-HTML converter using design tokens."""

import html
import re

from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    ACCENT_SECONDARY,
    DARK_SURFACE,
    DARK_TEXT,
    DARK_TEXT_SECONDARY,
    FONT_BASE,
    FONT_LG,
    FONT_MD,
    FONT_MONO,
    FONT_SM,
    FONT_XS,
    GLASS_BORDER,
    GLASS_HOVER,
)

# Pre-compute style fragments
_CODE_BG = f"background:rgba(18,18,42,0.8); color:{DARK_TEXT_SECONDARY};"
_CODE_BORDER = f"border:1px solid {GLASS_BORDER};"
_CODE_FONT = f"font-family:{FONT_MONO};"
_TEXT_COLOR = f"color:{DARK_TEXT};"
_MUTED = f"color:{DARK_TEXT_SECONDARY};"


def md_to_html(text: str) -> str:
    text = html.escape(text)
    lines = text.split("\n")
    result = []
    in_table = False
    in_code_block = False
    in_list = False
    table_rows: list[list[str]] = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                in_code_block = False
                result.append("</pre>")
            else:
                in_code_block = True
                result.append(
                    f'<pre style="{_CODE_BG} padding:10px 14px; border-radius:8px;'
                    f' font-size:{FONT_SM}px; {_CODE_FONT} {_CODE_BORDER} margin:6px 0;'
                    f' white-space:pre-wrap; word-wrap:break-word; overflow-wrap:break-word;">'
                )
            continue

        if in_code_block:
            result.append(line)
            continue

        if "|" in stripped and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.match(r"^:?-+:?$", c) for c in cells):
                continue
            table_rows.append(cells)
            in_table = True
            continue
        elif in_table:
            result.append(_render_table(table_rows))
            table_rows = []
            in_table = False

        if stripped.startswith("### "):
            result.append(f'<p style="font-size:{FONT_BASE}px; font-weight:700; {_TEXT_COLOR} margin:10px 0 4px 0;">{_inline(stripped[4:])}</p>')
            continue
        if stripped.startswith("## "):
            result.append(f'<p style="font-size:{FONT_MD}px; font-weight:700; {_TEXT_COLOR} margin:10px 0 4px 0;">{_inline(stripped[3:])}</p>')
            continue
        if stripped.startswith("# "):
            result.append(f'<p style="font-size:{FONT_LG}px; font-weight:700; {_TEXT_COLOR} margin:10px 0 6px 0;">{_inline(stripped[2:])}</p>')
            continue

        m = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if m:
            in_list = True
            result.append(
                f'<p style="margin:2px 0 2px 4px; {_TEXT_COLOR} font-size:{FONT_BASE}px;">'
                f'<span style="color:{ACCENT_PRIMARY}; font-weight:700; min-width:20px; '
                f'display:inline-block;">{m.group(1)}.</span> {_inline(m.group(2))}</p>'
            )
            continue

        if stripped.startswith(("- ", "* ")):
            in_list = True
            result.append(
                f'<p style="margin:2px 0 2px 4px; {_TEXT_COLOR} font-size:{FONT_BASE}px;">'
                f'<span style="color:{ACCENT_PRIMARY}; margin-right:6px;">&#9670;</span>'
                f"{_inline(stripped[2:])}</p>"
            )
            continue

        if in_list and stripped == "":
            in_list = False

        if stripped == "":
            result.append('<p style="margin:4px 0;"></p>')
            continue

        result.append(f'<p style="margin:2px 0; {_TEXT_COLOR} font-size:{FONT_BASE}px; line-height:1.6;">{_inline(stripped)}</p>')

    if in_table and table_rows:
        result.append(_render_table(table_rows))

    return "\n".join(result)


def _inline(text: str) -> str:
    text = re.sub(
        r"\*\*(.+?)\*\*",
        rf'<span style="font-weight:700; {_TEXT_COLOR}">\1</span>',
        text,
    )
    text = re.sub(
        r"__(.+?)__",
        rf'<span style="font-weight:700; {_TEXT_COLOR}">\1</span>',
        text,
    )
    text = re.sub(
        r"\*(.+?)\*",
        rf'<span style="font-style:italic; {_MUTED}">\1</span>',
        text,
    )
    text = re.sub(
        r"`(.+?)`",
        rf'<span style="{_CODE_BG} color:{ACCENT_SECONDARY}; padding:1px 6px;'
        rf' border-radius:4px; {_CODE_FONT} font-size:{FONT_SM}px; {_CODE_BORDER}">\1</span>',
        text,
    )
    return text


def _render_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    html_parts = [
        f'<table style="border-collapse:collapse; width:100%; margin:10px 0;'
        f' font-size:{FONT_SM}px; border-radius:10px; overflow:hidden;'
        f' border:1px solid {GLASS_BORDER}; table-layout:fixed; word-wrap:break-word;">'
    ]
    for i, row in enumerate(rows):
        if i == 0:
            html_parts.append(f'<tr style="background:rgba(108,92,231,0.10); border-bottom:1px solid rgba(108,92,231,0.25);">')
            for cell in row:
                html_parts.append(
                    f'<th style="padding:8px 10px; text-align:left; font-weight:700;'
                    f' color:{ACCENT_SECONDARY}; font-size:{FONT_XS}px;'
                    f' text-transform:uppercase; letter-spacing:0.5px; word-wrap:break-word;">{_inline(cell)}</th>'
                )
            html_parts.append("</tr>")
        else:
            bg = GLASS_HOVER if i % 2 == 0 else "transparent"
            html_parts.append(f'<tr style="background:{bg}; border-bottom:1px solid rgba(255,255,255,0.03);">')
            for j, cell in enumerate(row):
                weight = "600" if j == 0 else "400"
                color = DARK_TEXT if j == 0 else DARK_TEXT_SECONDARY
                html_parts.append(
                    f'<td style="padding:6px 10px; color:{color}; font-weight:{weight};'
                    f' word-wrap:break-word; overflow-wrap:break-word;">'
                    f"{_inline(cell)}</td>"
                )
            html_parts.append("</tr>")
    html_parts.append("</table>")
    return "\n".join(html_parts)
