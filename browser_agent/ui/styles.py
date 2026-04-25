"""Design token system + QSS theme.

ALL sizes, fonts, colors, spacing, and animation constants live here.
Every other UI file imports from this module — no hardcoded values anywhere else.
"""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget

# ═══════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════

# ── Typography ─────────────────────────────────────────────────
FONT_MAIN = "Inter"
FONT_FALLBACK = "'Inter', 'Segoe UI Variable', 'SF Pro Display', -apple-system, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace"

FONT_XS = 10        # timestamps, labels
FONT_SM = 11.5      # detail text, meta
FONT_BASE = 13      # body text, inputs
FONT_MD = 14        # sub-headers
FONT_LG = 16        # section titles
FONT_XL = 18        # panel headers
FONT_XXL = 22       # page titles

# ── Spacing ────────────────────────────────────────────────────
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_8 = 32

# ── Border Radius ──────────────────────────────────────────────
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14
RADIUS_XL = 18
RADIUS_PILL = 9999

# ── Component Sizes ────────────────────────────────────────────
BTN_SM = 28
BTN_MD = 36
BTN_LG = 44
HEADER_H = 52
INPUT_H = 44
PROGRESS_H = 3
THREAD_ITEM_H = 50
ICON_SM = 14
ICON_MD = 18

# ── Animation ──────────────────────────────────────────────────
ANIM_FAST = 150
ANIM_NORMAL = 250
ANIM_SLOW = 400
ANIM_SPRING = 500

# Gradient rotation speeds (degrees per frame at 60fps)
GRADIENT_SPEED_IDLE = 0.3
GRADIENT_SPEED_FOCUS = 2.0

# Glow fade rates (per frame)
GLOW_FADE_IN = 0.08
GLOW_FADE_OUT = 0.04

# Hover easing factor
HOVER_EASE = 0.15

# ── Colour Palette ─────────────────────────────────────────────
# Base
DARK_BG = "#0b0c10"
DARK_BG_ALT = "#12141a"
DARK_SURFACE = "#1a1d24"
DARK_SURFACE_LIGHT = "#22262e"
DARK_BORDER = "#2c313a"
DARK_BORDER_LIGHT = "#3b404a"

# Glass
GLASS_BG = "rgba(26, 29, 36, 0.65)"
GLASS_BORDER = "rgba(255, 255, 255, 0.05)"
GLASS_HOVER = "rgba(255, 255, 255, 0.08)"

# Text
DARK_TEXT = "#e2e8f0"
DARK_TEXT_SECONDARY = "#94a3b8"
DARK_TEXT_MUTED = "#64748b"

# Accent
ACCENT_PRIMARY = "#3b82f6"
ACCENT_SECONDARY = "#6366f1"
ACCENT_HOVER = "#60a5fa"
ACCENT_GLOW = "rgba(59, 130, 246, 0.25)"

# Semantic
SUCCESS = "#10b981"
SUCCESS_DIM = "rgba(16, 185, 129, 0.12)"
WARNING = "#f59e0b"
ERROR = "#ef4444"
ERROR_DIM = "rgba(239, 68, 68, 0.12)"
INFO = "#3b82f6"

# Chat bubbles
USER_BUBBLE = "rgba(59, 130, 246, 0.08)"
USER_BUBBLE_BORDER = "rgba(59, 130, 246, 0.15)"
ASSISTANT_BUBBLE = "rgba(26, 29, 36, 0.5)"
ASSISTANT_BUBBLE_BORDER = "rgba(255, 255, 255, 0.04)"
TOOL_BUBBLE = "rgba(100, 116, 139, 0.08)"
TOOL_BUBBLE_BORDER = "rgba(100, 116, 139, 0.15)"
THINKING_BUBBLE = "rgba(99, 102, 241, 0.08)"
THINKING_BUBBLE_BORDER = "rgba(99, 102, 241, 0.15)"


# ═══════════════════════════════════════════════════════════════
#  ANIMATION HELPERS
# ═══════════════════════════════════════════════════════════════

def fade_in(widget: QWidget, duration: int = ANIM_SLOW) -> QPropertyAnimation:
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim


def slide_fade_in(widget: QWidget, duration: int = ANIM_SLOW) -> QPropertyAnimation:
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    fade = QPropertyAnimation(effect, b"opacity")
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setDuration(duration)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)
    fade.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return fade


# ═══════════════════════════════════════════════════════════════
#  INLINE STYLE BUILDERS (for widgets that use setStyleSheet)
# ═══════════════════════════════════════════════════════════════

