"""
חילוץ תיאור משרה מ-HTML גולמי (בלי Jina ובלי דפדפן).

למה: יש אתרים שמגישים את המשרה מוכנה ב-HTML (WordPress, אתרי קריירה של חברות), אבל
ה-Reader של Jina "מסכם" אותם ומפיל חלקים. MazeBolt: ב-HTML יש את כל התיאור, ו-Jina החזיר
1,840 תווים בלי הדרישות - הבדיקה פסלה אותם (no_job_content) והמשרה סומנה "אין מידע".
בשרת החינמי אין דפדפן, אז זה הגיבוי היחיד לאתרים כאלה.

    html_to_document(html, url) -> str   # בפורמט של Jina: "Title: ...\n\nURL Source: ...\n\nMarkdown Content:\n..."
"""
import re
from typing import Optional

from bs4 import BeautifulSoup
from markdownify import markdownify

# תגיות שאף פעם לא חלק מתיאור המשרה. לא <form> (ב-ASP.NET כל הדף בתוך form) ולא <header>
# (בהרבה אתרים כותרת המשרה והמיקום בתוך <header> של ה-article)
_DROP_TAGS = ("script", "style", "noscript", "template", "svg", "iframe", "footer", "nav", "aside", "button")
# סדר העדיפות לבחירת האזור הראשי של הדף
_CONTENT_SELECTORS = (
    "main",
    "article",
    "[role=main]",
    ".job-description",
    "#job-detail",
    "#content",
)
# אזור קטן מזה כנראה לא התיאור (למשל <main> שיש בו רק כותרת) - לוקחים את כל ה-body
_MIN_CONTENT_CHARS = 500


def _title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and (og.get("content") or "").strip():
        return og["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(" ", strip=True) if h1 else ""


def _content_node(soup: BeautifulSoup):
    for selector in _CONTENT_SELECTORS:
        node = soup.select_one(selector)
        if node and len(node.get_text(" ", strip=True)) >= _MIN_CONTENT_CHARS:
            return node
    return soup.body or soup


def html_to_document(html: str, url: str, final_url: Optional[str] = None) -> str:
    """final_url: לאן הגענו אחרי הפניות - כדי ש-validate_content יזהה הפניה לרשימת המשרות."""
    soup = BeautifulSoup(html or "", "html.parser")
    title = _title(soup)
    for tag in soup(_DROP_TAGS):
        tag.decompose()
    node = _content_node(soup)
    markdown = markdownify(str(node), heading_style="ATX")
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    header = f"Title: {title}\n\nURL Source: {url}\n"
    if final_url and final_url.rstrip("/?") != url.rstrip("/?"):
        header += f"Final URL: {final_url}\n"
    return f"{header}\nMarkdown Content:\n{markdown}"
