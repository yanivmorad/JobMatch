import logging
import os
import time
from typing import List, Optional

import requests
from dotenv import load_dotenv

from scraper_service.utils import clean_text, validate_content

# ניסיון ייבוא שקט של Playwright
try:
    from markdownify import markdownify as md
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

load_dotenv()
logger = logging.getLogger(__name__)


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
        מנסה Jina ואז Playwright. מחזיר {"source", "full_description"} או None.
        trace (אופציונלי): רשימה שאליה נוסף תיעוד של כל ניסיון
        {method, status, length, valid, reason, seconds} - לדיבאג ולהודעות שגיאה ב-UI.
        """
        id_tag = f"[ID {job_id}] " if job_id else ""
        trace = trace if trace is not None else []
        start_time = time.time()

        # 1. ניסיון מהיר עם Jina AI (מקסימום 20 שניות)
        jina_result = self._try_jina(target_url, id_tag, trace)
        if jina_result:
            return jina_result

        # בדיקה כמה זמן נשאר לנו (לפני שהוורקר הורג אותנו ב-60 שניות)
        elapsed = time.time() - start_time
        if elapsed > 45:
            logger.error(
                f"{id_tag}Scraper: Not enough time left for Playwright fallback"
            )
            trace.append({"method": "playwright", "valid": False, "reason": "no_time_left"})
            return None

        # 2. Fallback ל-Playwright אם Jina נכשל
        if HAS_PLAYWRIGHT:
            logger.info(f"{id_tag}Scraper: Falling back to Local Playwright")
            t0 = time.time()
            content = self._scrape_with_playwright(target_url, job_id=job_id)
            valid, reason = validate_content(content) if content else (False, "fetch_failed")
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

    def _try_jina(self, url: str, id_tag: str, trace: List[dict]) -> Optional[dict]:
        result = self._jina_request(url, id_tag, trace, self.headers)
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
                valid, reason = validate_content(res.text)
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
                    page.wait_for_timeout(2000)  # המתנה קטנה ל-JS

                    # שורת Title בפורמט של Jina, כדי ש-validate_content יבדוק גם את הכותרת
                    return f"Title: {page.title()}\n\n" + md(page.content())
                finally:
                    # נסגר תמיד, גם בשגיאה / timeout
                    browser.close()
        except Exception as e:
            logger.error(f"{id_tag}Scraper: Playwright fallback failed: {e}")
            return None
