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

import base64
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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


class _JsonResp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


class _ApiSession:
    """ה-API של HireMeTech בלי רשת. status=500 = ה-API לא ענה (ממשיכים לדפדפן)."""

    def __init__(self, status=500, job=None):
        self.status, self.job = status, job
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, dict(headers or {})))
        return _JsonResp(self.status, {"job": self.job} if self.job is not None else None)


def _resolver(token="t", **api):
    return URLResolver(hireme_token=token, session=_ApiSession(**api))


def test_regular_urls_pass_through():
    r = _resolver()
    assert r.resolve("https://boards.greenhouse.io/acme/jobs/1") == "https://boards.greenhouse.io/acme/jobs/1"
    # 'hiremetech.com' רק בתוך ה-query - לא קישור של HireMeTech
    assert r.resolve("https://acme.com/job?ref=hiremetech.com") == "https://acme.com/job?ref=hiremetech.com"
    assert r.session.calls == []


def test_missing_token_raises_instead_of_returning_hiremetech_url(monkeypatch):
    """באג: בלי טוקן הוחזר הקישור המקורי, והסורק סרק את דף ההתחברות של HireMeTech."""
    monkeypatch.delenv("HIRE_ME_TECH_TOKEN", raising=False)
    with pytest.raises(ResolveError, match="HIRE_ME_TECH_TOKEN"):
        URLResolver(session=_ApiSession()).resolve("https://hiremetech.com/jobs/123")


def test_no_playwright_raises(monkeypatch):
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", False)
    with pytest.raises(ResolveError, match="Playwright"):
        _resolver().resolve("https://www.hiremetech.com/jobs/123")


def test_browser_closed_and_error_wrapped_on_failure(monkeypatch):
    browser = _FakeBrowser()
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(resolvers, "sync_playwright", _fake_playwright(browser), raising=False)

    def boom(self, *a):
        raise TimeoutError("page.goto timed out")

    monkeypatch.setattr(URLResolver, "_click_through_hiremetech", boom)

    with pytest.raises(ResolveError, match="HireMeTech"):
        _resolver().resolve("https://hiremetech.com/jobs/123")
    assert browser.closed


def test_resolve_error_from_click_through_is_kept(monkeypatch):
    browser = _FakeBrowser()
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(resolvers, "sync_playwright", _fake_playwright(browser), raising=False)

    def no_button(self, *a):
        raise ResolveError("HireMeTech: לא נמצא כפתור הגשה")

    monkeypatch.setattr(URLResolver, "_click_through_hiremetech", no_button)

    with pytest.raises(ResolveError, match="כפתור הגשה"):
        _resolver().resolve("https://hiremetech.com/jobs/123")
    assert browser.closed


def _jwt(exp: datetime) -> str:
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    return f"{b64({'alg': 'HS256'})}.{b64({'exp': int(exp.timestamp()), 'user_id': 1})}.sig"


def test_token_expiry_reads_exp_without_verifying():
    exp = datetime(2026, 2, 22, 10, 40, 30, tzinfo=timezone.utc)
    assert resolvers.token_expiry(_jwt(exp)) == exp
    assert resolvers.token_expiry("not-a-jwt") is None
    assert resolvers.token_expiry("a.b.c") is None


def test_token_status_never_exposes_the_token():
    past = _jwt(datetime.now(timezone.utc) - timedelta(days=1))
    status = resolvers.hiremetech_token_status(past)
    assert status["configured"] is True and status["expired"] is True
    assert past not in json.dumps(status)
    assert resolvers.hiremetech_token_status("")["configured"] is False


def test_expired_token_fails_fast_with_public_fallback(monkeypatch):
    """באג: עם טוקן שפג נפתח דפדפן לכל משרה (~23 שניות), וההודעה הייתה 'הלחיצה לא הובילה לאתר'."""
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", True)

    def must_not_launch():
        raise AssertionError("browser launched with an expired token")

    monkeypatch.setattr(resolvers, "sync_playwright", must_not_launch, raising=False)
    token = _jwt(datetime(2026, 2, 22, tzinfo=timezone.utc))

    with pytest.raises(ResolveError, match="פג ב-22/02/2026") as err:
        URLResolver(hireme_token=token).resolve("https://hiremetech.com/job/1")
    assert err.value.public_fallback is True


