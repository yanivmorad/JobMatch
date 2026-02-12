import logging
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

from scraper_service.resolvers import URLResolver

# Import utility functions from the new modular structure
from scraper_service.utils import clean_text, is_content_valid

try:
    from markdownify import markdownify as md
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# הגדרת לוגים בסיסית שנראה מה קורה בטרמינל
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [SCRAPER] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


class Scraper:
    """
    Main scraper class that coordinates URL resolution and content scraping.
    Now uses modular components from scraper_service package.
    """

    def __init__(self):
        self.session = requests.Session()
        self.api_key = os.getenv("JINA_API_KEY")
        self.hireme_token = os.getenv("HIRE_ME_TECH_TOKEN")

        if not self.api_key:
            raise ValueError("❌ JINA_API_KEY missing!")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Timeout": "40",
            "X-With-Iframe": "true",
            "X-With-Shadow-Dom": "true",
        }

        # Initialize the URL resolver with tokens
        self.resolver = URLResolver(hireme_token=self.hireme_token)

    def _scrape_with_playwright(self, url: str) -> Optional[str]:
        """Backup local scraper if Jina fails"""
        if not HAS_PLAYWRIGHT:
            return None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=60000, wait_until="networkidle")
                content = md(page.content())
                browser.close()
                return content
        except Exception:
            return None

    def scrape(self, url: str, retries: int = 2) -> Optional[dict]:
        """
        The entry point. Detects if specific site handling is needed,
        resolves the real URL, and then scrapes the content.

        Args:
            url: The URL to scrape
            retries: Number of retry attempts for Jina scraping

        Returns:
            Dict with scraping results or None if failed:
            {
                "source": "jina" or "local_browser",
                "original_url": original input URL,
                "resolved_url": final URL that was scraped,
                "full_description": cleaned text content
            }
        """

        # --- STEP 1: RESOLVE (Special Handling) ---
        # Use the URLResolver to handle special sites like HireMeTech
        target_url = self.resolver.resolve(url)

        if target_url != url:
            logger.info(f"URL Resolved: {url} → {target_url}")

        # --- STEP 2: SCRAPE WITH JINA ---
        jina_url = f"https://r.jina.ai/{target_url}"
        logger.info(f"📡 Scraping via Jina: {target_url}")

        for attempt in range(retries):
            try:
                headers = self.headers.copy()
                if attempt > 0:
                    headers["X-No-Cache"] = "true"

                res = self.session.get(jina_url, headers=headers, timeout=40)
                if res.status_code == 200 and is_content_valid(res.text):
                    return {
                        "source": "jina",
                        "original_url": url,
                        "resolved_url": target_url,
                        "full_description": clean_text(res.text),
                    }
            except Exception as e:
                logger.warning(f"Jina attempt {attempt + 1} failed: {e}")
            time.sleep(1)

        # --- STEP 3: BACKUP SCRAPER (Local Playwright) ---
        logger.warning("🚨 Jina failed, falling back to local Playwright...")
        local_content = self._scrape_with_playwright(target_url)
        if local_content and is_content_valid(local_content):
            return {
                "source": "local_browser",
                "original_url": url,
                "resolved_url": target_url,
                "full_description": clean_text(local_content),
            }

        return None


if __name__ == "__main__":
    scraper = Scraper()
    # Test with HireMeTech link
    test_url = "https://hiremetech.com/job/106273229"
    res = scraper.scrape(test_url)

    if res:
        print("\n" + "=" * 40)
        print("✅ SCRAPE COMPLETE")
        print(f"Source: {res['source']}")
        print(f"Resolved URL: {res['resolved_url']}")
        print(f"Content Preview: {res['full_description'][:300]}...")
        print("=" * 40)
    else:
        print("\n🛑 SCRAPE FAILED")
