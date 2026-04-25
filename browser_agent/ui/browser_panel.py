"""Browser panel — Brave-style layout: tabs on top, toolbar below, web content."""

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from browser_agent.browser.engine import BrowserEngine
from browser_agent.ui.nav_button import NavButton
from browser_agent.ui.progress_bar import LoadingProgressBar
from browser_agent.ui.tab_bar import BrowserTabBar
from browser_agent.ui.url_bar import AnimatedUrlBar
from browser_agent.ui.styles import (
    ACCENT_PRIMARY,
    DARK_TEXT_MUTED,
    DARK_TEXT,
    FONT_SM,
    FONT_XS,
    GLASS_BORDER,
    RADIUS_SM,
    SPACE_2,
    SPACE_3,
)


class _ToolbarButton(QLabel):
    """Small icon button for the toolbar (bookmark star, AI toggle, downloads, menu)."""
    clicked = pyqtSignal()

    def __init__(self, icon: str, tooltip: str, size: int = 30, parent=None):
        super().__init__(icon, parent)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._default_style = (
            f"QLabel {{ color: {DARK_TEXT_MUTED}; font-size: 15px;"
            f" background: transparent; border-radius: {RADIUS_SM}px; }}"
            f"QLabel:hover {{ color: {DARK_TEXT}; background: rgba(255,255,255,0.08); }}"
        )
        self.setStyleSheet(self._default_style)

    def set_active(self, active: bool) -> None:
        if active:
            self.setStyleSheet(
                f"QLabel {{ color: {ACCENT_PRIMARY}; font-size: 15px;"
                f" background: rgba(59,130,246,0.12); border-radius: {RADIUS_SM}px; }}"
                f"QLabel:hover {{ background: rgba(59,130,246,0.18); }}"
            )
        else:
            self.setStyleSheet(self._default_style)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class BrowserPanel(QWidget):
    url_changed = pyqtSignal(str)
    page_loaded = pyqtSignal(str, str)  # url, title
    title_changed = pyqtSignal(str)
    # New signals for toolbar actions
    sidebar_toggle_requested = pyqtSignal()
    menu_requested = pyqtSignal()
    bookmark_toggle_requested = pyqtSignal(str, str)  # url, title

    def __init__(self, engine: BrowserEngine, home_url: str = "https://duckduckgo.com",
                 search_template: str = "https://duckduckgo.com/?q={query}") -> None:
        super().__init__()
        self._engine = engine
        self._home_url = home_url
        self._search_template = search_template

        # ── Tab bar (TOP — Brave/Chrome style) ──
        self._tab_bar = BrowserTabBar()
        self._tab_bar.currentChanged.connect(self._on_tab_switched)
        self._tab_bar.new_tab_requested.connect(lambda: self.add_tab())
        self._tab_bar.tab_close_requested.connect(self.close_tab)

        # ── Toolbar (below tabs) ──
        toolbar = QWidget()
        toolbar.setObjectName("nav_bar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        toolbar_layout.setSpacing(2)

        # Navigation buttons
        self._back_btn = NavButton("\u2190", "Back (Alt+Left)")
        self._back_btn.clicked.connect(self._go_back)

        self._forward_btn = NavButton("\u2192", "Forward (Alt+Right)")
        self._forward_btn.clicked.connect(self._go_forward)

        self._reload_btn = NavButton("\u27f3", "Reload (F5)")
        self._reload_btn.clicked.connect(self._reload)

        toolbar_layout.addWidget(self._back_btn)
        toolbar_layout.addWidget(self._forward_btn)
        toolbar_layout.addWidget(self._reload_btn)
        toolbar_layout.addSpacing(4)

        # URL bar (takes most space)
        self._url_bar = AnimatedUrlBar()
        self._url_bar.returnPressed.connect(self._on_url_bar_submit)
        toolbar_layout.addWidget(self._url_bar, 1)

        toolbar_layout.addSpacing(4)

        # Bookmark star
        self._bookmark_btn = _ToolbarButton("\u2606", "Bookmark this page (Ctrl+D)")
        self._bookmark_btn.clicked.connect(self._toggle_bookmark)
        toolbar_layout.addWidget(self._bookmark_btn)

        # Downloads button
        self._downloads_btn = _ToolbarButton("\u2913", "Downloads (Ctrl+J)")
        toolbar_layout.addWidget(self._downloads_btn)

        # AI sidebar toggle
        self._ai_btn = _ToolbarButton("\u2726", "AI Assistant (Ctrl+B)", size=32)
        self._ai_btn.setStyleSheet(
            f"QLabel {{ color: {ACCENT_PRIMARY}; font-size: 16px; font-weight: bold;"
            f" background: rgba(59,130,246,0.08); border-radius: {RADIUS_SM}px; }}"
            f"QLabel:hover {{ background: rgba(59,130,246,0.18); }}"
        )
        self._ai_btn.clicked.connect(self.sidebar_toggle_requested.emit)
        toolbar_layout.addWidget(self._ai_btn)

        # Hamburger menu
        self._menu_btn = _ToolbarButton("\u22ee", "Menu", size=30)
        self._menu_btn.clicked.connect(self.menu_requested.emit)
        toolbar_layout.addWidget(self._menu_btn)

        # ── Loading progress bar ──
        self._progress = LoadingProgressBar()

        # ── Stacked views ──
        self._stack = QStackedWidget()

        # ── Main layout: Tabs → Toolbar → Progress → Content ──
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._tab_bar)
        layout.addWidget(toolbar)
        layout.addWidget(self._progress)
        layout.addWidget(self._stack, 1)

        # Open first tab
        self.add_tab(self._home_url)

    # ── Tab management ──

    def add_tab(self, url: str = "") -> int:
        view = self._engine.create_view()
        idx = self._stack.addWidget(view)
        self._tab_bar.addTab("New Tab")
        self._tab_bar.setCurrentIndex(idx)

        view.titleChanged.connect(lambda title, i=idx: self._on_title_changed(i, title))
        view.urlChanged.connect(lambda qurl: self._on_url_changed(qurl))
        view.loadStarted.connect(self._progress.start)
        view.loadStarted.connect(lambda i=idx: self._tab_bar.set_tab_loading(i, True))
        view.loadFinished.connect(lambda ok: self._on_load_finished(ok))
        view.loadFinished.connect(lambda ok, i=idx: self._tab_bar.set_tab_loading(i, False))
        view.iconChanged.connect(lambda icon, i=idx: self._tab_bar.set_tab_favicon(i, icon))

        if url:
            self.navigate_to(url)
        return idx

    def add_incognito_tab(self, url: str = "") -> int:
        """Open a new incognito tab — no cookies or history saved."""
        view = self._engine.create_incognito_view()
        idx = self._stack.addWidget(view)
        self._tab_bar.addTab("\U0001f576 Incognito")
        self._tab_bar.setCurrentIndex(idx)
        self._tab_bar.setTabToolTip(idx, "Incognito \u2014 no data saved")

        view.titleChanged.connect(lambda title, i=idx: self._on_title_changed(i, title))
        view.urlChanged.connect(lambda qurl: self._on_url_changed(qurl))
        view.loadStarted.connect(self._progress.start)
        view.loadStarted.connect(lambda i=idx: self._tab_bar.set_tab_loading(i, True))
        view.loadFinished.connect(lambda ok: self._on_load_finished(ok))
        view.loadFinished.connect(lambda ok, i=idx: self._tab_bar.set_tab_loading(i, False))
        view.iconChanged.connect(lambda icon, i=idx: self._tab_bar.set_tab_favicon(i, icon))

        if url:
            self.navigate_to(url)
        else:
            self.navigate_to(self._home_url)
        return idx

    def close_tab(self, index: int) -> None:
        if self._tab_bar.count() <= 1:
            return
        widget = self._stack.widget(index)
        self._tab_bar.removeTab(index)
        self._stack.removeWidget(widget)
        if widget:
            self._engine.remove_view(widget)
            widget.deleteLater()

    def navigate_to(self, url: str) -> None:
        url = url.strip()
        if self._is_search_query(url):
            from urllib.parse import quote_plus
            url = self._search_template.replace("{query}", quote_plus(url))
        elif not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url
        view = self.current_view()
        if view:
            view.setUrl(QUrl(url))

    def current_view(self):
        return self._stack.currentWidget()

    def set_bookmark_active(self, active: bool) -> None:
        """Update the bookmark star icon state."""
        self._bookmark_btn.setText("\u2605" if active else "\u2606")  # ★ or ☆
        self._bookmark_btn.set_active(active)

    def set_ai_sidebar_active(self, active: bool) -> None:
        """Update the AI sidebar toggle button state."""
        self._ai_btn.set_active(active)

    # ── Internal handlers ──

    def _on_tab_switched(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        view = self._stack.currentWidget()
        if view:
            self._url_bar.setText(view.url().toString())
            self.title_changed.emit(view.title() or "New Tab")

    def _on_url_bar_submit(self) -> None:
        self.navigate_to(self._url_bar.text().strip())

    def _on_url_changed(self, qurl: QUrl) -> None:
        url = qurl.toString()
        if self._stack.currentWidget() and self._stack.currentWidget().url() == qurl:
            self._url_bar.setText(url)
        self.url_changed.emit(url)

    def _on_title_changed(self, index: int, title: str) -> None:
        short = title[:30] + "\u2026" if len(title) > 30 else title
        self._tab_bar.setTabText(index, short or "New Tab")
        if index == self._tab_bar.currentIndex():
            self.title_changed.emit(title)

    def _on_load_finished(self, ok: bool) -> None:
        self._progress.stop()
        view = self.current_view()
        if view and ok:
            url = view.url().toString()
            title = view.title()
            self.page_loaded.emit(url, title or "")

    def _toggle_bookmark(self) -> None:
        view = self.current_view()
        if view:
            self.bookmark_toggle_requested.emit(
                view.url().toString(), view.title() or ""
            )

    def _go_back(self) -> None:
        view = self.current_view()
        if view:
            view.back()

    def _go_forward(self) -> None:
        view = self.current_view()
        if view:
            view.forward()

    def _reload(self) -> None:
        view = self.current_view()
        if view:
            view.reload()

    @staticmethod
    def _is_search_query(text: str) -> bool:
        """Return True if the text looks like a search query rather than a URL."""
        if " " in text:
            return True
        if "." not in text:
            return True
        if text.startswith(("http://", "https://", "file://")):
            return False
        import re
        if re.match(r'^[\w.-]+\.\w{2,}(/.*)?$', text):
            return False
        return True
