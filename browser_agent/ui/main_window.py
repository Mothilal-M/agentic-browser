"""Main window — Brave-style layout with sidebar icon strip and expandable panels."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from browser_agent.browser.engine import BrowserEngine
from browser_agent.config import AppConfig
from browser_agent.ui.browser_panel import BrowserPanel
from browser_agent.ui.chat_panel import ChatPanel
from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    ACCENT_SECONDARY,
    DARK_BG,
    DARK_TEXT,
    DARK_TEXT_MUTED,
    DARK_TEXT_SECONDARY,
    DARK_THEME,
    ERROR,
    FONT_SM,
    FONT_XS,
    GLASS_BORDER,
    RADIUS_MD,
    RADIUS_SM,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SUCCESS,
    WARNING,
)


# ─── Sidebar icon strip ─────────────────────────────────────────────

class _SidebarIcon(QLabel):
    """Single icon in the vertical sidebar strip."""
    clicked = pyqtSignal()

    def __init__(self, icon: str, tooltip: str, parent=None):
        super().__init__(icon, parent)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(40, 40)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._active = False
        self._apply_style()

    def _apply_style(self) -> None:
        if self._active:
            self.setStyleSheet(
                f"QLabel {{ color: {ACCENT_PRIMARY}; font-size: 18px;"
                f" background: rgba(59,130,246,0.12); border-radius: {RADIUS_SM}px;"
                f" border-left: 2px solid {ACCENT_PRIMARY}; }}"
            )
        else:
            self.setStyleSheet(
                f"QLabel {{ color: {DARK_TEXT_MUTED}; font-size: 18px;"
                f" background: transparent; border-radius: {RADIUS_SM}px;"
                f" border-left: 2px solid transparent; }}"
                f"QLabel:hover {{ color: {DARK_TEXT}; background: rgba(255,255,255,0.06); }}"
            )

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SidebarStrip(QWidget):
    """Vertical icon strip on the right edge of the window (Brave-style sidebar)."""
    panel_requested = pyqtSignal(str)  # panel_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar_strip")
        self.setFixedWidth(44)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, SPACE_2, 2, SPACE_2)
        layout.setSpacing(SPACE_1)

        # Top icons
        self._icons: dict[str, _SidebarIcon] = {}

        ai_icon = _SidebarIcon("\u2726", "AI Assistant (Ctrl+B)")
        ai_icon.clicked.connect(lambda: self.panel_requested.emit("ai"))
        self._icons["ai"] = ai_icon
        layout.addWidget(ai_icon)

        history_icon = _SidebarIcon("\u23f0", "History (Ctrl+H)")
        history_icon.clicked.connect(lambda: self.panel_requested.emit("history"))
        self._icons["history"] = history_icon
        layout.addWidget(history_icon)

        bookmarks_icon = _SidebarIcon("\u2606", "Bookmarks (Ctrl+Shift+B)")
        bookmarks_icon.clicked.connect(lambda: self.panel_requested.emit("bookmarks"))
        self._icons["bookmarks"] = bookmarks_icon
        layout.addWidget(bookmarks_icon)

        skills_icon = _SidebarIcon("\u26a1", "Skills")
        skills_icon.clicked.connect(lambda: self.panel_requested.emit("skills"))
        self._icons["skills"] = skills_icon
        layout.addWidget(skills_icon)

        layout.addStretch()

        # Bottom icons
        settings_icon = _SidebarIcon("\u2699", "Settings")
        settings_icon.clicked.connect(lambda: self.panel_requested.emit("settings"))
        self._icons["settings"] = settings_icon
        layout.addWidget(settings_icon)

    def set_active_panel(self, panel_name: str | None) -> None:
        for name, icon in self._icons.items():
            icon.set_active(name == panel_name)


# ─── Main Window ─────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, engine: BrowserEngine) -> None:
        super().__init__()
        self._config = config
        self._engine = engine
        self._active_panel: str | None = None
        self._sidebar_pinned = False

        self.setWindowTitle("Agentic Browser")
        self.resize(config.window_width, config.window_height)
        self.setStyleSheet(DARK_THEME)

        self._setup_actions()
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_statusbar()

    def _setup_actions(self) -> None:
        """Create menu QAction objects up front so external code can wire to them.

        The actions are added to the hamburger menu in _show_app_menu() but exist
        as MainWindow attributes from startup, so app.py can connect handlers.
        """
        self._record_action = QAction("⏺ Start Recording", self)
        self._stop_record_action = QAction("⏹ Stop Recording", self)
        self._stop_record_action.setEnabled(False)
        self._export_html_action = QAction("\U0001f4c4 Export as HTML Report", self)
        self._export_html_action.setEnabled(False)
        self._export_json_action = QAction("\U0001f4be Export as JSON", self)
        self._export_json_action.setEnabled(False)
        self._import_skill_action = QAction("\U0001f4e5 Import Skill from File", self)
        self._export_skills_action = QAction("\U0001f4e4 Export All Skills", self)

    def _setup_ui(self) -> None:
        # Browser panel (main content)
        self.browser_panel = BrowserPanel(
            self._engine,
            self._config.resolved_home_url,
            self._config.search_url_template,
        )

        # Chat panel (AI sidebar content)
        self.chat_panel = ChatPanel()
        self.chat_panel.setMinimumWidth(340)

        # Sidebar strip (vertical icon bar)
        self._sidebar_strip = SidebarStrip()
        self._sidebar_strip.panel_requested.connect(self._on_sidebar_panel_requested)

        # Splitter: Browser | Sidebar panel
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self.browser_panel)
        self._splitter.addWidget(self.chat_panel)
        self._splitter.setHandleWidth(1)
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, True)

        total = self._config.window_width - 44  # subtract sidebar strip width
        sidebar = int(total * self._config.sidebar_width_ratio)
        self._splitter.setSizes([total - sidebar, sidebar])

        # Central layout: [Splitter] [SidebarStrip]
        central = QWidget()
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self._splitter, 1)

        # Separator line before sidebar strip
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {GLASS_BORDER};")
        central_layout.addWidget(sep)
        central_layout.addWidget(self._sidebar_strip)

        self.setCentralWidget(central)

        # Set AI panel as default active
        self._sidebar_strip.set_active_panel("ai")
        self._active_panel = "ai"

        # Wire browser panel signals
        self.browser_panel.title_changed.connect(
            lambda t: self.setWindowTitle(f"{t} \u2014 Agentic Browser" if t else "Agentic Browser")
        )
        self.browser_panel.sidebar_toggle_requested.connect(self._toggle_sidebar)
        self.browser_panel.menu_requested.connect(self._show_app_menu)

    def _setup_shortcuts(self) -> None:
        """Register keyboard shortcuts (replaces old menu bar)."""
        shortcuts = [
            ("Ctrl+T", self._new_tab),
            ("Ctrl+Shift+N", self._new_incognito_tab),
            ("Ctrl+W", self._close_current_tab),
            ("Ctrl+Q", self.close),
            ("Ctrl+B", self._toggle_sidebar),
            ("Ctrl+L", self._focus_url_bar),
            ("F5", self._reload_page),
            ("Ctrl+R", self._reload_page),
        ]
        for key_seq, handler in shortcuts:
            action = QAction(self)
            action.setShortcut(QKeySequence(key_seq))
            action.triggered.connect(handler)
            self.addAction(action)

    def _setup_statusbar(self) -> None:
        status = QStatusBar()
        status.setSizeGripEnabled(False)
        self.setStatusBar(status)

        _sep_style = f"color: {GLASS_BORDER}; font-size: {FONT_XS}px; margin: 0 4px;"
        _label_style = (
            f"color: {DARK_TEXT_MUTED}; font-size: {FONT_XS}px; font-weight: 500;"
        )

        # URL indicator
        self._status_url = QLabel("")
        self._status_url.setStyleSheet(_label_style)
        self._status_url.setMaximumWidth(400)
        status.addWidget(self._status_url, 1)

        sep1 = QLabel("\u2502")
        sep1.setStyleSheet(_sep_style)
        status.addWidget(sep1)

        # Tab count
        self._status_tabs = QLabel("\u25a2 1 tab")
        self._status_tabs.setStyleSheet(_label_style)
        status.addWidget(self._status_tabs)

        sep2 = QLabel("\u2502")
        sep2.setStyleSheet(_sep_style)
        status.addWidget(sep2)

        # Agent status
        self._status_agent = QLabel("\u2022 Ready")
        self._status_agent.setStyleSheet(
            f"color: {SUCCESS}; font-size: {FONT_XS}px; font-weight: 500;"
        )
        status.addWidget(self._status_agent)

        # Recording indicator (hidden by default)
        self._status_recording = QLabel("\u23fa REC")
        self._status_recording.setStyleSheet(
            f"color: {ERROR}; font-size: {FONT_XS}px; font-weight: 700;"
            f" background: rgba(239,68,68,0.12); border-radius: 4px;"
            f" padding: 1px 6px; margin-left: 8px;"
        )
        self._status_recording.setVisible(False)
        status.addPermanentWidget(self._status_recording)

        # Recording blink timer
        self._rec_blink_timer = QTimer(self)
        self._rec_blink_timer.timeout.connect(self._blink_recording)
        self._rec_visible = True

        # Wire signals
        self.browser_panel.url_changed.connect(self._update_status_url)
        self.browser_panel._tab_bar.currentChanged.connect(
            lambda _: self._update_tab_count()
        )

    # ── Sidebar panel management ──

    def _on_sidebar_panel_requested(self, panel_name: str) -> None:
        """Handle sidebar icon clicks — toggle panel visibility."""
        if self._active_panel == panel_name and self.chat_panel.isVisible():
            # Clicking active panel icon hides it
            self.chat_panel.setVisible(False)
            self._sidebar_strip.set_active_panel(None)
            self._active_panel = None
            self.browser_panel.set_ai_sidebar_active(False)
        else:
            self._active_panel = panel_name
            self._sidebar_strip.set_active_panel(panel_name)
            self.chat_panel.setVisible(True)
            self.browser_panel.set_ai_sidebar_active(panel_name == "ai")

            # Switch chat panel to appropriate view
            if panel_name == "ai":
                self.chat_panel.show_chat()
            elif panel_name == "history":
                self.chat_panel.toggle_history()
            elif panel_name == "skills":
                self.chat_panel.toggle_skills()
            elif panel_name == "bookmarks":
                # Will be implemented in Week 3
                self.chat_panel.show_chat()
            elif panel_name == "settings":
                # Will be implemented in Week 5
                self.chat_panel.show_chat()

    def _toggle_sidebar(self) -> None:
        """Toggle AI sidebar visibility."""
        if self.chat_panel.isVisible():
            self.chat_panel.setVisible(False)
            self._sidebar_strip.set_active_panel(None)
            self._active_panel = None
            self.browser_panel.set_ai_sidebar_active(False)
        else:
            self._active_panel = "ai"
            self._sidebar_strip.set_active_panel("ai")
            self.chat_panel.setVisible(True)
            self.chat_panel.show_chat()
            self.browser_panel.set_ai_sidebar_active(True)

    # ── App menu (replaces menu bar) ──

    def _show_app_menu(self) -> None:
        """Show the hamburger menu dropdown."""
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background: rgba(18,18,42,0.95); border: 1px solid {GLASS_BORDER};"
            f" border-radius: {RADIUS_MD}px; padding: 6px; color: {DARK_TEXT};"
            f" font-size: {FONT_SM}px; }}"
            f"QMenu::item {{ padding: 8px 28px 8px 16px; border-radius: {RADIUS_SM}px;"
            f" margin: 2px 4px; }}"
            f"QMenu::item:selected {{ background: rgba(108,92,231,0.15); }}"
            f"QMenu::separator {{ height: 1px; background: {GLASS_BORDER};"
            f" margin: 4px 12px; }}"
        )

        menu.addAction("New Tab\tCtrl+T", self._new_tab)
        menu.addAction("New Incognito Tab\tCtrl+Shift+N", self._new_incognito_tab)
        menu.addAction("Close Tab\tCtrl+W", self._close_current_tab)
        menu.addSeparator()

        menu.addAction("\u2726 AI Assistant\tCtrl+B", self._toggle_sidebar)
        menu.addSeparator()

        # Session recording submenu (uses pre-created actions wired in app.py)
        session_menu = menu.addMenu("Session")
        session_menu.addAction(self._record_action)
        session_menu.addAction(self._stop_record_action)
        session_menu.addSeparator()
        session_menu.addAction(self._export_html_action)
        session_menu.addAction(self._export_json_action)
        session_menu.addSeparator()
        session_menu.addAction(self._import_skill_action)
        session_menu.addAction(self._export_skills_action)

        menu.addSeparator()
        menu.addAction("Quit\tCtrl+Q", self.close)

        # Show menu below the menu button in browser panel
        btn = self.browser_panel._menu_btn
        pos = btn.mapToGlobal(btn.rect().bottomLeft())
        menu.exec(pos)

    # ── Status bar helpers ──

    def _update_status_url(self, url: str) -> None:
        short = url
        if len(url) > 70:
            short = url[:67] + "..."
        self._status_url.setText(short)

    def _update_tab_count(self) -> None:
        count = self.browser_panel._tab_bar.count()
        self._status_tabs.setText(f"\u25a2 {count} tab{'s' if count != 1 else ''}")

    def set_agent_status(self, status: str, color: str = "") -> None:
        if not color:
            color = SUCCESS if status == "Ready" else ACCENT_PRIMARY
        self._status_agent.setText(f"\u2022 {status}")
        self._status_agent.setStyleSheet(
            f"color: {color}; font-size: {FONT_XS}px; font-weight: 500;"
        )

    def set_recording(self, active: bool) -> None:
        self._status_recording.setVisible(active)
        if active:
            self._rec_blink_timer.start(800)
        else:
            self._rec_blink_timer.stop()
            self._rec_visible = True

    def _blink_recording(self) -> None:
        self._rec_visible = not self._rec_visible
        self._status_recording.setVisible(self._rec_visible)

    # ── Tab/navigation actions ──

    def _new_tab(self) -> None:
        self.browser_panel.add_tab(self._config.home_url)

    def _new_incognito_tab(self) -> None:
        self.browser_panel.add_incognito_tab()

    def _close_current_tab(self) -> None:
        tab_bar = self.browser_panel._tab_bar
        self.browser_panel.close_tab(tab_bar.currentIndex())

    def _focus_url_bar(self) -> None:
        self.browser_panel._url_bar._edit.setFocus()
        self.browser_panel._url_bar._edit.selectAll()

    def _reload_page(self) -> None:
        view = self.browser_panel.current_view()
        if view:
            view.reload()
