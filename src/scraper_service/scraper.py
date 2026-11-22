import logging
import os
import re
import time
from typing import List, Optional
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from scraper_service.hiremetech import is_hiremetech
from scraper_service.html_extract import html_to_document
from scraper_service.site_apis import fetch_from_site_api
from scraper_service.utils import clean_text, playwright_allowed, validate_content

# ניסיון ייבוא שקט של Playwright
try:
    from markdownify import markdownify as md
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

load_dotenv()
logger = logging.getLogger(__name__)

# selector ייעודי לאתרים שבהם ה-selector הכללי תופס את החלק הלא נכון.
# LinkedIn: "main" הכיל רק "עבודות דומות", וגם הדף המלא דרך Jina היה בלי תיאור המשרה.
SITE_SELECTORS = {
    "linkedin.com": ".top-card-layout, .description__text, .show-more-less-html__markup",
}
_HIREMETECH_TITLE_SUFFIX = re.compile(r"\s+at\s+Company\s*\|\s*HireMe\b", re.IGNORECASE)

# האתר כבר ענה שהמשרה לא קיימת - אין טעם להוריד את הדף שוב
_FINAL_REASONS = ("job_unavailable", "not_found", "http_error_404", "http_error_410", "no_description")
# תשובות של API שאין אחריהן טעם לנסות סורק אחר
_FINAL_API_REASONS = ("job_unavailable", "hiremetech_no_description")
DIRECT_TIMEOUT_SECONDS = 12
_DIRECT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
}


