"""Browser panel — animated nav bar, URL pill, tabs, progress bar, and QWebEngineView."""

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from browser_agent.browser.engine import BrowserEngine
from browser_agent.ui.nav_button import NavButton
from browser_agent.ui.progress_bar import LoadingProgressBar
from browser_agent.ui.tab_bar import BrowserTabBar
from browser_agent.ui.url_bar import AnimatedUrlBar


class BrowserPanel(QWidget):
    url_changed = pyqtSignal(str)
    page_loaded = pyqtSignal(str, str)  # url, title
    title_changed = pyqtSignal(str)

    def __init__(self, engine: BrowserEngine, home_url: str = "https://duckduckgo.com",
                 search_template: str = "https://duckduckgo.com/?q={query}") -> None:
        super().__init__()
        self._engine = engine
        self._home_url = home_url
        self._search_template = search_template

        # -- Navigation bar --
        nav_bar = QWidget()
        nav_bar.setObjectName("nav_bar")

        self._back_btn = NavButton("\u2190", "Back")
        self._back_btn.clicked.connect(self._go_back)

        self._forward_btn = NavButton("\u2192", "Forward")
        self._forward_btn.clicked.connect(self._go_forward)

        self._reload_btn = NavButton("\u27f3", "Reload")
        self._reload_btn.clicked.connect(self._reload)

        self._home_btn = NavButton("\u2302", "Home")
        self._home_btn.clicked.connect(lambda: self.navigate_to(self._home_url))

        self._url_bar = AnimatedUrlBar()
        self._url_bar.returnPressed.connect(self._on_url_bar_submit)

        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 6, 8, 6)
        nav_layout.setSpacing(4)
        nav_layout.addWidget(self._back_btn)
        nav_layout.addWidget(self._forward_btn)
        nav_layout.addWidget(self._reload_btn)
        nav_layout.addWidget(self._home_btn)
        nav_layout.addSpacing(6)
        nav_layout.addWidget(self._url_bar, 1)

        # -- Loading progress bar --
        self._progress = LoadingProgressBar()

        # -- Tab bar --
        self._tab_bar = BrowserTabBar()
        self._tab_bar.currentChanged.connect(self._on_tab_switched)
        self._tab_bar.new_tab_requested.connect(lambda: self.add_tab())
        self._tab_bar.tab_close_requested.connect(self.close_tab)

        # -- Stacked views --
        self._stack = QStackedWidget()

        # -- Layout --
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(nav_bar)
        layout.addWidget(self._progress)
        layout.addWidget(self._tab_bar)
        layout.addWidget(self._stack, 1)

        # Open first tab
        self.add_tab(self._home_url)

    def add_tab(self, url: str = "") -> int:
        view = self._engine.create_view()
        idx = self._stack.addWidget(view)
        self._tab_bar.addTab("New Tab")
        self._tab_bar.setCurrentIndex(idx)

        view.titleChanged.connect(lambda title, i=idx: self._on_title_changed(i, title))
        view.urlChanged.connect(lambda qurl: self._on_url_changed(qurl))
        view.loadStarted.connect(self._progress.start)
        view.loadFinished.connect(lambda ok: self._on_load_finished(ok))

        if url:
            self.navigate_to(url)
        return idx

    def add_incognito_tab(self, url: str = "") -> int:
        """Open a new incognito tab — no cookies or history saved."""
        view = self._engine.create_incognito_view()
        idx = self._stack.addWidget(view)
        self._tab_bar.addTab("\U0001f576 Incognito")
        self._tab_bar.setCurrentIndex(idx)
        # Purple-tinted tab text for incognito
        self._tab_bar.setTabToolTip(idx, "Incognito — no data saved")

        view.titleChanged.connect(lambda title, i=idx: self._on_title_changed(i, title))
        view.urlChanged.connect(lambda qurl: self._on_url_changed(qurl))
        view.loadStarted.connect(self._progress.start)
        view.loadFinished.connect(lambda ok: self._on_load_finished(ok))

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
        # Has spaces → definitely a search
        if " " in text:
            return True
        # No dots at all → search (e.g. "python tutorials")
        if "." not in text:
            return True
        # Starts with http/https/file → URL
        if text.startswith(("http://", "https://", "file://")):
            return False
        # Has a TLD-like pattern → URL (e.g. "google.com", "example.org")
        import re
        if re.match(r'^[\w.-]+\.\w{2,}(/.*)?$', text):
            return False
        return True
