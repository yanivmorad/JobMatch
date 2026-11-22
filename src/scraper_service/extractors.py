# src/scraper_service/extractors.py
"""
מחלצים ייעודיים לאתרי גיוס מוכרים.
עדיפים על סריקה כללית: מחזירים את תיאור המשרה הנקי ישירות מה-API של האתר,
בלי תפריטים, באנרים של עוגיות או תלות בהרצת JavaScript.
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse

import requests

from scraper_service.utils import clean_text

try:
    from markdownify import markdownify as md
except ImportError:  # pragma: no cover
    md = None

logger = logging.getLogger(__name__)

_WORKDAY_HOST = re.compile(r"^(?P<tenant>[^.]+)\.wd\d+\.myworkdayjobs\.com$", re.I)
_LOCALE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class JobNotFoundError(Exception):
    """המשרה לא קיימת יותר באתר (הוסרה / נסגרה)."""


def _html_to_text(html: str) -> str:
    if md:
        return clean_text(md(html))
    return clean_text(re.sub(r"<[^>]+>", " ", html))


def workday_api_url(url: str) -> Optional[str]:
    """
    ממיר לינק של משרה ב-Workday לכתובת ה-API הציבורי שלה.
    https://kla.wd1.myworkdayjobs.com/en-US/Israel/job/X_123
      -> https://kla.wd1.myworkdayjobs.com/wday/cxs/kla/Israel/job/X_123
    מחזיר None אם זה לא לינק משרה של Workday.
    """
    parsed = urlparse(url)
    host_match = _WORKDAY_HOST.match(parsed.netloc)
    if not host_match:
        return None

    parts = [p for p in parsed.path.split("/") if p]
    if parts and _LOCALE.match(parts[0]):
        parts = parts[1:]  # הסרת קידומת שפה (en-US)
    if len(parts) < 3 or "job" not in parts[1:]:
        return None

    site = parts[0]
    job_path = "/".join(parts[parts.index("job", 1) :])
    tenant = host_match.group("tenant")
    return f"https://{parsed.netloc}/wday/cxs/{tenant}/{site}/{job_path}"


def extract_workday(url: str, timeout: int = 20) -> Optional[dict]:
    """
    שולף משרת Workday דרך ה-API הציבורי (אותו API שהאתר עצמו משתמש בו).
    מחזיר None אם הלינק לא של Workday; זורק JobNotFoundError אם המשרה הוסרה.
    """
    api_url = workday_api_url(url)
    if not api_url:
        return None

    headers = {"Accept": "application/json", "User-Agent": _BROWSER_UA}
    for attempt in range(3):
        res = requests.get(api_url, headers=headers, timeout=timeout)
        if res.status_code != 429:
            break
        # הגבלת קצב (למשל כששולחים הרבה משרות Workday בבת אחת) - המתנה קצרה וניסיון חוזר
        try:
            wait = min(float(res.headers.get("Retry-After", 0)) or 3 * (attempt + 1), 10)
        except ValueError:
            wait = 3 * (attempt + 1)
        logger.info(f"Workday rate limit (429), retrying in {wait:.0f}s")
        time.sleep(wait)

    if res.status_code == 404:
        raise JobNotFoundError("המשרה לא נמצאה ב-Workday (כנראה הוסרה או שהלינק חסר)")
    res.raise_for_status()

    info = res.json().get("jobPostingInfo") or {}
    description_html = info.get("jobDescription") or ""
    if not description_html:
        return None

    description = _html_to_text(description_html)
    header = "\n".join(
        line
        for line in [
            info.get("title") and f"Title: {info['title']}",
            info.get("location") and f"Location: {info['location']}",
            info.get("timeType") and f"Type: {info['timeType']}",
        ]
        if line
    )
    return {
        "source": "workday_api",
        "job_title": info.get("title") or None,
        # שם הארגון ב-Workday הוא לרוב קוד יחידה פנימי - עדיף שה-AI יחלץ מהתיאור
        "company": None,
        "full_description": f"{header}\n\n{description}" if header else description,
    }


# סדר הניסיון: מחלצים ייעודיים לפני סריקה כללית
EXTRACTORS = [extract_workday]
