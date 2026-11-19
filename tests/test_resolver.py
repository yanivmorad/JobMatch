import os

from scraper_service import resolvers


class _FakePage:
    def __init__(self):
        self.paths = []

    def screenshot(self, path):
        self.paths.append(path)
        with open(path, "wb") as f:
            f.write(b"png")


def test_no_screenshot_by_default(monkeypatch, tmp_path):
    """באג: צילום מסך נכתב תמיד לתיקיית העבודה (שורש הפרויקט)."""
    monkeypatch.delenv("DEBUG_SCREENSHOTS", raising=False)
    monkeypatch.setattr(resolvers, "DEBUG_DIR", str(tmp_path / "debug"))
    page = _FakePage()

    resolvers._debug_screenshot(page, "x.png")

    assert page.paths == []


def test_screenshot_goes_to_debug_dir_when_enabled(monkeypatch, tmp_path):
    debug_dir = tmp_path / "logs" / "debug"
    monkeypatch.setenv("DEBUG_SCREENSHOTS", "true")
    monkeypatch.setattr(resolvers, "DEBUG_DIR", str(debug_dir))
    page = _FakePage()

    resolvers._debug_screenshot(page, "missing_button_7.png")

    assert page.paths == [str(debug_dir / "missing_button_7.png")]
    assert (debug_dir / "missing_button_7.png").exists()


def test_default_debug_dir_is_under_logs():
    assert resolvers.DEBUG_DIR.replace(os.sep, "/").endswith("logs/debug")


def test_screenshot_failure_does_not_raise(monkeypatch, tmp_path):
    class _Broken:
        def screenshot(self, path):
            raise RuntimeError("page closed")

    monkeypatch.setenv("DEBUG_SCREENSHOTS", "1")
    monkeypatch.setattr(resolvers, "DEBUG_DIR", str(tmp_path))
    resolvers._debug_screenshot(_Broken(), "x.png")  # לא אמור לזרוק


# --- ResolveError: כישלון מפורש במקום החזרה שקטה של הקישור המקורי ---

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from scraper_service.resolvers import ResolveError, URLResolver


class _FakeBrowser:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def _fake_playwright(browser):
    @contextmanager
    def _cm():
        yield SimpleNamespace(chromium=SimpleNamespace(launch=lambda headless: browser))

    return _cm


def test_regular_urls_pass_through():
    r = URLResolver(hireme_token="t")
    assert r.resolve("https://boards.greenhouse.io/acme/jobs/1") == "https://boards.greenhouse.io/acme/jobs/1"
    # 'hiremetech.com' רק בתוך ה-query - לא קישור של HireMeTech
    assert r.resolve("https://acme.com/job?ref=hiremetech.com") == "https://acme.com/job?ref=hiremetech.com"


def test_missing_token_raises_instead_of_returning_hiremetech_url(monkeypatch):
    """באג: בלי טוקן הוחזר הקישור המקורי, והסורק סרק את דף ההתחברות של HireMeTech."""
    monkeypatch.delenv("HIRE_ME_TECH_TOKEN", raising=False)
    with pytest.raises(ResolveError, match="HIRE_ME_TECH_TOKEN"):
        URLResolver().resolve("https://hiremetech.com/jobs/123")


def test_no_playwright_raises(monkeypatch):
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", False)
    with pytest.raises(ResolveError, match="Playwright"):
        URLResolver(hireme_token="t").resolve("https://www.hiremetech.com/jobs/123")


def test_browser_closed_and_error_wrapped_on_failure(monkeypatch):
    browser = _FakeBrowser()
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(resolvers, "sync_playwright", _fake_playwright(browser), raising=False)

    def boom(self, *a):
        raise TimeoutError("page.goto timed out")

    monkeypatch.setattr(URLResolver, "_click_through_hiremetech", boom)

    with pytest.raises(ResolveError, match="HireMeTech"):
        URLResolver(hireme_token="t").resolve("https://hiremetech.com/jobs/123")
    assert browser.closed


def test_resolve_error_from_click_through_is_kept(monkeypatch):
    browser = _FakeBrowser()
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(resolvers, "sync_playwright", _fake_playwright(browser), raising=False)

    def no_button(self, *a):
        raise ResolveError("HireMeTech: לא נמצא כפתור הגשה")

    monkeypatch.setattr(URLResolver, "_click_through_hiremetech", no_button)

    with pytest.raises(ResolveError, match="כפתור הגשה"):
        URLResolver(hireme_token="t").resolve("https://hiremetech.com/jobs/123")
    assert browser.closed


def test_successful_resolution_returns_company_url(monkeypatch):
    browser = _FakeBrowser()
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(resolvers, "sync_playwright", _fake_playwright(browser), raising=False)
    monkeypatch.setattr(
        URLResolver, "_click_through_hiremetech", lambda self, *a: "https://acme.comeet.com/jobs/1"
    )

    assert URLResolver(hireme_token="t").resolve("https://hiremetech.com/jobs/1") == "https://acme.comeet.com/jobs/1"
    assert browser.closed
