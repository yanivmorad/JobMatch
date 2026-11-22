"""
הכנת תיאור המשרה לשליחה ל-AI: ניקוי רעש וחיתוך חכם, כדי לחסוך טוקנים (מכסת TPM בחינם).

טקסט סרוק כולל הרבה רעש: תפריטי ניווט, קישורים, באנר cookies, "משרות דומות".
דוגמאות מהבדיקה: AllJobs ~13K תווים כשהמשרה עצמה ~2K, BiScience 31K עם באנר Cookiebot.

    condense_description(text, max_chars) -> str

1. ניקוי: [טקסט](קישור) -> טקסט, בלי תמונות / URL-ים חשופים / שורות כותרת של Jina,
   בלי שורות ניווט קצרות שחוזרות, בלי שורות זהות כפולות.
2. אם עדיין ארוך מ-max_chars: שומרים את חלון הפסקאות הרצוף עם הכי הרבה "סימני משרה"
   (requirements / דרישות / ניסיון...) - כלומר את גוף המשרה, ולא את התפריט שלפניו.
"""
import re
from typing import List

from scraper_service.utils import count_job_signals

DEFAULT_MAX_CHARS = 8000

_JINA_META = re.compile(r"^(URL Source|Final URL|Published Time|Markdown Content|Warning):.*$", re.MULTILINE)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\((?:[^()]|\([^)]*\))*\)")
_BARE_URL = re.compile(r"https?://\S+")
_EMPTY_BULLET = re.compile(r"^\s*([*\-+•|]\s*)+$")
_SPACES = re.compile(r"[ \t ]+")
# באנר הסכמה ל-cookies: שורות שמתארות cookie, ושמות של cookies / פרמטרי מעקב (_clck, __ft_utm_term)
_COOKIE_LINE = re.compile(r"cookie|עוגיות|עוגיה", re.IGNORECASE)
# שורה ארוכה מזה היא לא באנר אלא פסקה (או כל הדף בשורה אחת, כמו ב-API של HireMeTech) -
# מורידים ממנה רק את המשפטים על cookies. באג (E2E): משרה של 4,200 תווים בשורה אחת הסתיימה
# ב"אתר זה משתמש ב... Cookie", כל השורה נמחקה, וה-AI קיבל רק כותרת וכישורים.
_COOKIE_LINE_MAX = 300
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
# markdown מוסיף escape: "mzb\_referrer", "visid\_incap\_\*"
_TRACKER_ID = re.compile(r"^(?:\\?[_*])*[A-Za-z0-9]+(?:(?:\\?[_*]|-|::)+[A-Za-z0-9]*)*$")
# הקשר שנשמר לפני סימן המשרה הראשון / אחרי האחרון בחלון (תיאור החברה, הטבות)
_CONTEXT_CHARS = 1500


def _drop_cookie_text(line: str) -> str:
    """
    שורה שמזכירה cookies: בלי סימני משרה = באנר (גם פסקה ארוכה של Cookiebot) -> "".
    עם תוכן משרה: שורה קצרה נשארת כמו שהיא ("We build cookie-less ad tracking. Requirements..."),
    ומשורה ארוכה יורדים רק המשפטים שמזכירים cookies.
    """
    if count_job_signals(line) < 2:
        return ""
    if len(line) <= _COOKIE_LINE_MAX:
        return line
    kept = [s for s in _SENTENCE_END.split(line) if not _COOKIE_LINE.search(s)]
    return " ".join(kept).strip()


def _clean(text: str) -> str:
    text = _JINA_META.sub("", text)
    text = _IMAGE.sub("", text)
    text = _LINK.sub(lambda m: m.group(1), text)
    text = _BARE_URL.sub("", text)

    lines, seen = [], set()
    for line in text.splitlines():
        line = _SPACES.sub(" ", line).strip()
        if not line or _EMPTY_BULLET.match(line):
            lines.append("")
            continue
        if "_" in line and _TRACKER_ID.match(line):
            continue
        if _COOKIE_LINE.search(line):
            line = _drop_cookie_text(line)
            if not line:
                continue
        key = line.lower()
        # שורה קצרה שכבר הופיעה = תפריט / כפתור שחוזר (שורות ארוכות זהות - גם הן כפילות)
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _best_window(lines: List[str], max_chars: int) -> str:
    """
    החלון הרציף של שורות (עד max_chars) עם הכי הרבה סימני משרה; בתיקו - המוקדם.
    two pointers: O(n). שורה בודדת ארוכה מהמגבלה נחתכת.
    """
    lines = [line[: max_chars - 1] for line in lines]  # -1: תו ירידת השורה
    sizes = [len(line) + 1 for line in lines]
    scores = [count_job_signals(line) for line in lines]
    best_score, best = -1, (0, 0)
    end, size, score = 0, 0, 0
    for start in range(len(lines)):
        while end < len(lines) and size + sizes[end] <= max_chars:
            size += sizes[end]
            score += scores[end]
            end += 1
        if score > best_score:
            best_score, best = score, (start, end)
        if end > start:
            size -= sizes[start]
            score -= scores[start]
        else:
            end = start + 1
    start, end = _trim_context(sizes, scores, *best)
    return "\n".join(lines[start:end]).strip()


def _trim_context(sizes: List[int], scores: List[int], start: int, end: int):
    """
    בחלון שנבחר: עד _CONTEXT_CHARS לפני השורה הראשונה עם סימן משרה ואחרי האחרונה.
    (בתיקו נבחר החלון המוקדם, שיכול להתחיל ברעש - תפריט / באנר - לפני גוף המשרה)
    """
    signal_lines = [i for i in range(start, end) if scores[i]]
    if not signal_lines:
        return start, end
    first, last = signal_lines[0], signal_lines[-1]
    new_start, budget = first, _CONTEXT_CHARS
    while new_start > start and budget - sizes[new_start - 1] >= 0:
        new_start -= 1
        budget -= sizes[new_start]
    new_end, budget = last + 1, _CONTEXT_CHARS
    while new_end < end and budget - sizes[new_end] >= 0:
        budget -= sizes[new_end]
        new_end += 1
    return new_start, new_end


def condense_description(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    if not text:
        return ""
    title = re.search(r"^Title:\s*(.+)$", text, re.MULTILINE)
    cleaned = _clean(re.sub(r"^Title:.*$", "", text, count=1, flags=re.MULTILINE))
    head = f"{title.group(1).strip()}\n\n" if title else ""

    budget = max(max_chars - len(head), 500)
    if len(cleaned) <= budget:
        return head + cleaned
    window = _best_window(cleaned.split("\n"), budget)
    return head + window + "\n\n[...התיאור קוצר...]"
