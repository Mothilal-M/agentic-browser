"""Snapshot diffing — structural and visual comparison of page states.

Structural: compare accessibility tree text line-by-line.
Visual: compare screenshots pixel-by-pixel (via QImage).
"""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def diff_snapshots(before: str, after: str) -> str:
    """Structural diff of two accessibility tree snapshots.

    Returns a unified diff string with + for additions, - for removals.
    """
    before_lines = before.strip().splitlines()
    after_lines = after.strip().splitlines()

    diff = difflib.unified_diff(
        before_lines, after_lines,
        fromfile="before", tofile="after",
        lineterm="",
    )
    result = list(diff)
    if not result:
        return "No structural changes detected."

    # Format nicely
    changes = []
    added = 0
    removed = 0
    for line in result:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            changes.append(f"  \u2795 {line[1:]}")
            added += 1
        elif line.startswith("-"):
            changes.append(f"  \u2796 {line[1:]}")
            removed += 1

    header = f"Snapshot diff: {added} added, {removed} removed"
    return header + "\n" + "\n".join(changes)


def diff_screenshots_pixel(before_b64: str, after_b64: str, threshold: float = 0.1) -> dict:
    """Visual diff of two base64 JPEG screenshots.

    Returns {changed_pixels, total_pixels, mismatch_pct, diff_image_b64}.
    Uses QImage for pixel comparison.
    """
    import base64
    from PyQt6.QtCore import QBuffer, QIODevice, Qt
    from PyQt6.QtGui import QColor, QImage

    # Decode images
    before_bytes = base64.b64decode(before_b64)
    after_bytes = base64.b64decode(after_b64)

    img_before = QImage()
    img_before.loadFromData(before_bytes)
    img_after = QImage()
    img_after.loadFromData(after_bytes)

    # Resize to same dimensions if needed
    w = min(img_before.width(), img_after.width())
    h = min(img_before.height(), img_after.height())

    if w == 0 or h == 0:
        return {"changed_pixels": 0, "total_pixels": 0, "mismatch_pct": 0.0, "diff_image_b64": ""}

    if img_before.size() != img_after.size():
        img_before = img_before.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio)
        img_after = img_after.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio)

    # Create diff image
    diff_img = QImage(w, h, QImage.Format.Format_RGB32)
    changed = 0
    total = w * h
    thresh_sq = (threshold * 255) ** 2 * 3  # squared distance threshold

    for y in range(h):
        for x in range(w):
            c1 = QColor(img_before.pixel(x, y))
            c2 = QColor(img_after.pixel(x, y))
            dr = c1.red() - c2.red()
            dg = c1.green() - c2.green()
            db = c1.blue() - c2.blue()
            dist_sq = dr * dr + dg * dg + db * db

            if dist_sq > thresh_sq:
                diff_img.setPixelColor(x, y, QColor(255, 50, 50))  # red for changed
                changed += 1
            else:
                # Dim the unchanged pixels
                gray = (c2.red() + c2.green() + c2.blue()) // 6
                diff_img.setPixelColor(x, y, QColor(gray, gray, gray))

    # Encode diff image as base64
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    diff_img.save(buf, "JPEG", 70)
    diff_b64 = base64.b64encode(buf.data().data()).decode()
    buf.close()

    pct = (changed / total * 100) if total > 0 else 0.0

    return {
        "changed_pixels": changed,
        "total_pixels": total,
        "mismatch_pct": round(pct, 2),
        "diff_image_b64": diff_b64,
    }