def label_style(
    color: str = DARK_TEXT,
    size: float = FONT_BASE,
    weight: int = 400,
    spacing: float = 0,
) -> str:
    s = f"color: {color}; font-size: {size}px; font-weight: {weight};"
    if spacing:
        s += f" letter-spacing: {spacing}px;"
    return s


def btn_glass_style(
    color: str = ACCENT_PRIMARY,
    bg: str = "rgba(108,92,231,0.12)",
    border: str = "rgba(108,92,231,0.2)",
    radius: int = RADIUS_MD,
    size: float = FONT_SM,
) -> str:
    return (
        f"QPushButton {{ background: {bg}; color: {color}; "
        f"border: 1px solid {border}; border-radius: {radius}px; "
        f"font-size: {size}px; font-weight: 600; padding: 0 {SPACE_4}px; }}"
        f"QPushButton:hover {{ background: {bg.replace('0.12', '0.20')}; "
        f"border-color: {border.replace('0.2', '0.35')}; }}"
    )


# ═══════════════════════════════════════════════════════════════
#  QSS THEME (uses tokens)
# ═══════════════════════════════════════════════════════════════

DARK_THEME = f"""
/* ═══════════════════════════════════════════════════════════
   Premium Glassmorphism Theme — AI Browser Agent
   All values derived from design tokens
   ═══════════════════════════════════════════════════════════ */

* {{
    font-family: {FONT_FALLBACK};
    font-size: {FONT_BASE}px;
}}

QMainWindow {{
    background-color: {DARK_BG};
    color: {DARK_TEXT};
}}

QSplitter {{
    background-color: {DARK_BG};
}}

QSplitter::handle {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 transparent, stop:0.3 {ACCENT_PRIMARY}, stop:0.7 {ACCENT_SECONDARY}, stop:1 transparent);
    width: 1px;
}}

QSplitter::handle:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 transparent, stop:0.2 {ACCENT_PRIMARY}, stop:0.8 {ACCENT_SECONDARY}, stop:1 transparent);
    width: 3px;
}}

/* --- Scrollbars --- */
QScrollBar:vertical {{
    background: transparent; width: {RADIUS_SM}px; margin: 0; border: none;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.08); min-height: 40px; border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.15); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none; border: none; height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent; height: {RADIUS_SM}px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255,255,255,0.08); min-width: 40px; border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{ background: rgba(255,255,255,0.15); }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none; border: none; width: 0px;
}}

/* --- Menu --- */
QMenuBar {{
    background-color: rgba(12,12,24,0.9); color: {DARK_TEXT_SECONDARY};
    border-bottom: 1px solid {GLASS_BORDER}; padding: 2px {SPACE_2}px; font-size: {FONT_SM}px;
}}
QMenuBar::item {{
    background: transparent; padding: {SPACE_2}px {SPACE_3}px;
    border-radius: {RADIUS_SM}px; margin: 2px;
}}
QMenuBar::item:selected {{ background-color: rgba(255,255,255,0.06); color: {DARK_TEXT}; }}

QMenu {{
    background-color: rgba(18,18,42,0.95); border: 1px solid {GLASS_BORDER};
    border-radius: {RADIUS_MD}px; padding: {RADIUS_SM}px; color: {DARK_TEXT};
}}
QMenu::item {{
    padding: {SPACE_2}px {SPACE_6}px {SPACE_2}px {SPACE_4}px;
    border-radius: {RADIUS_SM}px; margin: 2px {SPACE_1}px;
}}
QMenu::item:selected {{ background-color: rgba(108,92,231,0.15); }}
QMenu::separator {{ height: 1px; background: {GLASS_BORDER}; margin: {SPACE_1}px {SPACE_3}px; }}

/* --- Nav Bar --- */
QWidget#nav_bar {{
    background-color: rgba(12,12,24,0.85); border-bottom: 1px solid {GLASS_BORDER};
}}
QToolButton#nav_btn {{
    background-color: transparent; color: {DARK_TEXT_MUTED}; border: none;
    border-radius: {RADIUS_MD}px; padding: {SPACE_2}px; font-size: {FONT_LG}px;
    font-weight: 500; min-width: {BTN_MD}px; min-height: {BTN_MD}px;
}}
QToolButton#nav_btn:hover {{ background-color: rgba(255,255,255,0.06); color: {DARK_TEXT}; }}
QToolButton#nav_btn:pressed {{ background-color: rgba(108,92,231,0.15); color: {ACCENT_PRIMARY}; }}

/* --- URL Bar --- */
QLineEdit#url_bar {{
    background-color: rgba(255,255,255,0.04); color: {DARK_TEXT_SECONDARY};
    border: 1px solid {GLASS_BORDER}; border-radius: {RADIUS_LG}px;
    padding: {SPACE_2}px {SPACE_4}px; font-size: {FONT_BASE}px;
    selection-background-color: {ACCENT_PRIMARY}; selection-color: white;
}}
QLineEdit#url_bar:focus {{
    border-color: rgba(108,92,231,0.4); background-color: rgba(255,255,255,0.06); color: {DARK_TEXT};
}}

/* --- Tabs --- */
QTabBar {{
    background-color: {DARK_BG}; border: none; qproperty-drawBase: 0;
}}
QTabBar::tab {{
    background-color: transparent; color: {DARK_TEXT_MUTED}; border: none;
    border-bottom: 2px solid transparent; padding: {SPACE_3}px {SPACE_5}px;
    margin: 0px 1px; font-size: {FONT_SM}px; font-weight: 500;
    min-width: 60px; max-width: 200px;
}}
QTabBar::tab:selected {{ color: {DARK_TEXT}; border-bottom: 2px solid {ACCENT_PRIMARY}; }}
QTabBar::tab:hover:!selected {{ color: {DARK_TEXT_SECONDARY}; background-color: rgba(255,255,255,0.03); }}
QTabBar::close-button {{
    image: none; subcontrol-position: right; padding: 2px;
    border-radius: {SPACE_1}px; margin-right: {SPACE_1}px;
}}
QTabBar::close-button:hover {{ background-color: {ERROR_DIM}; }}

/* --- Chat Panel --- */
QWidget#chat_panel {{
    background-color: rgba(8,8,15,0.95); border-left: 1px solid {GLASS_BORDER};
}}
QWidget#chat_header {{
    background-color: rgba(18,18,42,0.6); border-bottom: 1px solid {GLASS_BORDER};
}}
QScrollArea#chat_scroll {{ background-color: transparent; border: none; }}
QWidget#messages_container {{ background-color: transparent; }}

/* --- Composer --- */
QWidget#composer_area {{
    background-color: rgba(18,18,42,0.4); border-top: 1px solid {GLASS_BORDER};
}}
QTextEdit#chat_input {{
    background-color: rgba(255,255,255,0.04); color: {DARK_TEXT};
    border: 1px solid {GLASS_BORDER}; border-radius: {RADIUS_LG}px;
    padding: {SPACE_3}px {SPACE_4}px; font-size: {FONT_BASE}px;
    selection-background-color: {ACCENT_PRIMARY}; selection-color: white;
}}
QTextEdit#chat_input:focus {{
    border-color: rgba(108,92,231,0.35); background-color: rgba(255,255,255,0.06);
}}

/* --- Send/Stop --- */
QPushButton#send_btn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_SECONDARY});
    color: white; border: none; border-radius: {RADIUS_LG}px;
    padding: {SPACE_3}px {SPACE_6}px; font-size: {FONT_BASE}px; font-weight: 600;
}}
QPushButton#send_btn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {ACCENT_HOVER}, stop:1 {ACCENT_SECONDARY});
}}
QPushButton#send_btn:disabled {{ background: rgba(255,255,255,0.06); color: {DARK_TEXT_MUTED}; }}

QPushButton#stop_btn {{
    background-color: {ERROR_DIM}; color: {ERROR};
    border: 1px solid rgba(239,68,68,0.25); border-radius: {RADIUS_LG}px;
    padding: {SPACE_3}px {SPACE_6}px; font-size: {FONT_BASE}px; font-weight: 600;
}}
QPushButton#stop_btn:hover {{
    background-color: rgba(239,68,68,0.20); border-color: rgba(239,68,68,0.40);
}}

/* --- Tool Groups --- */
QFrame#tool_group {{
    background-color: {TOOL_BUBBLE}; border: 1px solid {TOOL_BUBBLE_BORDER};
    border-radius: {RADIUS_LG}px; margin: {SPACE_1}px {SPACE_2}px;
}}
QFrame#tool_group:hover {{
    background-color: rgba(16,185,129,0.06); border-color: rgba(16,185,129,0.18);
}}
QWidget#tool_detail_container {{
    background: transparent; border-top: 1px solid rgba(16,185,129,0.08);
    margin: 0px {SPACE_2}px;
}}

/* --- Messages --- */
QFrame#msg_user {{
    background-color: {USER_BUBBLE}; border: 1px solid {USER_BUBBLE_BORDER};
    border-radius: {RADIUS_LG}px; padding: {SPACE_3}px {SPACE_4}px;
    margin: {SPACE_1}px {SPACE_2}px {SPACE_1}px {SPACE_8}px;
}}
QFrame#msg_assistant {{
    background-color: {ASSISTANT_BUBBLE}; border: 1px solid {ASSISTANT_BUBBLE_BORDER};
    border-radius: {RADIUS_LG}px; padding: {SPACE_4}px {SPACE_4}px;
    margin: {SPACE_1}px {SPACE_2}px;
}}
QFrame#msg_tool {{
    background-color: {TOOL_BUBBLE}; border: 1px solid {TOOL_BUBBLE_BORDER};
    border-radius: {RADIUS_MD}px; padding: {SPACE_3}px {SPACE_3}px;
    margin: 2px {SPACE_2}px 2px {SPACE_6}px;
}}
QFrame#msg_error {{
    background-color: {ERROR_DIM}; border: 1px solid rgba(239,68,68,0.20);
    border-radius: {RADIUS_MD}px; padding: {SPACE_3}px {SPACE_3}px;
    margin: 2px {SPACE_2}px;
}}
QFrame#msg_thinking {{
    background-color: {THINKING_BUBBLE}; border: 1px solid {THINKING_BUBBLE_BORDER};
    border-radius: {RADIUS_MD}px; padding: {SPACE_2}px {SPACE_3}px;
    margin: 2px {SPACE_2}px 2px {SPACE_6}px;
}}

/* --- Role Labels --- */
QLabel#role_label_user {{
    color: {ACCENT_PRIMARY}; font-size: {FONT_XS}px; font-weight: 700; letter-spacing: 1px;
}}
QLabel#role_label_assistant {{
    color: {ACCENT_SECONDARY}; font-size: {FONT_XS}px; font-weight: 700; letter-spacing: 1px;
}}
QLabel#role_label_tool {{
    color: {SUCCESS}; font-size: {FONT_XS}px; font-weight: 700; letter-spacing: 1px;
}}
QLabel#role_label_error {{
    color: {ERROR}; font-size: {FONT_XS}px; font-weight: 700; letter-spacing: 1px;
}}
QLabel#role_label_thinking {{
    color: {ACCENT_SECONDARY}; font-size: {FONT_XS}px; font-weight: 700; letter-spacing: 1px;
}}
QLabel#msg_timestamp {{
    color: rgba(255,255,255,0.15); font-size: {FONT_XS}px; font-weight: 500;
}}
QLabel#msg_text {{
    color: {DARK_TEXT}; font-size: {FONT_BASE}px; line-height: 1.6;
}}
QLabel#msg_detail {{
    color: {DARK_TEXT_SECONDARY}; font-size: {FONT_SM}px; line-height: 1.4;
}}

/* --- Typing Indicator --- */
QWidget#typing_indicator {{
    background-color: rgba(18,18,42,0.4); border: 1px solid {GLASS_BORDER};
    border-radius: {RADIUS_LG}px; margin: 2px {SPACE_2}px;
}}

/* --- Sidebar --- */
QWidget#thread_selector {{
    background-color: rgba(8,8,15,0.95); border-right: 1px solid {GLASS_BORDER};
}}
QFrame#thread_item {{
    background: transparent; border: 1px solid transparent;
    border-radius: {RADIUS_MD}px; margin: 1px 2px;
}}
QFrame#thread_item:hover {{
    background: rgba(255,255,255,0.03); border-color: {GLASS_BORDER};
}}
QFrame#thread_active {{
    background: rgba(108,92,231,0.08); border: 1px solid rgba(108,92,231,0.15);
    border-radius: {RADIUS_MD}px; margin: 1px 2px;
}}

/* --- Skill Cards --- */
QFrame#skill_card {{
    background: rgba(168,85,247,0.04); border: 1px solid rgba(168,85,247,0.10);
    border-radius: {RADIUS_MD}px; margin: 2px 0px;
}}
QFrame#skill_card:hover {{
    background: rgba(168,85,247,0.08); border-color: rgba(168,85,247,0.20);
}}

/* --- Rule Cards --- */
QFrame#rule_card {{
    background: rgba(245,158,11,0.04); border: 1px solid rgba(245,158,11,0.10);
    border-radius: {RADIUS_MD}px; margin: 2px 0px;
}}
QFrame#rule_card:hover {{
    background: rgba(245,158,11,0.08); border-color: rgba(245,158,11,0.20);
}}

/* --- Sidebar Icon Strip --- */
QWidget#sidebar_strip {{
    background-color: rgba(8,8,15,0.95);
    border-left: 1px solid {GLASS_BORDER};
}}

/* --- Status Bar --- */
QStatusBar {{
    background-color: rgba(8,8,15,0.9); color: {DARK_TEXT_MUTED};
    font-size: {FONT_SM}px; border-top: 1px solid {GLASS_BORDER};
    padding: 2px {SPACE_3}px;
}}
"""
