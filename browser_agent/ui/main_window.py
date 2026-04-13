"""Main window — polished QSplitter with BrowserPanel (left) and ChatPanel (right)."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QMenuBar,
    QSplitter,
    QStatusBar,
)

from browser_agent.browser.engine import BrowserEngine
from browser_agent.config import AppConfig
from browser_agent.ui.browser_panel import BrowserPanel
from browser_agent.ui.chat_panel import ChatPanel
from browser_agent.ui.styles import DARK_TEXT_MUTED, DARK_THEME, ACCENT_PRIMARY


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, engine: BrowserEngine) -> None:
        super().__init__()
        self._config = config
        self._engine = engine

        self.setWindowTitle("AI Browser Agent")
        self.resize(config.window_width, config.window_height)
        self.setStyleSheet(DARK_THEME)

        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()

    def _setup_ui(self) -> None:
        self.browser_panel = BrowserPanel(
            self._engine,
            self._config.resolved_home_url,
            self._config.search_url_template,
        )
        self.chat_panel = ChatPanel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.browser_panel)
        splitter.addWidget(self.chat_panel)
        splitter.setHandleWidth(1)

        total = self._config.window_width
        sidebar = int(total * self._config.sidebar_width_ratio)
        splitter.setSizes([total - sidebar, sidebar])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        self.setCentralWidget(splitter)

        # Update window title with page title
        self.browser_panel.title_changed.connect(
            lambda t: self.setWindowTitle(f"{t} \u2014 AI Browser Agent" if t else "AI Browser Agent")
        )

    def _setup_menu(self) -> None:
        menu_bar = QMenuBar()
        self.setMenuBar(menu_bar)

        file_menu = menu_bar.addMenu("&File")

        new_tab_action = QAction("New Tab", self)
        new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        new_tab_action.triggered.connect(self._new_tab)
        file_menu.addAction(new_tab_action)

        incognito_action = QAction("New Incognito Tab", self)
        incognito_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        incognito_action.triggered.connect(self._new_incognito_tab)
        file_menu.addAction(incognito_action)

        close_tab_action = QAction("Close Tab", self)
        close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        close_tab_action.triggered.connect(self._close_current_tab)
        file_menu.addAction(close_tab_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menu_bar.addMenu("&View")

        toggle_action = QAction("Toggle Sidebar", self)
        toggle_action.setShortcut(QKeySequence("Ctrl+B"))
        toggle_action.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(toggle_action)

        # Session recording menu
        self._session_menu = menu_bar.addMenu("&Session")

        self._record_action = QAction("\u23fa Start Recording", self)
        self._record_action.setShortcut(QKeySequence("Ctrl+R"))
        self._session_menu.addAction(self._record_action)

        self._stop_record_action = QAction("\u23f9 Stop Recording", self)
        self._stop_record_action.setEnabled(False)
        self._session_menu.addAction(self._stop_record_action)

        self._session_menu.addSeparator()

        self._export_html_action = QAction("\U0001f4c4 Export as HTML Report", self)
        self._export_html_action.setEnabled(False)
        self._session_menu.addAction(self._export_html_action)

        self._export_json_action = QAction("\U0001f4be Export as JSON", self)
        self._export_json_action.setEnabled(False)
        self._session_menu.addAction(self._export_json_action)

        self._session_menu.addSeparator()

        self._import_skill_action = QAction("\U0001f4e5 Import Skill from File", self)
        self._session_menu.addAction(self._import_skill_action)

        self._export_skills_action = QAction("\U0001f4e4 Export All Skills", self)
        self._session_menu.addAction(self._export_skills_action)

    def _setup_statusbar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        self.browser_panel.url_changed.connect(
            lambda url: status.showMessage(url, 5000)
        )

    def _new_tab(self) -> None:
        self.browser_panel.add_tab(self._config.home_url)

    def _new_incognito_tab(self) -> None:
        self.browser_panel.add_incognito_tab()

    def _close_current_tab(self) -> None:
        tab_bar = self.browser_panel._tab_bar
        self.browser_panel.close_tab(tab_bar.currentIndex())

    def _toggle_sidebar(self) -> None:
        self.chat_panel.setVisible(not self.chat_panel.isVisible())
