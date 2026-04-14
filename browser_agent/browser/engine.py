"""BrowserEngine — manages QWebEngineProfile, cookie persistence, and view creation."""

from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

from browser_agent.config import AppConfig

CHROME_VERSION = "130.0.0.0"
CHROME_UA = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    f"AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/{CHROME_VERSION} Safari/537.36"
)

# Injected before any page script runs — overrides navigator.userAgent,
# navigator.userAgentData, and navigator.appVersion so sites like WhatsApp
# see a modern Chrome and don't block us.
UA_OVERRIDE_JS = f"""
(function() {{
    const ua = "{CHROME_UA}";
    Object.defineProperty(navigator, 'userAgent', {{get: () => ua}});
    Object.defineProperty(navigator, 'appVersion', {{get: () => ua.substring(8)}});
    Object.defineProperty(navigator, 'platform', {{get: () => 'Win32'}});

    // Override User-Agent Client Hints API (navigator.userAgentData)
    if (navigator.userAgentData) {{
        const brands = [
            {{brand: "Google Chrome", version: "{CHROME_VERSION.split('.')[0]}"}},
            {{brand: "Chromium", version: "{CHROME_VERSION.split('.')[0]}"}},
            {{brand: "Not?A_Brand", version: "99"}}
        ];
        const uaData = {{
            brands: brands,
            mobile: false,
            platform: "Windows",
            getHighEntropyValues: (hints) => Promise.resolve({{
                brands: brands,
                mobile: false,
                platform: "Windows",
                platformVersion: "15.0.0",
                architecture: "x86",
                model: "",
                uaFullVersion: "{CHROME_VERSION}",
                fullVersionList: brands.map(b => ({{...b, version: "{CHROME_VERSION}"}}))
            }})
        }};
        Object.defineProperty(navigator, 'userAgentData', {{get: () => uaData}});
    }}
}})();
"""


class BrowserEngine:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._cleanup_stale_caches()
        self._profile = self._create_profile()
        self._incognito_profile: QWebEngineProfile | None = None
        self._views: list[QWebEngineView] = []

    def _cleanup_stale_caches(self) -> None:
        """Remove old cache_PID dirs from previous instances that didn't clean up."""
        import shutil
        storage = Path(self._config.persistent_storage_path)
        if not storage.exists():
            return
        for d in storage.iterdir():
            if d.is_dir() and d.name.startswith("cache_"):
                try:
                    shutil.rmtree(d, ignore_errors=True)
                except Exception:
                    pass  # locked by another running instance — skip

    def _create_profile(self) -> QWebEngineProfile:
        # Use the default profile — stores cookies in persistentStoragePath
        # Named profiles on Qt6/Windows store cookies in a separate Qt-managed location
        profile = QWebEngineProfile.defaultProfile()

        storage_path = self._config.persistent_storage_path
        Path(storage_path).mkdir(parents=True, exist_ok=True)

        # Persistent storage for cookies, localStorage, IndexedDB
        profile.setPersistentStoragePath(storage_path)
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        # Separate cache dir with PID to avoid lock conflicts between instances
        import os
        cache_dir = Path(storage_path) / f"cache_{os.getpid()}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        profile.setCachePath(str(cache_dir))

        # HTTP-level user agent
        profile.setHttpUserAgent(CHROME_UA)

        # JS-level override — runs at DocumentCreation before any page scripts
        script = QWebEngineScript()
        script.setName("ua_override")
        script.setSourceCode(UA_OVERRIDE_JS)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)
        profile.scripts().insert(script)

        return profile

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
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True
        )

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

    # ── Incognito mode ──

    def _get_incognito_profile(self) -> QWebEngineProfile:
        """Create or return an off-the-record profile (no cookies/storage saved)."""
        if self._incognito_profile is None:
            # No name = off-the-record (nothing persisted to disk)
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
        """Create a view with an off-the-record profile — no data persisted."""
        profile = self._get_incognito_profile()
        page = QWebEnginePage(profile)
        view = QWebEngineView()
        view.setPage(page)

        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True
        )

        # Tag as incognito so UI can style differently
        view.setProperty("incognito", True)
        self._views.append(view)
        return view