class Scraper:
    def __init__(self):
        self.session = requests.Session()
        self.api_key = (os.getenv("JINA_API_KEY") or "").strip()

        # הגדרות Jina אגרסיביות יותר
        self.headers = {
            "X-Timeout": "20",  # קיצור זמן ההמתנה של Jina
            "X-With-Iframe": "true",
            "X-With-Shadow-Dom": "true",
            "X-Target-Selector": "main, article, .job-description, #job-detail",  # עוזר ל-Jina להתמקד
        }
        # בלי מפתח נשלחה הכותרת "Bearer None"
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def scrape(
        self,
        target_url: str,
        job_id: Optional[int] = None,
        trace: Optional[List[dict]] = None,
    ) -> Optional[dict]:
        """
        API של מערכת הגיוס -> Jina -> ה-HTML הישיר -> Playwright.
        מחזיר {"source", "full_description"} (ולפעמים company / job_title) או None.
        trace (אופציונלי): רשימה שאליה נוסף תיעוד של כל ניסיון
        {method, status, length, valid, reason, seconds} - לדיבאג ולהודעות שגיאה ב-UI.
        """
        id_tag = f"[ID {job_id}] " if job_id else ""
        trace = trace if trace is not None else []
        start_time = time.time()

        result = self._scrape(target_url, job_id, id_tag, trace, start_time)
        if result and is_hiremetech(target_url):
            # הדף הציבורי: "RPA Developer at Company | HireMe" - ה-AI לקח את "Company | HireMe"
            # כשם החברה. מורידים את החלק הזה מהכותרת ומציינים שהחברה מוסתרת.
            result["full_description"] = _HIREMETECH_TITLE_SUFFIX.sub(
                " (שם החברה מוסתר בדף הציבורי של HireMeTech)", result["full_description"], count=1
            )
        return result

    def _scrape(
        self, target_url: str, job_id: Optional[int], id_tag: str, trace: List[dict], start_time: float
    ) -> Optional[dict]:
        # 0. API ציבורי של מערכת הגיוס (Workday / BambooHR): דפי SPA ש-Jina מקבל מהם שלד ריק
        api_result = self._try_site_api(target_url, id_tag, trace)
        if api_result is not None:
            return api_result or None  # {} = המשרה סגורה (תשובה סופית, אין טעם לנסות סורק אחר)

        # 1. ניסיון מהיר עם Jina AI (מקסימום 20 שניות)
        jina_result = self._try_jina(target_url, id_tag, trace)
        if jina_result:
            return jina_result

        # 2. ה-HTML עצמו, בלי Jina ובלי דפדפן: דפים שמגיעים מוכנים מהשרת ו-Jina חתך
        # (MazeBolt). מדלגים כשהאתר כבר ענה שהמשרה לא קיימת.
        if not any(a.get("reason") in _FINAL_REASONS for a in trace):
            direct = self._try_direct_html(target_url, id_tag, trace)
            if direct:
                return direct

        # בדיקה כמה זמן נשאר (ה-worker עוצר את הסריקה אחרי SCRAPE_TIMEOUT_SECONDS=90;
        # Playwright לוקח עד ~45 שניות: טעינה 30 + המתנה לתוכן עד 14)
        elapsed = time.time() - start_time
        if elapsed > 40:
            logger.error(
                f"{id_tag}Scraper: Not enough time left for Playwright fallback"
            )
            trace.append({"method": "playwright", "valid": False, "reason": "no_time_left"})
            return None

        # 3. Fallback ל-Playwright אם Jina נכשל
        if HAS_PLAYWRIGHT and playwright_allowed():
            logger.info(f"{id_tag}Scraper: Falling back to Local Playwright")
            t0 = time.time()
            content = self._scrape_with_playwright(target_url, job_id=job_id)
            valid, reason = (
                validate_content(content, target_url) if content else (False, "fetch_failed")
            )
            trace.append(
                {
                    "method": "playwright",
                    "status": None,
                    "length": len(content or ""),
                    "valid": valid,
                    "reason": reason,
                    "seconds": round(time.time() - t0, 1),
                }
            )
            if valid:
                return {
                    "source": "local_browser",
                    "full_description": clean_text(content),
                }
            logger.warning(f"{id_tag}Scraper: Playwright content rejected ({reason})")

        return None

    def _try_site_api(self, url: str, id_tag: str, trace: List[dict]) -> Optional[dict]:
        """
        None = האתר לא נתמך / ה-API נכשל -> ממשיכים ל-Jina.
        {}   = ה-API אומר שהמשרה סגורה / שאין לה תיאור (תשובה סופית).
        dict = תוצאה תקינה (כולל company / job_title מה-API).
        """
        t0 = time.time()
        result = fetch_from_site_api(url, self.session)
        if result is None:
            return None
        entry = {
            "method": result.method,
            "status": result.status,
            "length": len(result.text or ""),
            "valid": False,
            "reason": result.reason,
        }
        try:
            if result.reason in _FINAL_API_REASONS:
                return {}
            if result.reason == "ok":
                valid, reason = validate_content(result.text, url)
                entry.update(valid=valid, reason=reason)
                if valid:
                    logger.info(f"{id_tag}Scraper: {result.method} success")
                    return {
                        "source": result.method,
                        "full_description": clean_text(result.text),
                        "company": result.company,
                        "job_title": result.job_title,
                    }
            logger.info(f"{id_tag}Scraper: {result.method} not usable ({entry['reason']})")
            return None
        finally:
            entry["seconds"] = round(time.time() - t0, 1)
            trace.append(entry)

    def _try_direct_html(self, url: str, id_tag: str, trace: List[dict]) -> Optional[dict]:
        """
        GET רגיל לדף והמרה ל-markdown. כישלון "רך" (דף SPA ריק, חסימת בוטים) מסומן
        direct_<reason> - הוא לא מכריע ש"אין מידע", כי ייתכן שהתוכן נטען רק ב-JavaScript.
        """
        t0 = time.time()
        entry = {"method": "direct_html", "status": None, "length": 0, "valid": False, "reason": None}
        try:
            res = self.session.get(url, headers=_DIRECT_HEADERS, timeout=DIRECT_TIMEOUT_SECONDS)
            entry["status"] = res.status_code
            if res.status_code in (404, 410):
                entry["reason"] = f"http_error_{res.status_code}"
                return None
            if res.status_code != 200:
                entry["reason"] = f"direct_http_{res.status_code}"
                return None
            content_type = ((getattr(res, "headers", None) or {}).get("content-type") or "").lower()
            if content_type and "html" not in content_type:
                entry["reason"] = "direct_not_html"
                return None
            text = html_to_document(res.text, url, final_url=getattr(res, "url", None))
            entry["length"] = len(text)
            valid, reason = validate_content(text, url)
            if valid:
                entry.update(valid=True, reason="ok")
                logger.info(f"{id_tag}Scraper: direct HTML success")
                return {"source": "direct_html", "full_description": clean_text(text)}
            entry["reason"] = reason if reason in ("job_unavailable", "not_found") else f"direct_{reason}"
            logger.info(f"{id_tag}Scraper: direct HTML rejected ({reason})")
            return None
        except Exception as e:
            entry["reason"] = f"direct_error: {type(e).__name__}"
            logger.info(f"{id_tag}Scraper: direct HTML failed: {e}")
            return None
        finally:
            entry["seconds"] = round(time.time() - t0, 1)
            trace.append(entry)

    def _headers_for(self, url: str) -> dict:
        host = (urlparse(url).hostname or "").lower()
        for domain, selector in SITE_SELECTORS.items():
            if host == domain or host.endswith("." + domain):
                return {**self.headers, "X-Target-Selector": selector}
        return self.headers

    def _try_jina(self, url: str, id_tag: str, trace: List[dict]) -> Optional[dict]:
        result = self._jina_request(url, id_tag, trace, self._headers_for(url))
        if result is None and trace and trace[-1].get("reason") == "jina_selector_miss":
            # Jina מחזיר 422 כשאף אחד מה-selectors לא קיים בדף (למשל Lever) -
            # מנסים שוב את כל הדף לפני שעוברים ל-Playwright
            headers = {k: v for k, v in self.headers.items() if k != "X-Target-Selector"}
            result = self._jina_request(url, id_tag, trace, headers, method="jina_full_page")
        return result

    def _jina_request(
        self, url: str, id_tag: str, trace: List[dict], headers: dict, method: str = "jina"
    ) -> Optional[dict]:
        jina_url = f"https://r.jina.ai/{url}"
        t0 = time.time()
        entry = {"method": method, "status": None, "length": 0, "valid": False}
        try:
            # שימוש ב-timeout קצר יותר ברמת ה-HTTP
            res = self.session.get(jina_url, headers=headers, timeout=25)
            entry["status"] = res.status_code
            entry["length"] = len(res.text or "")
            if res.status_code == 200:
                valid, reason = validate_content(res.text, url)
            elif res.status_code == 422 and "target selector" in (res.text or ""):
                valid, reason = False, "jina_selector_miss"
            else:
                valid, reason = False, f"jina_http_{res.status_code}"
            entry.update(valid=valid, reason=reason)
            if valid:
                logger.info(f"{id_tag}Scraper: Jina AI success ({method})")
                return {
                    "source": "jina",
                    "full_description": clean_text(res.text),
                }
            logger.info(f"{id_tag}Scraper: Jina content rejected ({reason})")
        except Exception as e:
            entry["reason"] = f"jina_error: {type(e).__name__}"
            logger.warning(f"{id_tag}Scraper: Jina fast attempt failed: {e}")
        finally:
            entry["seconds"] = round(time.time() - t0, 1)
            trace.append(entry)
        return None

    # מספיק טקסט כדי שזה כנראה כבר תיאור משרה ולא שלד של SPA
    CONTENT_READY_CHARS = 1000

    @classmethod
    def _wait_for_content(cls, page, network_idle_ms: int = 8000, content_ms: int = 6000) -> None:
        """
        דפי SPA (Workday, BambooHR...) מרנדרים את המשרה רק אחרי קריאות API.
        קודם: המתנה קבועה של 2 שניות, ואז חזר שלד ריק (9 / 25 תווים).
        עכשיו: עד network idle, ואז עד שיש בדף מספיק טקסט - כל שלב עם תקרה, ובלי לזרוק.
        """
        try:
            page.wait_for_load_state("networkidle", timeout=network_idle_ms)
        except Exception:
            pass  # אתרים עם polling / analytics אף פעם לא מגיעים ל-networkidle
        try:
            page.wait_for_function(
                f"() => document.body && document.body.innerText.length > {cls.CONTENT_READY_CHARS}",
                timeout=content_ms,
            )
        except Exception:
            pass  # דף קצר באמת - validate_content יחליט

    def _scrape_with_playwright(
        self, url: str, job_id: Optional[int] = None
    ) -> Optional[str]:
        id_tag = f"[ID {job_id}] " if job_id else ""
        try:
            with sync_playwright() as p:
                # הרצה ב-Headless ועם User-Agent של דפדפן אמיתי
                browser = p.chromium.launch(headless=True)
                try:
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                    )
                    page = context.new_page()

                    # חסימת משאבים כבדים לטעינה מהירה
                    page.route(
                        "**/*",
                        lambda route: (
                            route.abort()
                            if route.request.resource_type in ["image", "media", "font"]
                            else route.continue_()
                        ),
                    )

                    # ניסיון טעינה (30 שניות גג)
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    self._wait_for_content(page)

                    # שורות Title / Final URL בפורמט של Jina, כדי ש-validate_content
                    # יבדוק גם את הכותרת וגם הפניה לרשימת המשרות (משרה שהוסרה)
                    header = f"Title: {page.title()}\n"
                    if page.url.rstrip("/?") != url.rstrip("/?"):
                        header += f"Final URL: {page.url}\n"
                    return header + "\n" + md(page.content())
                finally:
                    # נסגר תמיד, גם בשגיאה / timeout
                    browser.close()
        except Exception as e:
            logger.error(f"{id_tag}Scraper: Playwright fallback failed: {e}")
            return None
