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
    def __init__(self, status_code, text, content_type="text/html", url=None):
        self.status_code = status_code
        self.text = text
        self.headers = {"content-type": content_type}
        self.url = url


# דף SPA: ה-HTML ריק עד שה-JavaScript רץ (מה שהורדה ישירה מקבלת מרוב אתרי ה-ATS)
SPA_SHELL = _Resp(200, "<html><head><title>Careers</title></head><body><div id='root'></div></body></html>")


class _Session:
    """r.jina.ai/... -> jina_resp, כל כתובת אחרת (הורדת ה-HTML הישירה) -> direct_resp."""

    def __init__(self, resp, direct_resp=SPA_SHELL):
        self.resp = resp
        self.direct_resp = direct_resp
        self.headers_seen = None
        self.direct_calls = []

    def get(self, url, headers=None, timeout=None):
        if not url.startswith("https://r.jina.ai/"):
            self.direct_calls.append(url)
            return self.direct_resp
        self.headers_seen = headers
        return self.resp


@pytest.fixture
def make_scraper(monkeypatch):
    def _make(jina_resp, playwright_content=None, key="jina-key", direct_resp=SPA_SHELL):
        if key is None:
            monkeypatch.delenv("JINA_API_KEY", raising=False)
        else:
            monkeypatch.setenv("JINA_API_KEY", key)
        s = Scraper()
        s.session = _Session(jina_resp, direct_resp)
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
    assert trace[1]["method"] == "direct_html" and trace[1]["reason"] == "direct_too_short"
    assert trace[2] == {**trace[2], "method": "playwright", "valid": True, "reason": "ok"}


def test_both_methods_fail_with_reasons(make_scraper):
    s = make_scraper(_Resp(403, "Forbidden"), playwright_content=LOGIN_PAGE)
    trace = []
    assert s.scrape("https://x.com/job", trace=trace) is None
    assert [a["reason"] for a in trace] == ["jina_http_403", "direct_too_short", "bad_title"]


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
        if not url.startswith("https://r.jina.ai/"):
            return SPA_SHELL  # הורדת ה-HTML הישירה
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

    assert [a["method"] for a in trace] == ["jina", "direct_html", "playwright"]
    assert len(s.session.calls) == 1  # Jina פעם אחת


# --- HireMeTech: הכותרת הציבורית "X at Company | HireMe" ---


def test_hiremetech_public_title_does_not_become_the_company(monkeypatch):
    """באג (E2E): ה-AI החזיר "Company | HireMe" כשם החברה לכל משרות HireMeTech."""
    from scraper_service.scraper import Scraper
    from services.job_fields import clean_field

    s = Scraper()
    page = "Title: RPA Developer (UiPath) at Company | HireMe\n\nRequirements: 2+ years of experience with UiPath"
    monkeypatch.setattr(s, "_scrape", lambda *a: {"source": "jina", "full_description": page})

    out = s.scrape("https://hiremetech.com/job/153667177")["full_description"]
    assert "Company | HireMe" not in out
    assert out.startswith("Title: RPA Developer (UiPath) (שם החברה מוסתר")
    # גם אם ה-AI מחזיר את זה - זה placeholder ולא נכתב לעמודה
    assert clean_field("Company | HireMe") is None and clean_field("Company") is None


def test_other_sites_titles_are_untouched(monkeypatch):
    from scraper_service.scraper import Scraper

    s = Scraper()
    page = "Title: Engineer at Company | HireMe\n\nRequirements: experience"
    monkeypatch.setattr(s, "_scrape", lambda *a: {"source": "jina", "full_description": page})
    assert s.scrape("https://jobs.lever.co/acme/1")["full_description"] == page


