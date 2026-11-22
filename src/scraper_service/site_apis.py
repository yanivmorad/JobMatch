"""
חילוץ ישיר מ-API ציבורי של מערכות גיוס (ATS) שהדפים שלהן הם SPA (Workday, BambooHR, HireMeTech).

Jina / Playwright מקבלים מהדפים האלה לפעמים רק שלד ריק (BambooHR: 91 תווים, Workday: 9 תווים
כשהרינדור איטי), אבל אותם אתרים טוענים את המשרה מ-endpoint ציבורי של JSON - אותו endpoint
שהדפדפן של כל מבקר קורא אליו. כאן קוראים אליו ישירות: מהיר, בלי דפדפן, ועם כותרת ושם מעסיק.

    fetch_from_site_api(url, session) -> SiteApiResult | None
        None = האתר לא נתמך כאן (ממשיכים ל-Jina / Playwright)
"""
import os
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlsplit

from scraper_service import hiremetech

try:
    from markdownify import markdownify as _md
except ImportError:  # markdownify הוא חלק מ-requirements, אבל לא נכשיל בלעדיו
    _md = None

TIMEOUT = 15
_HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (JobMatch)"}


@dataclass
class SiteApiResult:
    method: str
    text: Optional[str] = None  # בפורמט של Jina: "Title: ...\n\n<markdown>"
    reason: Optional[str] = None  # "ok" / "job_unavailable" / "api_error: ..."
    status: Optional[int] = None
    company: Optional[str] = None
    job_title: Optional[str] = None


def _to_markdown(html: str) -> str:
    if not html:
        return ""
    if _md:
        return _md(html, heading_style="ATX").strip()
    return re.sub(r"<[^>]+>", " ", html).strip()


def _document(title: str, fields: dict, description_html: str) -> str:
    lines = [f"Title: {title}", "", f"# {title}"]
    lines += [f"{k}: {v}" for k, v in fields.items() if v]
    return "\n".join(lines) + "\n\n" + _to_markdown(description_html)


# --- Workday: https://{tenant}.wd5.myworkdayjobs.com/{locale?}/{site}/job/{...} ---
_WORKDAY_LOCALE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")


def _workday_api_url(url: str) -> Optional[str]:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if not host.endswith(".myworkdayjobs.com"):
        return None
    segments = [s for s in parts.path.split("/") if s]
    if segments and _WORKDAY_LOCALE.match(segments[0]):
        segments = segments[1:]
    if len(segments) < 3 or "job" not in segments[1:]:
        return None
    site = segments[0]
    rest = "/".join(segments[segments.index("job", 1):])
    tenant = host.split(".")[0]
    return f"https://{host}/wday/cxs/{tenant}/{site}/{rest}"


def _workday(url: str, session) -> Optional[SiteApiResult]:
    api = _workday_api_url(url)
    if not api:
        return None
    res = session.get(api, headers=_HEADERS, timeout=TIMEOUT)
    if res.status_code in (404, 410):
        return SiteApiResult("workday_api", reason="job_unavailable", status=res.status_code)
    res.raise_for_status()
    data = res.json()
    info = data.get("jobPostingInfo") or {}
    title = (info.get("title") or "").strip()
    if not title or not info.get("jobDescription"):
        return SiteApiResult("workday_api", reason="api_error: empty posting", status=res.status_code)
    # "400 Flextronics (Israel) Ltd." -> "Flextronics (Israel) Ltd."
    company = re.sub(r"^\d+\s+", "", ((data.get("hiringOrganization") or {}).get("name") or "")).strip() or None
    text = _document(
        title,
        {"Company": company, "Location": info.get("location"), "Time type": info.get("timeType"), "Posted": info.get("postedOn")},
        info["jobDescription"],
    )
    return SiteApiResult("workday_api", text=text, reason="ok", status=res.status_code, company=company, job_title=title)


# --- BambooHR: https://{company}.bamboohr.com/careers/{id}  (או /jobs/view.php?id=) ---
_BAMBOO_CAREERS = re.compile(r"^/careers/(\d+)")


def _bamboohr_job_id(url: str) -> Optional[str]:
    parts = urlsplit(url)
    if not (parts.hostname or "").lower().endswith(".bamboohr.com"):
        return None
    m = _BAMBOO_CAREERS.match(parts.path)
    if m:
        return m.group(1)
    if parts.path.rstrip("/").endswith("/jobs/view.php"):
        return (parse_qs(parts.query).get("id") or [None])[0]
    return None


