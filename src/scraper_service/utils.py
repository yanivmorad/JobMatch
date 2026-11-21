# src/scraper_service/utils.py
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

MIN_LENGTH = 150
MIN_JOB_SIGNALS = 2

# --- תמיד פוסל: המשרה סגורה ---
_JOB_UNAVAILABLE = (
    "no longer accepting applications",  # LinkedIn
    "this job is no longer available",
    "job is no longer available",
    "this position is no longer available",
    "position has been filled",
    "this job has expired",
    "job posting has expired",
    "job you are looking for is no longer",  # Greenhouse / Lever
    "המשרה אינה זמינה",
    "המשרה לא זמינה",
    "המשרה כבר לא זמינה",
    "המשרה אינה פעילה",
    "משרה זו אינה פעילה",
    "המשרה הוסרה",
    "המשרה נסגרה",
)

# --- תמיד פוסל: דף הגנת בוטים (ביטויים שלא מופיעים בתיאור משרה) ---
_BLOCKED = (
    "just a moment...",  # Cloudflare
    "checking your browser",
    "verify you are human",
    "enable javascript and cookies to continue",
    "attention required! | cloudflare",
    "are you a robot",
    "unusual traffic from your computer",
)

# --- פוסל רק אם אין מספיק תוכן של משרה ---
# (ביטויי שגיאה יכולים להופיע בתיאור אמיתי, למשל משרת QA / אבטחה)
_ERROR_PAGE = (
    "access denied",
    "403 forbidden",
    "404 not found",
    "page not found",
    "this page doesn't exist",
    "this page does not exist",
    "הדף לא נמצא",
    "העמוד לא נמצא",
    "הדף המבוקש לא נמצא",
)
_CAPTCHA = ("captcha", "robot check")  # למשל "This site is protected by reCAPTCHA" ב-Greenhouse
_LOGIN = (
    "sign in",
    "log in",
    "login",
    "forgot password",
    "join now",
    "התחברות",
    "התחבר",
    "שכחת סיסמה",
    "שכחתי סיסמה",
)
_COOKIES = ("cookie", "עוגיות")

# כותרת הדף (שורת Title של Jina / <title>) שמעידה על דף שאינו משרה.
# גבולות מילה: "Req 40412" או "Blogin" לא אמורים להיפסל.
_BAD_TITLE = re.compile(
    r"\bsign ?(in|up)\b|\blog ?in\b|just a moment|access denied|page not found|\b404\b|התחברות",
    re.IGNORECASE,
)
# כותרת "הדף לא נמצא" = המשרה הוסרה / הקישור שגוי (ולא דף התחברות)
_NOT_FOUND_TITLE = re.compile(
    r"page not found|not found|\b404\b|\b410\b|הדף לא נמצא|העמוד לא נמצא", re.IGNORECASE
)

# מילים שמופיעות כמעט בכל תיאור משרה. סופרים כמה שונות מופיעות.
_JOB_SIGNALS = (
    "requirement",
    "responsibilit",
    "qualification",
    "experience",
    "years of",
    "skills",
    "what you'll do",
    "what you will do",
    "about the role",
    "about the job",
    "job description",
    "we are looking for",
    "we're looking for",
    "you will",
    "full-time",
    "full time",
    "benefits",
    "דרישות",
    "תיאור המשרה",
    "תיאור התפקיד",
    "ניסיון",
    "אחריות",
    "מחפשים",
    "השכלה",
    "יתרון",
    "היקף משרה",
    "משרה מלאה",
    "כישורים",
    "התפקיד כולל",
    # ניסוחים נפוצים נוספים (למשל Greenhouse של ScaleOps: "Who you are" / "What you bring")
    "who you are",
    "what you bring",
    "what you'll bring",
    "about you",
    "nice to have",
    "must have",
    "bonus points",
    "degree in",
    "knowledge of",
    "familiarity with",
    "track record",
    "what we offer",
    "hands-on",
    "proficien",
    "תואר",
    "היכרות עם",
    "תחומי אחריות",
    "דרישות התפקיד",
    "המשרה כוללת",
)

