import pytest

from scraper_service import scraper as scraper_mod
from scraper_service.scraper import Scraper

VALID_JOB = """Title: Backend Engineer
Markdown Content:
We are looking for a Backend Engineer. Requirements: 3+ years of experience with Python,
strong skills in SQL. You will build services. Responsibilities include on-call.
"""

LOGIN_PAGE = """Title: Sign in | Acme
Markdown Content:
Log in to your account. Email. Password. Forgot password? Create an account to continue
browsing and save your searches across all of your devices in one place.
"""


class _Resp:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


class _Session:
    def __init__(self, resp):
        self.resp = resp
        self.headers_seen = None

    def get(self, url, headers=None, timeout=None):
        self.headers_seen = headers
        return self.resp


@pytest.fixture
def make_scraper(monkeypatch):
    def _make(jina_resp, playwright_content=None, key="jina-key"):
        if key is None:
            monkeypatch.delenv("JINA_API_KEY", raising=False)
        else:
            monkeypatch.setenv("JINA_API_KEY", key)
        s = Scraper()
        s.session = _Session(jina_resp)
        monkeypatch.setattr(s, "_scrape_with_playwright", lambda url, job_id=None: playwright_content)
        monkeypatch.setattr(scraper_mod, "HAS_PLAYWRIGHT", True)
        return s

    return _make


def test_no_authorization_header_without_jina_key(make_scraper):
    """באג: בלי מפתח נשלחה הכותרת 'Authorization: Bearer None'."""
    s = make_scraper(_Resp(200, VALID_JOB), key=None)
    s.scrape("https://x.com/job")
    assert "Authorization" not in s.session.headers_seen


def test_authorization_header_with_jina_key(make_scraper):
    s = make_scraper(_Resp(200, VALID_JOB), key="k123")
    s.scrape("https://x.com/job")
    assert s.session.headers_seen["Authorization"] == "Bearer k123"


def test_jina_success_is_traced(make_scraper):
    s = make_scraper(_Resp(200, VALID_JOB))
    trace = []
    result = s.scrape("https://x.com/job", trace=trace)

    assert result["source"] == "jina"
    assert [a["method"] for a in trace] == ["jina"]
    assert trace[0]["valid"] is True and trace[0]["status"] == 200


def test_login_page_from_jina_falls_back_to_playwright(make_scraper):
    s = make_scraper(_Resp(200, LOGIN_PAGE), playwright_content=VALID_JOB)
    trace = []
    result = s.scrape("https://x.com/job", trace=trace)

    assert result["source"] == "local_browser"
    assert trace[0]["reason"] == "bad_title"
    assert trace[1] == {**trace[1], "method": "playwright", "valid": True, "reason": "ok"}


def test_both_methods_fail_with_reasons(make_scraper):
    s = make_scraper(_Resp(403, "Forbidden"), playwright_content=LOGIN_PAGE)
    trace = []
    assert s.scrape("https://x.com/job", trace=trace) is None
    assert [a["reason"] for a in trace] == ["jina_http_403", "bad_title"]


def test_playwright_fetch_failure_is_traced(make_scraper):
    s = make_scraper(_Resp(500, ""), playwright_content=None)
    trace = []
    assert s.scrape("https://x.com/job", trace=trace) is None
    assert trace[-1]["reason"] == "fetch_failed"


class _SeqSession:
    """מחזיר תשובות לפי הסדר ושומר את ה-headers של כל קריאה."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(dict(headers))
        return self.responses.pop(0)


SELECTOR_MISS = _Resp(
    422,
    '{"code":422,"message":"No content available for URL https://jobs.lever.co/x with target selector main, article"}',
)


def test_jina_selector_miss_retries_full_page(make_scraper):
    """באג: X-Target-Selector גרם ל-422 באתרים בלי main/article (Lever), ונפל ל-Playwright."""
    s = make_scraper(_Resp(200, VALID_JOB))
    s.session = _SeqSession([SELECTOR_MISS, _Resp(200, VALID_JOB)])
    trace = []

    result = s.scrape("https://jobs.lever.co/x", trace=trace)

    assert result["source"] == "jina"
    assert [a["method"] for a in trace] == ["jina", "jina_full_page"]
    assert trace[0]["reason"] == "jina_selector_miss"
    assert "X-Target-Selector" in s.session.calls[0]
    assert "X-Target-Selector" not in s.session.calls[1]


def test_other_jina_errors_do_not_retry(make_scraper):
    s = make_scraper(_Resp(200, VALID_JOB), playwright_content=VALID_JOB)
    s.session = _SeqSession([_Resp(422, '{"message":"Invalid URL"}')])
    trace = []

    s.scrape("https://x.com/job", trace=trace)

    assert [a["method"] for a in trace] == ["jina", "playwright"]
    assert len(s.session.calls) == 1
