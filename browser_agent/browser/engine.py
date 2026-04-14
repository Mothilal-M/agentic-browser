"""BrowserEngine — manages QWebEngineProfile, cookie persistence, and view creation."""

import json
import logging
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtWebEngineCore import (
    QWebEngineCookieStore,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

from browser_agent.config import AppConfig

logger = logging.getLogger(__name__)

CHROME_VERSION = "130.0.0.0"
CHROME_UA = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    f"AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/{CHROME_VERSION} Safari/537.36"
)

UA_OVERRIDE_JS = f"""
(function() {{
    const ua = "{CHROME_UA}";
    Object.defineProperty(navigator, 'userAgent', {{get: () => ua}});
    Object.defineProperty(navigator, 'appVersion', {{get: () => ua.substring(8)}});
    Object.defineProperty(navigator, 'platform', {{get: () => 'Win32'}});
    if (navigator.userAgentData) {{
        const brands = [
            {{brand: "Google Chrome", version: "{CHROME_VERSION.split('.')[0]}"}},
            {{brand: "Chromium", version: "{CHROME_VERSION.split('.')[0]}"}},
            {{brand: "Not?A_Brand", version: "99"}}
        ];
        const uaData = {{
            brands: brands, mobile: false, platform: "Windows",
            getHighEntropyValues: (hints) => Promise.resolve({{
                brands: brands, mobile: false, platform: "Windows",
                platformVersion: "15.0.0", architecture: "x86", model: "",
                uaFullVersion: "{CHROME_VERSION}",
                fullVersionList: brands.map(b => ({{...b, version: "{CHROME_VERSION}"}}))
            }})
        }};
        Object.defineProperty(navigator, 'userAgentData', {{get: () => uaData}});
    }}
}})();
"""


class CookiePersistence:
    """Manually save/restore cookies via QWebEngineCookieStore API.

    Qt6 named profiles don't create a Cookies SQLite file with setPersistentStoragePath.
    This class intercepts all cookies via cookieAdded signal and saves them to a JSON file.
    On startup, it restores cookies from the JSON file.
    Auto-saves every 30 seconds if cookies changed.
    """

    def __init__(self, cookie_store: QWebEngineCookieStore, save_path: Path) -> None:
        from PyQt6.QtCore import QTimer

        self._store = cookie_store
        self._save_path = save_path
        self._cookies: dict[str, dict] = {}
        self._dirty = False

        # Restore BEFORE connecting signals (so restored cookies don't re-trigger save)
        self._restore()

        # NOW connect signals — only new cookies from browsing will be captured
        self._store.cookieAdded.connect(self._on_cookie_added)
        self._store.cookieRemoved.connect(self._on_cookie_removed)

        # Auto-save timer — every 30 seconds
        self._save_timer = QTimer()
        self._save_timer.timeout.connect(self.save)
        self._save_timer.start(30_000)

    def _cookie_key(self, cookie: QNetworkCookie) -> str:
        return f"{cookie.domain()}|{cookie.path()}|{cookie.name().data().decode()}"

    def _on_cookie_added(self, cookie: QNetworkCookie) -> None:
        key = self._cookie_key(cookie)
        self._cookies[key] = {
            "name": cookie.name().data().decode(),
            "value": cookie.value().data().decode(),
            "domain": cookie.domain(),
            "path": cookie.path(),
            "secure": cookie.isSecure(),
            "httponly": cookie.isHttpOnly(),
            "expiry": cookie.expirationDate().toString() if cookie.expirationDate().isValid() else "",
        }
        self._dirty = True

    def _on_cookie_removed(self, cookie: QNetworkCookie) -> None:
        key = self._cookie_key(cookie)
        self._cookies.pop(key, None)
        self._dirty = True

    def save(self) -> None:
        """Save all cookies to disk."""
        if not self._dirty and self._save_path.exists():
            return
        try:
            self._save_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_path.write_text(
                json.dumps(list(self._cookies.values()), indent=2),
                encoding="utf-8",
            )
            logger.info("Saved %d cookies to %s", len(self._cookies), self._save_path)
            self._dirty = False
        except Exception as e:
            logger.warning("Failed to save cookies: %s", e)

    def _restore(self) -> None:
        """Restore cookies from disk into the cookie store."""
        if not self._save_path.exists():
            return
        try:
            data = json.loads(self._save_path.read_text(encoding="utf-8"))
            count = 0
            for c in data:
                cookie = QNetworkCookie()
                cookie.setName(c["name"].encode())
                cookie.setValue(c["value"].encode())
                cookie.setDomain(c["domain"])
                cookie.setPath(c["path"])
                cookie.setSecure(c.get("secure", False))
                cookie.setHttpOnly(c.get("httponly", False))

                # Build the origin URL from domain — required for setCookie to work
                domain = c["domain"].lstrip(".")
                scheme = "https" if c.get("secure") else "http"
                origin = QUrl(f"{scheme}://{domain}{c['path']}")
                self._store.setCookie(cookie, origin)
                count += 1
            logger.info("Restored %d cookies from %s", count, self._save_path)
        except Exception as e:
            logger.warning("Failed to restore cookies: %s", e)


