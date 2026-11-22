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
    def __init__(self, status, payload=None, html=False):
        self.status_code = status
        self._payload = payload
        self._html = html

    def json(self):
        if self._html:  # requests זורק ValueError (JSONDecodeError) על גוף שאינו JSON
            raise ValueError("Expecting value")
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


# התשובות האמיתיות של Workday (נבדקו מול amat.wd1.myworkdayjobs.com, 2026-11-22)
_WD_UNPOSTED = {"errorCode": "S22", "errorCaseId": "F7C5BDMWS9ZP6I", "httpStatus": 403, "message": "permission denied", "messageParams": {}}
_WD_NOT_FOUND = {"errorCode": "S21", "httpStatus": 404, "message": "not found: Job_Posting_Anchor_ID=Fake_R0000001", "messageParams": {}}


def test_workday_unposted_job_is_closed_not_a_login_wall():
    """באג: משרה שהוסרה (R2614690) -> 403 S22 -> נחשב לתקלה -> Playwright ראה דף התחברות ->
    'האתר דורש התחברות'. עכשיו: המשרה סגורה."""
    r = fetch_from_site_api(_WD_URL, _Session({_WD_API: _Resp(403, _WD_UNPOSTED)}))
    assert r.reason == "job_unavailable" and r.status == 403


def test_workday_missing_job_json_404():
    assert fetch_from_site_api(_WD_URL, _Session({_WD_API: _Resp(404, _WD_NOT_FOUND)})).reason == "job_unavailable"


@pytest.mark.parametrize(
    "resp",
    [
        _Resp(403, html=True),  # דף חסימה (WAF / Cloudflare) - לא JSON
        _Resp(403, {"error": "forbidden"}),  # JSON שאינו של Workday
        _Resp(403, ["not", "a", "dict"]),
        _Resp(500, {"errorCode": "S99", "httpStatus": 500}),
    ],
    ids=["html_403", "foreign_json_403", "list_json_403", "server_error"],
)
def test_workday_other_errors_fall_through_to_the_scrapers(resp):
    """רק ה-403 של Workday עצמו אומר שהמשרה הוסרה; כל שגיאה אחרת -> ממשיכים ל-Jina / Playwright."""
    r = fetch_from_site_api(_WD_URL, _Session({_WD_API: resp}))
    assert r.reason.startswith("api_error")


def test_scraper_reports_an_unposted_workday_job_as_closed(monkeypatch):
    """מקצה לקצה בסורק: בלי Jina / HTML / Playwright, והודעה למשתמש 'המשרה סגורה'."""
    from scraper_service.utils import failure_message

    s = _scraper(_Session({_WD_API: _Resp(403, _WD_UNPOSTED)}))
    monkeypatch.setattr(s, "_try_jina", lambda *a, **k: pytest.fail("no Jina for a closed job"))
    monkeypatch.setattr(s, "_try_direct_html", lambda *a, **k: pytest.fail("no direct HTML for a closed job"))
    monkeypatch.setattr(s, "_scrape_with_playwright", lambda *a, **k: pytest.fail("no Playwright for a closed job"))
    trace = []
    assert s.scrape(_WD_URL, trace=trace) is None
    assert [a["reason"] for a in trace] == ["job_unavailable"]
    assert failure_message([a["reason"] for a in trace]) == "המשרה סגורה או אינה זמינה יותר"


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


# --- HireMeTech: /api/jobs/{id} (התיאור המלא גם בלי התחברות; החברה מוסתרת) ---

import base64
import json
from datetime import datetime, timedelta, timezone

from scraper_service import hiremetech

_HMT_URL = "https://hiremetech.com/he-il/job/152001956?f=1"
_HMT_API = "https://hiremetech.com/api/jobs/152001956"
_HMT_DESC = (
    "דרישות:\n✔ ניסיון של שנה עד שנתיים בפיתוח Full Stack\n✔ ניסיון מוכח ב־C#, .NET Framework ו־SQL\n"
    "מה אנחנו מציעים?\n• משרה מלאה | אזור המרכז\nלהגשת קורות חיים:\n📧 jobs@giv-solutions.com"
)


def _hmt_job(**overrides):
    """בצורה של התשובה האמיתית לאורח (2026-11-22)."""
    job = {
        "id": 152001956,
        "title": "Full Stack Developer",
        "company_name": "",
        "company": {"name": "", "employer_masked": True},
        "employer_masked": True,
        "location": {"basic": {"display_name": "Israel"}, "work_model": {"display_tag": "On-site"}},
        "employment_type": "Full-time",
        "job_level": "Junior / Entry Level",
        "department": "Software Engineering",
        "skills_required": ["C#", ".NET Framework", "SQL", "React"],
        "experience": {"min_years": 1, "max_years": 2},
        "posted_date": "2026-10-26",
        "description": _HMT_DESC,
        "is_active": True,
        "job_status": "published",
        "closure_reason": None,
        "job_url": "https://hiremetech.com/job/152001956",
        "apply_url": None,
    }
    job.update(overrides)
    return job


class _HmtSession:
    """מחזיר תשובה לפי הטוקן: {None: guest_resp, "<token>": resp}. שומר את הכותרות."""

    def __init__(self, by_token):
        self.by_token = by_token
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        auth = (headers or {}).get("Authorization")
        self.calls.append((url, auth))
        token = auth.split(" ", 1)[1] if auth else None
        return self.by_token.get(token, _Resp(500))


def _jwt(days):
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    exp = datetime.now(timezone.utc) + timedelta(days=days)
    return f"{b64({'alg': 'HS256'})}.{b64({'exp': int(exp.timestamp())})}.sig"


