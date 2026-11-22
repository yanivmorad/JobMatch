"""
HireMeTech דרך ה-API שהאתר עצמו קורא אליו: GET https://hiremetech.com/api/jobs/{id}

בלי התחברות ה-API מחזיר את כל פרטי המשרה: תיאור, ניסיון נדרש, רמה, כישורים, מיקום,
והאם המשרה פעילה. רק שם החברה וקישור ההגשה מוסתרים (employer_masked=true).
עם טוקן תקף (Authorization: Bearer, כמו שהאתר שולח) חוזרים גם הם.

זה מחליף את הדפדפן: הדף עצמו הוא SPA (צריך Playwright או Jina שירנדרו אותו), ובשרת
החינמי אין דפדפן בכלל.
"""
import base64
import json
import re
from datetime import datetime, timezone
from typing import Optional, Tuple
from urllib.parse import urlparse

try:
    from markdownify import markdownify as _md
except ImportError:
    _md = None

API_URL = "https://hiremetech.com/api/jobs/{job_id}"
TIMEOUT = 15
_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}
# /job/147318715, /he-il/job/147318715 (וגם /jobs/ למקרה שהאתר ישנה)
_JOB_PATH = re.compile(r"^/(?:[a-z]{2}-[a-z]{2}/)?jobs?/(\d+)/?$", re.IGNORECASE)
MASKED_COMPANY_NOTE = "(שם החברה מוסתר בדף הציבורי של HireMeTech)"


def is_hiremetech(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "hiremetech.com" or host.endswith(".hiremetech.com")


def job_id(url: str) -> Optional[str]:
    if not is_hiremetech(url):
        return None
    m = _JOB_PATH.match(urlparse(url).path or "")
    return m.group(1) if m else None


def token_expiry(token: str) -> Optional[datetime]:
    """מועד התפוגה (exp) של JWT, בלי לאמת חתימה. None אם זה לא JWT או שאין exp."""
    try:
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)
    except Exception:
        return None


def token_expired(token: str) -> bool:
    exp = token_expiry(token)
    return bool(exp and exp <= datetime.now(timezone.utc))


def fetch_job(job_id_: str, session, token: Optional[str] = None) -> Tuple[int, Optional[dict]]:
    """(קוד HTTP, האובייקט job מהתשובה או None)."""
    headers = dict(_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    res = session.get(API_URL.format(job_id=job_id_), headers=headers, timeout=TIMEOUT)
    if res.status_code != 200:
        return res.status_code, None
    job = (res.json() or {}).get("job")
    return res.status_code, job if isinstance(job, dict) else None


def is_masked(job: dict) -> bool:
    company = job.get("company") if isinstance(job.get("company"), dict) else {}
    return bool(job.get("employer_masked") or company.get("employer_masked"))


def is_closed(job: dict) -> bool:
    return (
        job.get("is_active") is False
        or (job.get("job_status") or "published") != "published"
        or bool(job.get("closure_reason"))
    )


def company_name(job: dict) -> Optional[str]:
    if is_masked(job):
        return None
    company = job.get("company") if isinstance(job.get("company"), dict) else {}
    name = (job.get("company_name") or company.get("name") or "").strip()
    return name or None


def external_url(job: dict) -> Optional[str]:
    """קישור ההגשה באתר החברה (רק למשתמש מחובר). לאורח job_url הוא דף HireMeTech עצמו."""
    for key in ("apply_url", "job_url", "applications_destination"):
        value = job.get(key)
        if isinstance(value, str) and value.startswith("http") and not is_hiremetech(value):
            return value.strip()
    return None


def _experience(job: dict) -> Optional[str]:
    exp = job.get("experience") if isinstance(job.get("experience"), dict) else {}
    low, high = exp.get("min_years"), exp.get("max_years")
    if low is not None and high is not None:
        return f"{low}-{high} years"
    if low is not None:
        return f"{low}+ years"
    if high is not None:
        return f"up to {high} years"
    return None


def _location(job: dict) -> Optional[str]:
    loc = job.get("location") if isinstance(job.get("location"), dict) else {}
    basic = loc.get("basic") if isinstance(loc.get("basic"), dict) else {}
    return basic.get("display_name") or loc.get("full_address") or loc.get("city") or loc.get("country")


def _text(value) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return "\n".join(f"- {v}" for v in value if v)
    value = str(value).strip()
    # בדרך כלל טקסט רגיל עם שורות; markdownify על טקסט רגיל היה מאחד את כל השורות
    if _md and re.search(r"<(p|br|li|ul|div|h\d)\b", value, re.IGNORECASE):
        return _md(value, heading_style="ATX").strip()
    return value


def document(job: dict) -> str:
    """פרטי המשרה כמסמך בפורמט של Jina ("Title: ...") - כמו שאר הסורקים."""
    title = (job.get("title") or "").strip()
    loc = job.get("location") if isinstance(job.get("location"), dict) else {}
    work_model = loc.get("work_model") if isinstance(loc.get("work_model"), dict) else {}
    skills = job.get("skills_required") or job.get("tech_stack") or job.get("skills") or []
    fields = {
        "Company": company_name(job) or MASKED_COMPANY_NOTE,
        "Level": job.get("job_level"),
        "Experience required": _experience(job),
        "Employment type": job.get("employment_type"),
        "Work model": work_model.get("display_tag") or work_model.get("type"),
        "Location": _location(job),
        "Department": job.get("department"),
        "Skills": ", ".join(str(s) for s in skills if s) if isinstance(skills, list) else skills,
        "Posted": job.get("posted_date"),
    }
    lines = [f"Title: {title}", "", f"# {title}"]
    lines += [f"{k}: {v}" for k, v in fields.items() if v]
    sections = [
        ("", job.get("description")),
        ("## Requirements", job.get("requirements")),
        ("## Benefits", job.get("benefits")),
    ]
    body = "\n\n".join(f"{h}\n{_text(v)}".strip() for h, v in sections if _text(v))
    return "\n".join(lines) + "\n\n" + body