class BrowserEngine:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._profile = self._create_profile()

        # Cookie persistence — signals connected first, then loadAllCookies
        self._cookies_path = Path(config.persistent_storage_path) / "cookies.json"
        self._cookie_store = self._profile.cookieStore()
        self._cookie_persistence = CookiePersistence(
            self._cookie_store, self._cookies_path,
        )
        # loadAllCookies AFTER signals connected — ensures cookieAdded fires
        self._cookie_store.loadAllCookies()
        self._incognito_profile: QWebEngineProfile | None = None
        self._views: list[QWebEngineView] = []

    def _create_profile(self) -> QWebEngineProfile:
        storage_path = self._config.persistent_storage_path
        Path(storage_path).mkdir(parents=True, exist_ok=True)

        profile = QWebEngineProfile("AgenticBrowser")
        profile.setPersistentStoragePath(storage_path)
        profile.setCachePath(str(Path(storage_path) / "cache"))
        # AllowPersistentCookies — we handle cookie persistence ourselves via CookiePersistence
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )

        profile.setHttpUserAgent(CHROME_UA)

        script = QWebEngineScript()
        script.setName("ua_override")
        script.setSourceCode(UA_OVERRIDE_JS)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)
        profile.scripts().insert(script)

        return profile

    def save_cookies(self) -> None:
        """Save cookies to disk. Uses CookiePersistence if signals worked, otherwise falls back to JS."""
        if self._cookie_persistence and len(self._cookie_persistence._cookies) > 0:
            self._cookie_persistence.save()
        else:
            # Fallback: extract cookies via JavaScript from current page
            self._save_cookies_via_js()

    def _save_cookies_via_js(self) -> None:
        """Extract document.cookie from the current page and save to JSON."""
        page = self.current_page()
        if not page:
            return

        def on_result(cookies_str):
            if not cookies_str:
                return
            cookies = []
            current_url = page.url()
            domain = current_url.host()
            for pair in cookies_str.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    name, value = pair.split("=", 1)
                    cookies.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": f".{domain}",
                        "path": "/",
                        "secure": current_url.scheme() == "https",
                        "httponly": False,
                    })
            if cookies:
                try:
                    self._cookies_path.parent.mkdir(parents=True, exist_ok=True)
                    # Merge with existing
                    existing = []
                    if self._cookies_path.exists():
                        existing = json.loads(self._cookies_path.read_text(encoding="utf-8"))
                    # Merge by name+domain key
                    by_key = {f"{c['domain']}|{c['name']}": c for c in existing}
                    for c in cookies:
                        by_key[f"{c['domain']}|{c['name']}"] = c
                    self._cookies_path.write_text(
                        json.dumps(list(by_key.values()), indent=2), encoding="utf-8"
                    )
                    logger.info("Saved %d cookies via JS fallback", len(by_key))
                except Exception as e:
                    logger.warning("JS cookie save failed: %s", e)

        page.runJavaScript("document.cookie", on_result)

    @property
    def profile(self) -> QWebEngineProfile:
        return self._profile

    def create_view(self) -> QWebEngineView:
        page = QWebEnginePage(self._profile)
        view = QWebEngineView()
        view.setPage(page)

        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        self._views.append(view)
        return view

    def current_view(self) -> QWebEngineView | None:
        return self._views[-1] if self._views else None

    def current_page(self):
        view = self.current_view()
        return view.page() if view else None

    def remove_view(self, view: QWebEngineView) -> None:
        if view in self._views:
            self._views.remove(view)

    # ── Incognito ──

    def _get_incognito_profile(self) -> QWebEngineProfile:
        if self._incognito_profile is None:
            self._incognito_profile = QWebEngineProfile()
            self._incognito_profile.setHttpUserAgent(CHROME_UA)

            script = QWebEngineScript()
            script.setName("ua_override")
            script.setSourceCode(UA_OVERRIDE_JS)
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(True)
            self._incognito_profile.scripts().insert(script)

        return self._incognito_profile

    def create_incognito_view(self) -> QWebEngineView:
        profile = self._get_incognito_profile()
        page = QWebEnginePage(profile)
        view = QWebEngineView()
        view.setPage(page)

        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        view.setProperty("incognito", True)
        self._views.append(view)
        return view