# שורות הכותרת ש-Jina מוסיף לפני התוכן
_JINA_HEADER = re.compile(
    r"^(Title|URL Source|Final URL|Published Time|Markdown Content|Warning):.*$",
    re.MULTILINE,
)
# Jina (וגם ה-fallback של Playwright) מוסיפים "Final URL:" כשהיתה הפניה
_FINAL_URL = re.compile(r"^Final URL:\s*(\S+)", re.MULTILINE)
# סימנים ב-URL הסופי שהמשרה כבר לא קיימת (LinkedIn: trk=expired_jd_redirect, Greenhouse: ?error=true)
_UNAVAILABLE_URL_MARKERS = ("expired", "error=true", "jobnotfound", "job-not-found")


def _site_key(host: str) -> str:
    """br.linkedin.com -> linkedin.com, www.alljobs.co.il -> alljobs.co.il"""
    labels = (host or "").lower().split(".")
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in ("co", "com", "org", "net", "ac", "gov"):
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def redirected_away(requested_url: Optional[str], final_url: Optional[str]) -> bool:
    """
    True אם ההפניה מעידה שהמשרה הוסרה:
    - ה-URL הסופי מסומן כפג תוקף / שגיאה, או
    - הפניה "למעלה" באותו אתר: לרשימת המשרות של החברה או לדף הבית
      (Comeet: /jobs/acme/46.00A/role/12.345 -> /jobs/acme/46.00A).
    הפניה לאתר אחר (HireMeTech -> Comeet) או לעמוד משרה אחר - תקינה.
    """
    if not requested_url or not final_url:
        return False
    if any(m in final_url.lower() for m in _UNAVAILABLE_URL_MARKERS) and not any(
        m in requested_url.lower() for m in _UNAVAILABLE_URL_MARKERS
    ):
        return True
    rq, fn = urlparse(requested_url), urlparse(final_url)
    if _site_key(rq.hostname) != _site_key(fn.hostname):
        return False
    req_path, final_path = rq.path.rstrip("/"), fn.path.rstrip("/")
    return final_path != req_path and req_path.startswith(final_path + "/")
_JINA_HTTP_ERROR = re.compile(r"Target URL returned error (\d{3})")
_TITLE_LINE = re.compile(r"^Title:\s*(.*)$", re.MULTILINE)
_HTML_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _find(text: str, markers) -> Optional[str]:
    return next((m for m in markers if m in text), None)


def count_job_signals(text: str) -> int:
    lowered = text.lower()
    return sum(1 for s in _JOB_SIGNALS if s in lowered)


def validate_content(text: str, url: Optional[str] = None) -> Tuple[bool, str]:
    """
    בודק שהטקסט שנסרק הוא באמת תיאור משרה, ולא דף התחברות / cookies / חסימה / משרה סגורה.
    url: הכתובת שביקשנו - כדי לזהות הפניה לרשימת המשרות / דף הבית (משרה שהוסרה).

    Returns:
        (True, "ok") או (False, reason), כש-reason הוא אחד מ:
        empty, too_short, http_error_<code>, job_unavailable, blocked, bad_title,
        error_page, captcha, login_wall, cookie_wall, no_job_content
    """
    if not text or not text.strip():
        return False, "empty"

    http_error = _JINA_HTTP_ERROR.search(text)
    if http_error and http_error.group(1)[0] in "45":
        return False, f"http_error_{http_error.group(1)}"

    final_url = _FINAL_URL.search(text)
    if final_url and redirected_away(url, final_url.group(1)):
        return False, "job_unavailable"

    lowered = text.lower()

    if _find(lowered, _JOB_UNAVAILABLE):
        return False, "job_unavailable"
    if _find(lowered, _BLOCKED):
        return False, "blocked"

    title_match = _TITLE_LINE.search(text) or _HTML_TITLE.search(text)
    if title_match and _BAD_TITLE.search(title_match.group(1)):
        if _NOT_FOUND_TITLE.search(title_match.group(1)):
            return False, "not_found"
        return False, "bad_title"

    body = _JINA_HEADER.sub("", text).strip()
    if len(body) < MIN_LENGTH:
        return False, "too_short"

    signals = count_job_signals(body)
    if signals < MIN_JOB_SIGNALS:
        if _find(lowered, _ERROR_PAGE):
            return False, "error_page"
        if _find(lowered, _CAPTCHA):
            return False, "captcha"
        if _find(lowered, _LOGIN):
            return False, "login_wall"
        if _find(lowered, _COOKIES):
            return False, "cookie_wall"
        # קודם עבר גם עם סימן אחד: LinkedIn החזיר רק "עבודות דומות" (בלי תיאור המשרה),
        # כלומר דף רשימה - וזה נשלח ל-AI כאילו היה המשרה
        return False, "no_job_content"

    return True, "ok"