def test_scrape_falls_back_to_playwright_through_the_public_method(monkeypatch):
    """הנתיב המלא scrape() -> Jina נכשל -> Playwright (תפס NameError על job_id אחרי refactor)."""
    from scraper_service import scraper as scraper_module
    from scraper_service.scraper import Scraper

    s = Scraper()
    monkeypatch.setattr(scraper_module, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(s, "_try_jina", lambda url, tag, trace: None)
    seen = {}

    def fake_playwright(url, job_id=None):
        seen["job_id"] = job_id
        return "Title: Data Analyst\n\nRequirements: 2+ years of experience with SQL. Responsibilities: reports. " * 3

    monkeypatch.setattr(s, "_scrape_with_playwright", fake_playwright)
    trace = []
    result = s.scrape("https://careers.example.com/jobs/1", job_id=42, trace=trace)
    assert result["source"] == "local_browser"
    assert seen["job_id"] == 42
    assert trace[-1]["method"] == "playwright" and trace[-1]["valid"] is True


# --- הורדת ה-HTML הישירה (בלי Jina ובלי דפדפן) ---

from scraper_service.utils import failure_message, is_transient_failure

SERVER_RENDERED = _Resp(
    200,
    """<html><head><title>Job opportunity: Junior Customer Success Manager</title>
<script>var tracking = 'abc';</script><style>.x{color:red}</style></head><body>
<nav><a href="/">Home</a><a href="/about">About us</a></nav>
<main><h1>Junior Customer Success Manager | Ramat Gan, Full-time, Entry-level</h1>
<h4>About The Position</h4><p>MazeBolt empowers organizations to shift from reactive DDoS firefighting
to proactive resilience, ensuring business continuity and measurable risk reduction.</p>
<h4>Requirements</h4><ul><li>1-3 years in a customer-facing role at a B2B technology company</li>
<li>Excellent written and spoken English</li><li>Comfort with CRM tools such as HubSpot</li></ul>
<h4>What You'll Do</h4><ul><li>Own a portfolio of customer accounts day-to-day</li>
<li>Prepare quarterly business reviews for security leaders</li></ul>
</main><footer>All rights reserved</footer></body></html>""",
)
# מה ש-Jina החזיר מהדף של MazeBolt: הפסקה הראשונה בלי הדרישות -> no_job_content
JINA_TRUNCATED = _Resp(
    200,
    "Title: Job opportunity: Junior Customer Success Manager\n\nMarkdown Content:\n"
    + "MazeBolt was named #11 of DUNS 100 top companies to work at in Israel. We have built a culture of trust. " * 3,
)
_MAZEBOLT = "https://mazebolt.com/careers-apply/co/technical-services/0F.476/junior-customer-success-manager/all"


def test_server_rendered_page_that_jina_truncated_is_read_directly(make_scraper):
    """באג (E2E): MazeBolt סומן 'אין מידע' - ב-HTML יש את כל התיאור, Jina החזיר רק פסקה."""
    s = make_scraper(JINA_TRUNCATED, playwright_content=None, direct_resp=SERVER_RENDERED)
    trace = []
    result = s.scrape(_MAZEBOLT, trace=trace)

    assert result["source"] == "direct_html"
    assert [a["method"] for a in trace] == ["jina", "direct_html"]
    assert trace[0]["reason"] == "no_job_content" and trace[1]["valid"] is True
    text = result["full_description"]
    assert "1-3 years in a customer-facing role" in text
    assert text.startswith("Title: Job opportunity: Junior Customer Success Manager")
    assert "tracking" not in text and "color:red" not in text  # script / style
    assert "About us" not in text and "All rights reserved" not in text  # nav / footer


def test_no_direct_download_after_the_site_said_the_job_is_gone(make_scraper):
    gone = _Resp(200, "Title: Drushim\nWarning: Target URL returned error 410: Gone\n\nMarkdown Content:\nx")
    s = make_scraper(gone, playwright_content=None, direct_resp=SERVER_RENDERED)
    assert s.scrape("https://www.drushim.co.il/job/1/a/", trace=[]) is None
    assert s.session.direct_calls == []


def test_spa_shell_after_a_jina_timeout_still_retries(make_scraper):
    """דף SPA ריק בהורדה הישירה לא מכריע 'אין מידע' - Jina רק נפל רגעית."""

    class _JinaDown(_Session):
        def get(self, url, headers=None, timeout=None):
            if url.startswith("https://r.jina.ai/"):
                raise TimeoutError("read timeout")
            return super().get(url, headers, timeout)

    s = make_scraper(None, playwright_content=None)
    s.session = _JinaDown(None)
    trace = []
    assert s.scrape("https://acme.comeet.com/jobs/1", trace=trace) is None
    reasons = [a["reason"] for a in trace]
    assert reasons[:2] == ["jina_error: TimeoutError", "direct_too_short"]
    assert is_transient_failure(reasons)


def test_direct_404_means_the_job_was_removed(make_scraper):
    s = make_scraper(_Resp(500, ""), playwright_content=None, direct_resp=_Resp(404, "Not found"))
    trace = []
    assert s.scrape("https://acme.com/careers/1", trace=trace) is None
    reasons = [a["reason"] for a in trace]
    assert "http_error_404" in reasons
    assert not is_transient_failure(reasons)
    assert "הוסרה" in failure_message(reasons)


def test_direct_redirect_to_the_job_list_is_a_closed_job(make_scraper):
    listing = _Resp(200, SERVER_RENDERED.text, url="https://www.comeet.com/jobs/acme/46.00A")
    s = make_scraper(_Resp(500, ""), playwright_content=None, direct_resp=listing)
    trace = []
    assert s.scrape("https://www.comeet.com/jobs/acme/46.00A/role/12.345", trace=trace) is None
    assert trace[1]["method"] == "direct_html" and trace[1]["reason"] == "job_unavailable"


def test_direct_download_ignores_non_html(make_scraper):
    pdf = _Resp(200, "%PDF-1.7", content_type="application/pdf")
    s = make_scraper(_Resp(500, ""), playwright_content=None, direct_resp=pdf)
    trace = []
    s.scrape("https://acme.com/job.pdf", trace=trace)
    assert trace[1]["reason"] == "direct_not_html"
