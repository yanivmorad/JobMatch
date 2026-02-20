import logging
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

from scraper_service.utils import clean_text, is_content_valid

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
        self.api_key = os.getenv("JINA_API_KEY")

        # הגדרות Jina אגרסיביות יותר
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Timeout": "20",  # קיצור זמן ההמתנה של Jina
            "X-With-Iframe": "true",
            "X-With-Shadow-Dom": "true",
            "X-Target-Selector": "main, article, .job-description, #job-detail",  # עוזר ל-Jina להתמקד
        }

    def scrape(self, target_url: str, job_id: Optional[int] = None) -> Optional[dict]:
        id_tag = f"[ID {job_id}] " if job_id else ""
        start_time = time.time()

        # 1. ניסיון מהיר עם Jina AI (מקסימום 20 שניות)
        jina_result = self._try_jina(target_url, id_tag)
        if jina_result:
            return jina_result

        # בדיקה כמה זמן נשאר לנו (לפני שהוורקר הורג אותנו ב-60 שניות)
        elapsed = time.time() - start_time
        if elapsed > 45:
            logger.error(
                f"{id_tag}Scraper: Not enough time left for Playwright fallback"
            )
            return None

        # 2. Fallback ל-Playwright אם Jina נכשל
        if HAS_PLAYWRIGHT:
            logger.info(f"{id_tag}Scraper: Falling back to Local Playwright")
            content = self._scrape_with_playwright(target_url, job_id=job_id)
            if content and is_content_valid(content):
                return {
                    "source": "local_browser",
                    "full_description": clean_text(content),
                }

        return None

    def _try_jina(self, url: str, id_tag: str) -> Optional[dict]:
        jina_url = f"https://r.jina.ai/{url}"
        try:
            # שימוש ב-timeout קצר יותר ברמת ה-HTTP
            res = self.session.get(jina_url, headers=self.headers, timeout=25)
            if res.status_code == 200 and is_content_valid(res.text):
                logger.info(f"{id_tag}Scraper: Jina AI success")
                return {
                    "source": "jina",
                    "full_description": clean_text(res.text),
                }
        except Exception as e:
            logger.warning(f"{id_tag}Scraper: Jina fast attempt failed: {e}")
        return None

    def _scrape_with_playwright(
        self, url: str, job_id: Optional[int] = None
    ) -> Optional[str]:
        id_tag = f"[ID {job_id}] " if job_id else ""
        try:
            with sync_playwright() as p:
                # הרצה ב-Headless ועם User-Agent של דפדפן אמיתי
                browser = p.chromium.launch(headless=True)
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
                time.sleep(2)  # המתנה קטנה ל-JS

                content = md(page.content())
                browser.close()
                return content
        except Exception as e:
            logger.error(f"{id_tag}Scraper: Playwright fallback failed: {e}")
            return None
