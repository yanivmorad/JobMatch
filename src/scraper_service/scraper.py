# src/scraper_service/scraper.py (גרסה מעודכנת ונקייה)

import logging
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

from scraper_service.utils import clean_text, is_content_valid

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
        if not self.api_key:
            raise ValueError("❌ JINA_API_KEY missing!")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Timeout": "40",
            "X-With-Iframe": "true",
            "X-With-Shadow-Dom": "true",
        }

    def scrape(self, target_url: str, job_id: Optional[int] = None) -> Optional[dict]:
        """סורק את התוכן מה-URL המוגמר."""
        id_tag = f"[ID {job_id}] " if job_id else ""
        logger.info(f"{id_tag}Scraper: Starting scrape flow for {target_url}")
        return self._execute_scraping_flow(target_url, job_id=job_id)

    def _execute_scraping_flow(
        self, target_url: str, retries: int = 2, job_id: Optional[int] = None
    ) -> Optional[dict]:
        id_tag = f"[ID {job_id}] " if job_id else ""
        # ניסיון סריקה עם Jina AI
        jina_url = f"https://r.jina.ai/{target_url}"

        for attempt in range(retries):
            try:
                logger.info(
                    f"{id_tag}Scraper: Attempting Jina AI (Attempt {attempt + 1}) for {target_url}"
                )
                headers = self.headers.copy()
                if attempt > 0:
                    headers["X-No-Cache"] = "true"

                res = self.session.get(jina_url, headers=headers, timeout=40)
                if res.status_code == 200 and is_content_valid(res.text):
                    logger.info(f"{id_tag}Scraper: Jina AI success for {target_url}")
                    return {
                        "source": "jina",
                        "full_description": clean_text(res.text),
                    }
                else:
                    logger.warning(
                        f"{id_tag}Scraper: Jina AI returned status {res.status_code} or invalid content for {target_url}"
                    )
            except Exception as e:
                logger.warning(
                    f"{id_tag}Scraper: Jina attempt {attempt + 1} failed for {target_url}: {e}"
                )

            if attempt < retries - 1:
                time.sleep(2)

        # Fallback ל-Playwright
        if HAS_PLAYWRIGHT:
            logger.info(f"{id_tag}Scraper: Falling back to Playwright for {target_url}")
            content = self._scrape_with_playwright(target_url, job_id=job_id)
            if content and is_content_valid(content):
                logger.info(f"{id_tag}Scraper: Playwright success for {target_url}")
                return {
                    "source": "local_browser",
                    "full_description": clean_text(content),
                }
            else:
                logger.warning(
                    f"{id_tag}Scraper: Playwright failed to extract valid content for {target_url}"
                )

        return None

    def _scrape_with_playwright(
        self, url: str, job_id: Optional[int] = None
    ) -> Optional[str]:
        id_tag = f"[ID {job_id}] " if job_id else ""
        try:
            with sync_playwright() as p:
                logger.debug(
                    f"{id_tag}Scraper: Initializing Playwright browser for {url}"
                )
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=60000, wait_until="networkidle")
                content = md(page.content())
                browser.close()
                return content
        except Exception as e:
            logger.error(f"{id_tag}Scraper: Playwright error for {url}: {e}")
            return None