@pytest.mark.parametrize(
    "url, job_id",
    [
        ("https://hiremetech.com/job/147318715", "147318715"),
        ("https://hiremetech.com/he-il/job/153667177?f=1", "153667177"),
        ("https://www.hiremetech.com/job/1/", "1"),
        ("https://hiremetech.com/companies/5", None),
        ("https://acme.com/job/1", None),
    ],
)
def test_hiremetech_job_id(url, job_id):
    assert hiremetech.job_id(url) == job_id


def test_hiremetech_guest_api_gives_the_full_description(monkeypatch):
    """בלי טוקן: כל הפרטים חוץ משם החברה - ובלי דפדפן (אין Playwright בשרת החינמי)."""
    monkeypatch.delenv("HIRE_ME_TECH_TOKEN", raising=False)
    session = _HmtSession({None: _Resp(200, {"job": _hmt_job()})})
    r = fetch_from_site_api(_HMT_URL, session)

    assert r.reason == "ok" and r.method == "hiremetech_api"
    assert r.job_title == "Full Stack Developer" and r.company is None
    assert session.calls == [(_HMT_API, None)]
    assert r.text.startswith("Title: Full Stack Developer\n")
    # בלי שורת Company: עם הערה "החברה מוסתרת ב-HireMeTech" ה-AI כתב "HireMeTech" כשם החברה
    assert "Company:" not in r.text and "HireMeTech" not in r.text
    assert "Experience required: 1-2 years" in r.text and "Level: Junior / Entry Level" in r.text
    assert "Skills: C#, .NET Framework, SQL, React" in r.text
    # התיאור הוא טקסט רגיל עם שורות - לא לאחד אותן (markdownify היה מאחד)
    assert "✔ ניסיון של שנה עד שנתיים בפיתוח Full Stack\n✔ ניסיון מוכח" in r.text


def test_hiremetech_with_a_valid_token_gets_the_company(monkeypatch):
    token = _jwt(days=3)
    monkeypatch.setenv("HIRE_ME_TECH_TOKEN", token)
    job = _hmt_job(employer_masked=False, company={"name": "Giv Solutions"}, company_name="Giv Solutions")
    r = fetch_from_site_api(_HMT_URL, _HmtSession({token: _Resp(200, {"job": job})}))
    assert r.company == "Giv Solutions"
    assert "Company: Giv Solutions" in r.text


def test_hiremetech_rejected_token_falls_back_to_the_guest_view(monkeypatch):
    token = _jwt(days=3)
    monkeypatch.setenv("HIRE_ME_TECH_TOKEN", token)
    session = _HmtSession({token: _Resp(401), None: _Resp(200, {"job": _hmt_job()})})
    r = fetch_from_site_api(_HMT_URL, session)
    assert r.reason == "ok" and r.company is None
    assert [auth for _, auth in session.calls] == [f"Bearer {token}", None]


def test_hiremetech_expired_token_is_not_sent(monkeypatch):
    monkeypatch.setenv("HIRE_ME_TECH_TOKEN", _jwt(days=-1))
    session = _HmtSession({None: _Resp(200, {"job": _hmt_job()})})
    assert fetch_from_site_api(_HMT_URL, session).reason == "ok"
    assert session.calls == [(_HMT_API, None)]


@pytest.mark.parametrize(
    "resp",
    [
        _Resp(404, {"detail": "Job 1 not found. The job may have been removed"}),
        _Resp(200, {"job": _hmt_job(is_active=False)}),
        _Resp(200, {"job": _hmt_job(job_status="closed")}),
        _Resp(200, {"job": _hmt_job(closure_reason="filled")}),
    ],
)
def test_hiremetech_closed_or_removed_job(monkeypatch, resp):
    monkeypatch.delenv("HIRE_ME_TECH_TOKEN", raising=False)
    assert fetch_from_site_api(_HMT_URL, _HmtSession({None: resp})).reason == "job_unavailable"


def test_hiremetech_api_error_falls_through(monkeypatch):
    monkeypatch.delenv("HIRE_ME_TECH_TOKEN", raising=False)
    assert fetch_from_site_api(_HMT_URL, _HmtSession({None: _Resp(503)})).reason.startswith("api_error")


def test_scraper_reads_hiremetech_through_the_api(monkeypatch):
    monkeypatch.delenv("HIRE_ME_TECH_TOKEN", raising=False)
    s = _scraper(_HmtSession({None: _Resp(200, {"job": _hmt_job()})}))
    monkeypatch.setattr(s, "_try_jina", lambda *a, **k: pytest.fail("Jina should not render the SPA"))
    result = s.scrape("https://hiremetech.com/job/152001956", trace=[])
    assert result["source"] == "hiremetech_api"
    assert result["job_title"] == "Full Stack Developer" and result["company"] is None
    assert "Company | HireMe" not in result["full_description"]


def test_hiremetech_job_without_a_description_is_final(monkeypatch):
    """ל-HireMeTech יש משרות עם כותרת בלבד - לא שולחים ל-AI, ולא מנסים סורק אחר."""
    from scraper_service.utils import failure_message, is_transient_failure

    monkeypatch.delenv("HIRE_ME_TECH_TOKEN", raising=False)
    s = _scraper(_HmtSession({None: _Resp(200, {"job": _hmt_job(description="", requirements=None)})}))
    monkeypatch.setattr(s, "_try_jina", lambda *a, **k: pytest.fail("no fallback when the API has no description"))
    trace = []
    assert s.scrape("https://hiremetech.com/job/143575413", trace=trace) is None
    reasons = [a["reason"] for a in trace]
    assert reasons == ["hiremetech_no_description"]
    assert not is_transient_failure(reasons)
    assert "טוקן HireMeTech" in failure_message(reasons)