def is_content_valid(text: str) -> bool:
    """
    Validates that scraped content is a job description and not an error,
    login, cookie-consent, bot-check or "job closed" page.
    """
    return validate_content(text)[0]


# הודעות למשתמש (מוצגות ב-UI ב-error_log) לפי סיבת הכישלון
FAILURE_MESSAGES = {
    "job_unavailable": "המשרה סגורה או אינה זמינה יותר",
    "not_found": "המשרה הוסרה או שהקישור שגוי (הדף לא נמצא)",
    "blocked": "האתר חסם את הסורק (הגנת בוטים / שגיאה) - אפשר להדביק את תיאור המשרה ידנית",
    "captcha": "האתר דורש אימות CAPTCHA - אפשר להדביק את תיאור המשרה ידנית",
    "login_wall": "האתר דורש התחברות כדי לראות את המשרה - אפשר להדביק את תיאור המשרה ידנית",
    "bad_title": "הסורק הגיע לדף התחברות או שגיאה במקום למשרה - אפשר להדביק ידנית",
    "error_page": "הקישור מוביל לדף שגיאה (לא נמצא / אין גישה)",
    "cookie_wall": "הסורק נתקע בהודעת cookies - אפשר להדביק את תיאור המשרה ידנית",
}
# הסדר קובע: תשובה "סופית" (המשרה סגורה / האתר החזיר 404-410) גוברת על חסימה של ניסיון
# אחר. למשל Drushim: Jina קיבל 410 (המשרה נמחקה) ו-Playwright קיבל CAPTCHA - ההודעה
# הנכונה היא "המשרה הוסרה", לא "הדבק ידנית".
_FAILURE_PRIORITY = (
    "job_unavailable",
    "not_found",
    "login_wall",
    "captcha",
    "blocked",
    "error_page",
    "bad_title",
    "cookie_wall",
)
DEFAULT_FAILURE_MESSAGE = "הסורק לא הצליח לחלץ תיאור משרה"


def failure_message(reasons) -> str:
    """בוחר את ההודעה הכי אינפורמטיבית מתוך הסיבות של כל הניסיונות (Jina, Playwright)."""
    reasons = [r for r in reasons if r]
    # האתר עצמו החזיר 404 / 410 (דרך Jina) = המשרה לא קיימת יותר
    reasons = ["not_found" if r in ("http_error_404", "http_error_410") else r for r in reasons]
    for key in _FAILURE_PRIORITY:
        if key in reasons:
            return FAILURE_MESSAGES[key]
    http = next((r for r in reasons if r.startswith("http_error_")), None)
    if http:
        return f"האתר החזיר שגיאה {http.rsplit('_', 1)[1]}"
    return DEFAULT_FAILURE_MESSAGE


def clean_text(text: str) -> str:
    """
    Cleans scraped text by removing URLs, images, and excessive newlines.
    DO NOT MODIFY - This regex logic works perfectly.

    Args:
        text: The raw scraped text

    Returns:
        Cleaned text
    """
    if not text:
        return ""
    # Remove top URL if present, images, and extra newlines
    text = re.sub(r"^>?\s*https?://[^\n]+\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
