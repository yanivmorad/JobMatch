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
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
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
    # url -> כותרת המשרה כפי שכתובה בהודעה (רק כשזוהתה בביטחון סביר)
    titles: Dict[str, str] = field(default_factory=dict)


# --- זיהוי כותרת המשרה מתוך ההודעה ---

# תחילת הודעה בהעתקה מוואטסאפ: "[22.11, 7:43] שם: " או בייצוא אנדרואיד "22/11/2026, 07:43 - שם: "
_CHAT_PREFIX = re.compile(
    r"^(?:\[[^\]\n]{1,40}\]\s*|\d{1,2}[./]\d{1,2}[./]\d{2,4},?\s+\d{1,2}:\d{2}(?:\s?[AaPp][Mm])?\s+-\s+)"
    r"[^:\n]{1,60}:[ \t]?",
    re.MULTILINE,
)
# תוויות שמסמנות במפורש שם משרה ("*שם המשרה:* X")
_TITLE_LABEL = re.compile(
    r"^(?:שם\s*ה?משרה|שם\s*ה?תפקיד|תפקיד|משרה|position|job\s*title|role|title)\s*[:\-–]\s*",
    re.IGNORECASE,
)
# תווי כיווניות שוואטסאפ מוסיף סביב שמות ומספרי טלפון
_BIDI = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def _clean_line(line: str) -> str:
    line = _BIDI.sub("", line)
    line = re.sub(r"[*_~`]", "", line)  # הדגשות של וואטסאפ / markdown
    return line.strip().rstrip("-–—|").strip()


# --- פתיח של הודעת גיוס לפני שם המשרה ---
# באג (ריצה אמיתית): "🔥 דרוש/ה Junior QA Automation Engineer" נשמר כשם המשרה כמו שהוא.
# אימוג'י וסימני רשימה בתחילת / סוף השורה: So = אימוג'י וסמלים, Sk = גוון עור,
# Cf = ZWJ ותווי כיווניות, Me / Mn = keycap ו-variation selectors (רק בתחילת השורה:
# בסוף שורה Mn יכול להיות ניקוד עברי). "." ו-"(" לא נמחקים: ".NET Developer", "(Junior) QA".
_LEADING_PUNCT = set("•·▪▫◦‣⁃*-–—>|:!¡#~=")
_TRAILING_MARKS = {"\ufe0f", "\ufe0e", "\u20e3"}


def _is_leading_decor(ch: str) -> bool:
    return ch.isspace() or ch in _LEADING_PUNCT or unicodedata.category(ch) in ("So", "Sk", "Cf", "Me", "Mn")


def _is_trailing_decor(ch: str) -> bool:
    return ch.isspace() or ch in _TRAILING_MARKS or unicodedata.category(ch) in ("So", "Sk", "Cf", "Me")


# מספור בסגנון keycap: "1️⃣ Backend" (ספרה + FE0F + 20E3 - הספרה עצמה היא לא קישוט)
_KEYCAP = re.compile(r"^[0-9#*]️?⃣")


def _strip_decor(line: str) -> str:
    while True:
        start, end = 0, len(line)
        while start < end and _is_leading_decor(line[start]):
            start += 1
        while end > start and _is_trailing_decor(line[end - 1]):
            end -= 1
        stripped = _KEYCAP.sub("", line[start:end])
        if stripped == line:
            return line
        line = stripped