def test_every_hiremetech_failure_allows_the_public_page(monkeypatch):
    browser = _FakeBrowser()
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(resolvers, "sync_playwright", _fake_playwright(browser), raising=False)

    def no_redirect(self, *a):
        raise ResolveError("HireMeTech: הלחיצה לא הובילה לאתר החברה")

    monkeypatch.setattr(URLResolver, "_click_through_hiremetech", no_redirect)
    with pytest.raises(ResolveError) as err:
        _resolver().resolve("https://hiremetech.com/job/1")
    assert err.value.public_fallback is True

    monkeypatch.delenv("HIRE_ME_TECH_TOKEN", raising=False)
    with pytest.raises(ResolveError) as err:
        URLResolver(session=_ApiSession()).resolve("https://hiremetech.com/job/1")
    assert err.value.public_fallback is True


def test_resolve_error_default_has_no_fallback():
    assert ResolveError("x").public_fallback is False


def test_successful_resolution_returns_company_url(monkeypatch):
    browser = _FakeBrowser()
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(resolvers, "sync_playwright", _fake_playwright(browser), raising=False)
    monkeypatch.setattr(
        URLResolver, "_click_through_hiremetech", lambda self, *a: "https://acme.comeet.com/jobs/1"
    )

    assert _resolver().resolve("https://hiremetech.com/jobs/1") == "https://acme.comeet.com/jobs/1"
    assert browser.closed


# --- ה-API של HireMeTech (/api/jobs/{id}): פענוח בלי דפדפן, גם בשרת החינמי ---

_VALID = _jwt(datetime.now(timezone.utc) + timedelta(days=3))
_GUEST_JOB = {  # כמו התשובה האמיתית לאורח: החברה וקישור ההגשה מוסתרים
    "title": "Full Stack Developer",
    "company_name": "",
    "company": {"name": "", "employer_masked": True},
    "employer_masked": True,
    "job_url": "https://hiremetech.com/job/152001956",
    "apply_url": None,
    "description": "Requirements: 1-2 years of C#",
}


def _no_browser(monkeypatch):
    monkeypatch.setenv("ENABLE_PLAYWRIGHT", "false")
    monkeypatch.setattr(resolvers, "sync_playwright", lambda: pytest.fail("browser launched"), raising=False)


def test_api_returns_the_company_link_without_a_browser(monkeypatch):
    _no_browser(monkeypatch)
    job = {**_GUEST_JOB, "employer_masked": False, "company": {"name": "Acme"}, "company_name": "Acme",
           "job_url": "https://acme.comeet.com/jobs/1?utm_source=hiremetech"}
    r = _resolver(_VALID, status=200, job=job)

    assert r.resolve("https://hiremetech.com/he-il/job/152001956") == "https://acme.comeet.com/jobs/1?utm_source=hiremetech"
    url, headers = r.session.calls[0]
    assert url == "https://hiremetech.com/api/jobs/152001956"
    assert headers["Authorization"] == f"Bearer {_VALID}"


@pytest.mark.parametrize("status, job", [(200, _GUEST_JOB), (401, None), (403, None)])
def test_api_rejecting_the_token_says_so(monkeypatch, status, job):
    """תשובה של אורח (החברה מוסתרת) למרות שנשלח טוקן = האתר לא קיבל אותו."""
    _no_browser(monkeypatch)
    with pytest.raises(ResolveError, match="דחה את הטוקן") as err:
        _resolver(_VALID, status=status, job=job).resolve("https://hiremetech.com/job/152001956")
    assert err.value.public_fallback is True


def test_api_removed_job(monkeypatch):
    _no_browser(monkeypatch)
    with pytest.raises(ResolveError, match="לא נמצאה") as err:
        _resolver(_VALID, status=404).resolve("https://hiremetech.com/job/999")
    assert err.value.public_fallback is True


def test_api_without_a_company_link_falls_back_to_the_browser(monkeypatch):
    """מחובר אבל אין קישור חיצוני ב-API - הלחיצה על 'הגש מועמדות' בדפדפן עדיין עשויה להוביל לאתר."""
    browser = _FakeBrowser()
    monkeypatch.setenv("ENABLE_PLAYWRIGHT", "true")
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(resolvers, "sync_playwright", _fake_playwright(browser), raising=False)
    monkeypatch.setattr(URLResolver, "_click_through_hiremetech", lambda self, *a: "https://acme.com/careers/1")
    job = {**_GUEST_JOB, "employer_masked": False, "company": {"name": "Acme"}}

    assert _resolver(_VALID, status=200, job=job).resolve("https://hiremetech.com/job/1") == "https://acme.com/careers/1"


def test_api_without_a_company_link_and_no_browser_scrapes_the_description(monkeypatch):
    _no_browser(monkeypatch)
    job = {**_GUEST_JOB, "employer_masked": False, "company": {"name": "Acme"}}
    with pytest.raises(ResolveError, match="לא התקבל קישור") as err:
        _resolver(_VALID, status=200, job=job).resolve("https://hiremetech.com/job/1")
    assert err.value.public_fallback is True
