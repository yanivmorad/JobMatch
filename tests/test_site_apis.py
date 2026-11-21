"""
חילוץ מ-API ציבורי של Workday / BambooHR (דפי SPA שהסורקים קיבלו מהם שלד ריק:
BambooHR 91 תווים, Workday 9 תווים). בלי רשת: session מזויף עם תשובות בצורה של ה-API האמיתי.
"""
import pytest

from scraper_service import site_apis
from scraper_service.scraper import Scraper
from scraper_service.site_apis import _bamboohr_job_id, _workday_api_url, fetch_from_site_api

_DESC = (
    "<p>We are looking for an analyst.</p><h3>Requirements</h3><ul><li>2+ years of experience</li>"
    "<li>Strong SQL skills</li></ul><h3>Responsibilities</h3><p>You will build reports and dashboards "
    "for the operations team, working with stakeholders across the company.</p>" * 2
)


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Session:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        return self.routes.get(url, _Resp(404))


# --- זיהוי כתובות ---


@pytest.mark.parametrize(
    "url, api",
    [
        (
            "https://flextronics.wd1.myworkdayjobs.com/he-IL/Careers/job/Israel-Migdal-Ha-Emek/Material-Quotation-Analyst_WD230441",
            "https://flextronics.wd1.myworkdayjobs.com/wday/cxs/flextronics/Careers/job/Israel-Migdal-Ha-Emek/Material-Quotation-Analyst_WD230441",
        ),
        (
            "https://amat.wd1.myworkdayjobs.com/External/job/RehovotISR/PWP-reaserch-Student_R2614690",
            "https://amat.wd1.myworkdayjobs.com/wday/cxs/amat/External/job/RehovotISR/PWP-reaserch-Student_R2614690",
        ),
    ],
)
def test_workday_api_url(url, api):
    assert _workday_api_url(url) == api


def test_workday_non_job_pages_are_not_handled():
    assert _workday_api_url("https://amat.wd1.myworkdayjobs.com/External") is None
    assert _workday_api_url("https://example.com/job/1") is None


def test_bamboohr_job_id():
    assert _bamboohr_job_id("https://rapaport.bamboohr.com/careers/307") == "307"
    assert _bamboohr_job_id("https://acme.bamboohr.com/jobs/view.php?id=12") == "12"
    assert _bamboohr_job_id("https://acme.bamboohr.com/careers") is None
    assert _bamboohr_job_id("https://jobs.lever.co/acme/1") is None


def test_unsupported_site_returns_none_without_requests():
    session = _Session({})
    assert fetch_from_site_api("https://jobs.lever.co/acme/1", session) is None
    assert session.calls == []


# --- Workday ---

_WD_URL = "https://flextronics.wd1.myworkdayjobs.com/he-IL/Careers/job/Israel/Analyst_WD1"
_WD_API = "https://flextronics.wd1.myworkdayjobs.com/wday/cxs/flextronics/Careers/job/Israel/Analyst_WD1"


def test_workday_posting_becomes_a_job_document():
    session = _Session(
        {
            _WD_API: _Resp(
                200,
                {
                    "jobPostingInfo": {"title": "Material Quotation Analyst", "jobDescription": _DESC, "location": "Israel, Migdal Ha-Emek"},
                    "hiringOrganization": {"name": "400 Flextronics (Israel) Ltd."},
                },
            )
        }
    )
    r = fetch_from_site_api(_WD_URL, session)
    assert r.reason == "ok" and r.method == "workday_api"
    assert r.job_title == "Material Quotation Analyst"
    assert r.company == "Flextronics (Israel) Ltd."  # בלי הקידומת המספרית
    assert r.text.startswith("Title: Material Quotation Analyst")
    assert "Requirements" in r.text and "<li>" not in r.text  # HTML -> markdown


def test_workday_removed_job():
    r = fetch_from_site_api(_WD_URL, _Session({_WD_API: _Resp(404)}))
    assert r.reason == "job_unavailable"


def test_workday_network_error_falls_through():
    class _Boom:
        def get(self, *a, **k):
            raise ConnectionError("down")

    assert fetch_from_site_api(_WD_URL, _Boom()).reason.startswith("api_error")


# --- BambooHR ---

_BB_URL = "https://rapaport.bamboohr.com/careers/307"
_BB_API = "https://rapaport.bamboohr.com/careers/307/detail"


def _bamboo(status="Open"):
    return {
        "result": {
            "jobOpening": {
                "jobOpeningName": "Customer Success Operations Specialist - Student",
                "jobOpeningStatus": status,
                "description": _DESC,
                "location": {"city": "Jerusalem", "state": "Israel", "addressCountry": "Israel"},
                "employmentStatusLabel": "Part-Time",
            }
        }
    }


def test_bamboohr_open_job():
    r = fetch_from_site_api(_BB_URL, _Session({_BB_API: _Resp(200, _bamboo())}))
    assert r.reason == "ok" and r.method == "bamboohr_api"
    assert r.job_title == "Customer Success Operations Specialist - Student"
    assert "Jerusalem" in r.text and "Part-Time" in r.text


def test_bamboohr_closed_or_missing_job():
    assert fetch_from_site_api(_BB_URL, _Session({_BB_API: _Resp(200, _bamboo("Filled"))})).reason == "job_unavailable"
    assert fetch_from_site_api(_BB_URL, _Session({})).reason == "job_unavailable"  # 404


# --- שילוב בסורק ---


def _scraper(session):
    s = Scraper()
    s.session = session
    return s


def test_scraper_uses_the_api_and_returns_company_and_title(monkeypatch):
    def no_jina(*a, **k):
        raise AssertionError("Jina should not be called when the API worked")

    s = _scraper(_Session({_BB_API: _Resp(200, _bamboo())}))
    monkeypatch.setattr(s, "_try_jina", no_jina)
    trace = []
    result = s.scrape(_BB_URL, trace=trace)
    assert result["source"] == "bamboohr_api"
    assert result["job_title"].startswith("Customer Success")
    assert trace[0]["method"] == "bamboohr_api" and trace[0]["valid"] is True


def test_scraper_stops_when_the_api_says_the_job_is_closed(monkeypatch):
    s = _scraper(_Session({_BB_API: _Resp(200, _bamboo("Closed"))}))
    monkeypatch.setattr(s, "_try_jina", lambda *a, **k: pytest.fail("no fallback for a closed job"))
    trace = []
    assert s.scrape(_BB_URL, trace=trace) is None
    assert [a["reason"] for a in trace] == ["job_unavailable"]


def test_scraper_falls_back_to_jina_when_the_api_fails(monkeypatch):
    class _Boom:
        def get(self, *a, **k):
            raise TimeoutError

    s = _scraper(_Boom())
    monkeypatch.setattr(s, "_try_jina", lambda url, tag, trace: {"source": "jina", "full_description": "x"})
    assert s.scrape(_BB_URL, trace=[])["source"] == "jina"