_SEP = r"[\s:\-–—!,|.]"
# מילות גיוס בתחילת השורה (לפני שם המשרה):
#   דרוש / דרושה / דרושים / דרושות / דרוש/ה / דרושים/ות / דרוש.ה
#   מחפש/ת / מחפשים / מחפשות / אנחנו מחפשים/ות, מגייסים / מגייסות (ברבים בלבד: "מגייס/ת" הוא שם תפקיד)
#   משרה חדשה / חמה / פתוחה, משרות חדשות
#   We're hiring / We are hiring / Now hiring (גם בלי סימן), "Hiring:" / "Job alert:" (רק עם סימן:
#   "Hiring Manager" הוא שם תפקיד)
_RECRUIT_PREFIX = re.compile(
    r"^(?:"
    r"(?:אנחנו\s+)?(?:דרוש|מחפש)(?:ים|ות|ת|ה)?(?:\s*[/\\.]\s*(?:ות|ים|ה|ת))?"
    r"|(?:אנחנו\s+)?מגייס(?:ים|ות)(?:\s*/\s*(?:ות|ים))?"
    r"|משר(?:ה|ות)\s+(?:חדש|חמ|פתוח)(?:ה|ות)"
    rf")(?=$|{_SEP})"
    rf"|^(?:we['’]?re|we\s+are|now)\s+hiring(?=$|{_SEP})"
    r"|^(?:hiring|job\s+alert|new\s+job|open\s+position)\s*(?=[:\-–—!|])",
    re.IGNORECASE,
)
# "לחברת הייטק מובילה דרוש/ה QA Engineer" - שם המשרה אחרי "דרוש" באמצע השורה
_RECRUIT_INFIX = re.compile(r"\sדרוש(?:ים|ות|ה)?(?:\s*/\s*(?:ות|ה))?\s*:?\s+(?=\S)")


# מה שנשאר אחרי פתיח כמו "משרות חמות להיום" / "משרות חדשות השבוע!": זו כותרת של הודעה, לא שם משרה
_TIME_WORDS = re.compile(
    r"^(?:ל?היום|ל?השבוע|ל?שבוע\s+הזה|ל?סופ\"?ש|today|this\s+week)[\s!.:\-–—]*$", re.IGNORECASE
)
# תווית שמובילה לקישור ("לפרטים והגשה:", "לינק להגשה:", "Apply here:") - לא שם משרה
_APPLY_LABEL = re.compile(
    r"^(?:ל?פרטים|ל?הגשה|ל?הגשת|לינק|קישור|לקישור|apply|link|details|more\s+info)\b"
    r"|(?:הגשה|להגשה|apply|link)\s*(?:here|כאן)?\s*$",
    re.IGNORECASE,
)


def _strip_recruit_prefix(line: str) -> Tuple[str, bool]:
    """
    מוריד אימוג'י ופתיחים ("🔥 דרוש/ה", "משרה חדשה!", "We're hiring:") מתחילת השורה.
    מחזיר (השורה הנקייה, האם הורד פתיח). שורה שהייתה רק פתיח ("🔥 דרושים! 🔥") -> ("", True).
    """
    line = _strip_decor(line)
    removed = False
    for _ in range(3):  # "🔥 משרה חדשה! דרוש/ה: QA" - כמה פתיחים ברצף
        m = _RECRUIT_PREFIX.match(line)
        if not m:
            break
        line = _strip_decor(re.sub(rf"^{_SEP}+", "", line[m.end():]))
        removed = True
    if removed and _TIME_WORDS.match(line):
        return "", True
    if not removed:
        infix = _RECRUIT_INFIX.search(line)
        if infix:
            rest = _strip_decor(line[infix.end():])
            if _valid_title(rest):
                return rest, True
    return line, removed


def _valid_title(line: str) -> Optional[str]:
    if not line or line.endswith(":") or _URL_RE.search(line):
        return None
    if not 2 <= len(line) <= 120 or not re.search(r"[^\W\d_]", line):
        return None
    return line