def _bamboohr(url: str, session) -> Optional[SiteApiResult]:
    job_id = _bamboohr_job_id(url)
    if not job_id:
        return None
    host = urlsplit(url).hostname
    res = session.get(f"https://{host}/careers/{job_id}/detail", headers=_HEADERS, timeout=TIMEOUT)
    if res.status_code in (404, 410):
        return SiteApiResult("bamboohr_api", reason="job_unavailable", status=res.status_code)
    res.raise_for_status()
    job = ((res.json().get("result") or {}).get("jobOpening")) or {}
    title = (job.get("jobOpeningName") or "").strip()
    if (job.get("jobOpeningStatus") or "").lower() not in ("", "open"):
        return SiteApiResult("bamboohr_api", reason="job_unavailable", status=res.status_code, job_title=title or None)
    if not title or not job.get("description"):
        return SiteApiResult("bamboohr_api", reason="api_error: empty posting", status=res.status_code)
    loc = job.get("location") or {}
    location = ", ".join(v for v in (loc.get("city"), loc.get("state"), loc.get("addressCountry")) if v)
    text = _document(
        title,
        {
            # ה-API לא מחזיר את שם החברה; תת-הדומיין (rapaport.bamboohr.com) הוא רמז ל-AI
            "Careers site": host.split(".")[0],
            "Location": location,
            "Employment": job.get("employmentStatusLabel"),
            "Department": job.get("departmentLabel"),
            "Minimum experience": job.get("minimumExperience"),
        },
        job["description"],
    )
    return SiteApiResult("bamboohr_api", text=text, reason="ok", status=res.status_code, job_title=title)


# --- HireMeTech: https://hiremetech.com/job/{id} -> /api/jobs/{id} (ראו hiremetech.py) ---


def _hiremetech(url: str, session) -> Optional[SiteApiResult]:
    job_id = hiremetech.job_id(url)
    if not job_id:
        return None
    # עם טוקן תקף ה-API מחזיר גם את שם החברה; טוקן שפג / נדחה -> הגרסה הציבורית
    token = (os.getenv("HIRE_ME_TECH_TOKEN") or "").strip()
    if token and hiremetech.token_expired(token):
        token = ""
    status, job = hiremetech.fetch_job(job_id, session, token or None)
    if token and status in (401, 403):
        status, job = hiremetech.fetch_job(job_id, session)
    if status in (404, 410):
        return SiteApiResult("hiremetech_api", reason="job_unavailable", status=status)
    if status != 200 or not job:
        return SiteApiResult("hiremetech_api", reason=f"api_error: http {status}", status=status)
    title = (job.get("title") or "").strip()
    if hiremetech.is_closed(job):
        return SiteApiResult("hiremetech_api", reason="job_unavailable", status=status, job_title=title or None)
    if not title:
        return SiteApiResult("hiremetech_api", reason="api_error: empty posting", status=status)
    if not any((job.get(k) or "") for k in ("description", "requirements")):
        # יש משרות שב-HireMeTech יש להן רק כותרת ("תיאור המשרה אינו זמין"). באג (E2E): Jina סרק
        # את הדף הזה, וה-AI נתן ציון על סמך הכותרת בלבד
        return SiteApiResult("hiremetech_api", reason="hiremetech_no_description", status=status, job_title=title)
    return SiteApiResult(
        "hiremetech_api",
        text=hiremetech.document(job),
        reason="ok",
        status=status,
        company=hiremetech.company_name(job),
        job_title=title,
    )


_HANDLERS = (("workday_api", _workday), ("bamboohr_api", _bamboohr), ("hiremetech_api", _hiremetech))


def fetch_from_site_api(url: str, session) -> Optional[SiteApiResult]:
    """None אם האתר לא נתמך. שגיאת רשת / JSON לא צפוי -> reason='api_error: ...' (ואז ממשיכים ל-Jina)."""
    for name, handler in _HANDLERS:
        try:
            result = handler(url, session)
        except Exception as e:
            return SiteApiResult(name, reason=f"api_error: {type(e).__name__}")
        if result is not None:
            return result
    return None
