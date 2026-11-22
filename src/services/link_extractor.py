"""
חילוץ קישורי משרות מטקסט גולמי (הודעות וואטסאפ / טלגרם / פוסטים).

    extract_job_links(text) -> ExtractedLinks(jobs=[...], ignored=[{"url", "reason"}])

- מוצא כל URL בטקסט. ה-URL נעצר בתו הראשון שאינו חוקי ב-URL (רווח, עברית, אימוג'י),
  כך ש-"https://x.com/jobs/abcערב טוב" (קישור שהודבק צמוד לטקסט) לא "בולע" את המילים.
- מסנן קישורים שאינם משרות (חנויות אפליקציות, קבוצות וואטסאפ / טלגרם, רשתות חברתיות,
  דפי קהילות / מיטאפים של HireMeTech, דפי בית) - עם סיבה, כדי שאפשר יהיה להציג אותם.
- מנרמל (normalize_job_url): מוריד פרמטרי מעקב (utm_*, fbclid, trk...) ו-#fragment,
  כך שאותה משרה שהגיעה משתי קבוצות שונות מזוהה ככפולה.

זהו המקור היחיד לחילוץ קישורים: הדשבורד (POST /api/jobs/raw) ובהמשך הבוט משתמשים בו.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# תווים חוקיים ב-URL לפי RFC 3986 (ASCII בלבד)
_URL_RE = re.compile(
    r"(?:https?://|www\.)[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+", re.IGNORECASE
)
# סימנים שנדבקים לסוף קישור בטקסט ואינם חלק ממנו ("...", "*bold*", "(קישור)")
_TRAILING = ".,;:!?*'\"]}>"

# פרמטרי מעקב שלא משנים את תוכן הדף
_TRACKING_PARAMS = {
    "fbclid", "gclid", "dclid", "msclkid", "igshid", "mc_cid", "mc_eid",
    "_hsenc", "_hsmi", "trk", "trackingid", "refid", "lipi", "original_referer",
}

# אתרים שהקישורים אליהם אינם משרות (תת-דומיינים נכללים)
_IGNORED_HOSTS = {
    "apps.apple.com": "חנות אפליקציות",
    "play.google.com": "חנות אפליקציות",
    "chat.whatsapp.com": "קבוצת וואטסאפ",
    "whatsapp.com": "וואטסאפ",
    "wa.me": "וואטסאפ",
    "t.me": "טלגרם",
    "telegram.me": "טלגרם",
    "facebook.com": "פייסבוק",
    "fb.me": "פייסבוק",
    "instagram.com": "אינסטגרם",
    "youtube.com": "יוטיוב",
    "youtu.be": "יוטיוב",
    "tiktok.com": "טיקטוק",
    "twitter.com": "טוויטר",
    "x.com": "טוויטר",
    "meetup.com": "מיטאפ",
    "zoom.us": "זום",
    "calendly.com": "זימון פגישה",
    "linktr.ee": "דף קישורים",
    "discord.gg": "דיסקורד",
    "discord.com": "דיסקורד",
}

_HIREMETECH_JOB_PATH = re.compile(r"^/(?:[a-z]{2}-[a-z]{2}/)?job/\d+/?$", re.IGNORECASE)
_LINKEDIN_JOB_PATH = re.compile(r"/jobs/view/", re.IGNORECASE)


@dataclass
class ExtractedLinks:
    jobs: List[str] = field(default_factory=list)
    ignored: List[dict] = field(default_factory=list)


def _host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _trim(url: str) -> str:
    while url and url[-1] in _TRAILING + ")":
        # סוגר שהוא חלק מה-URL (למשל ויקיפדיה) נשאר, סוגר של טקסט מסביב יורד
        if url[-1] == ")" and url.count("(") >= url.count(")"):
            break
        url = url[:-1]
    return url


def _is_tracking(key: str) -> bool:
    key = key.lower()
    return key.startswith("utm_") or key in _TRACKING_PARAMS


def normalize_job_url(url: str) -> str:
    """
    צורה קנונית של קישור משרה (להשוואת כפילויות ולשמירה ב-DB):
    scheme + host באותיות קטנות, בלי פרמטרי מעקב, בלי #fragment, בלי '?' ריק בסוף.
    LinkedIn: ...?currentJobId=123 -> https://www.linkedin.com/jobs/view/123/
    """
    url = (url or "").strip()
    if url.lower().startswith("www."):
        url = "https://" + url
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.port:
        host = f"{host}:{parts.port}"
    query = parse_qsl(parts.query, keep_blank_values=True)

    if _host_matches(host, "linkedin.com") and not _LINKEDIN_JOB_PATH.search(parts.path):
        job_id = dict(query).get("currentJobId")
        if job_id and job_id.isdigit():
            return f"https://www.linkedin.com/jobs/view/{job_id}/"

    clean_query = urlencode([(k, v) for k, v in query if not _is_tracking(k)])
    return urlunsplit((parts.scheme.lower() or "https", host, parts.path, clean_query, ""))


def ignore_reason(url: str) -> Optional[str]:
    """None = נראה כמו קישור למשרה. אחרת - הסיבה שהקישור אינו משרה (מוצגת למשתמש)."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if not host or "." not in host:
        return "קישור לא תקין"
    for domain, label in _IGNORED_HOSTS.items():
        if _host_matches(host, domain):
            return f"לא משרה ({label})"
    path = parts.path or "/"
    if _host_matches(host, "hiremetech.com") and not _HIREMETECH_JOB_PATH.match(path):
        return "דף כללי של HireMeTech (לא משרה)"
    if _host_matches(host, "linkedin.com") and not _LINKEDIN_JOB_PATH.search(path):
        return "דף לינקדאין שאינו משרה (פוסט / פרופיל / חברה)"
    if path.strip("/") == "" and not parts.query:
        return "דף בית, לא משרה"
    return None


def extract_job_links(text: str) -> ExtractedLinks:
    """כל קישורי המשרות בטקסט, מנורמלים, בלי כפילויות, לפי סדר ההופעה."""
    result = ExtractedLinks()
    seen = set()
    for match in _URL_RE.finditer(text or ""):
        raw = _trim(match.group(0))
        if not raw:
            continue
        url = normalize_job_url(raw)
        if url in seen:
            continue
        seen.add(url)
        reason = ignore_reason(url)
        if reason:
            result.ignored.append({"url": url, "reason": reason})
        else:
            result.jobs.append(url)
    return result