def _title_from(region: str, first_line_wins: bool) -> Optional[str]:
    """
    בוחר כותרת מתוך הטקסט שלפני הקישור:
    1. שורה עם תווית ("שם המשרה: X") - הכי אמינה.
    2. הודעה עם קישור משרה יחיד - השורה הראשונה של ההודעה (שם המשרה בדרך כלל בראש).
       שורת פתיח בלבד ("🔥 דרושים!") או שורת קישוט בלי אותיות - מדלגים לשורה הבאה.
    3. אחרת - השורה הקרובה ביותר לפני הקישור, בדילוג על תוויות ריקות ("לינק להגשה:").
    בכל המקרים מורידים מהכותרת אימוג'י ופתיח גיוס ("🔥 דרוש/ה Junior QA" -> "Junior QA").
    """
    lines = [_clean_line(l) for l in region.splitlines()]
    lines = [l for l in lines if l]

    for line in reversed(lines):
        labeled = _TITLE_LABEL.match(_strip_decor(line))
        if labeled:
            value, _ = _strip_recruit_prefix(_strip_decor(line)[labeled.end():])
            title = _valid_title(value)
            if title:
                return title

    ordered = lines if first_line_wins else list(reversed(lines))
    for n, line in enumerate(ordered):
        cleaned, had_prefix = _strip_recruit_prefix(line)
        title = _valid_title(cleaned)
        if not title and not first_line_wins and n == 0 and cleaned.endswith(":"):
            # השורה הצמודה לקישור: "אנליסט/ית לצוות חדש, היברידי:" - שם המשרה עם נקודתיים.
            # תווית הגשה ("לפרטים והגשה:") ממשיכה להיפסל, והחיפוש עולה לשורה שמעליה.
            stem = cleaned.rstrip(":").strip()
            if not _APPLY_LABEL.search(stem):
                title = _valid_title(stem)
        if title:
            return title
        if first_line_wins:
            decorative = not re.search(r"[^\W\d_]", line)  # "🔥🔥🔥" / "-----"
            if (had_prefix and not cleaned) or decorative:
                continue
            return None  # השורה הראשונה לא נראית ככותרת - לא מנחשים
    return None


def _extract_titles(text: str, matches: List[tuple]) -> Dict[int, str]:
    """
    matches: [(start, end, is_job)] לכל קישור בטקסט.
    מחזיר {אינדקס של קישור משרה: כותרת}.
    """
    # גבולות ההודעות (אם זה טקסט מוואטסאפ); אחרת כל הטקסט הוא "הודעה" אחת
    starts = [m.start() for m in _CHAT_PREFIX.finditer(text)]
    is_chat = bool(starts)
    bounds = (starts or [0]) + [len(text)]
    messages = list(zip(bounds[:-1], bounds[1:]))
    if starts and starts[0] > 0:
        messages.insert(0, (0, starts[0]))

    titles = {}
    for msg_start, msg_end in messages:
        in_msg = [(i, m) for i, m in enumerate(matches) if msg_start <= m[0] < msg_end]
        job_links = [(i, m) for i, m in in_msg if m[2]]
        body_start = msg_start
        prefix = _CHAT_PREFIX.match(text, msg_start)
        if prefix:
            body_start = prefix.end()
        single = is_chat and len(job_links) == 1

        for i, (start, _end, is_job) in in_msg:
            if not is_job:
                continue
            if single:
                region_start = body_start
            else:
                prev_ends = [m[1] for _, m in in_msg if m[1] <= start]
                region_start = max([body_start] + prev_ends)
            title = _title_from(text[region_start:start], first_line_wins=single)
            if title:
                titles[i] = title
    return titles


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
    """
    כל קישורי המשרות בטקסט, מנורמלים, בלי כפילויות, לפי סדר ההופעה.
    בנוסף: titles - הכותרת שכתובה בהודעה לכל קישור משרה (כשאפשר לזהות אותה).
    """
    text = text or ""
    result = ExtractedLinks()
    found = []  # (start, end, url, reason)
    for match in _URL_RE.finditer(text):
        raw = _trim(match.group(0))
        if not raw:
            continue
        url = normalize_job_url(raw)
        found.append((match.start(), match.start() + len(raw), url, ignore_reason(url)))

    titles = _extract_titles(text, [(s, e, reason is None) for s, e, _u, reason in found])

    seen = set()
    for i, (_s, _e, url, reason) in enumerate(found):
        if url in seen:
            continue
        seen.add(url)
        if reason:
            result.ignored.append({"url": url, "reason": reason})
        else:
            result.jobs.append(url)
            if i in titles:
                result.titles[url] = titles[i]
    return result
