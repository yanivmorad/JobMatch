# src/scraper_service/resolvers.py
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# טעינת משתני סביבה מהקובץ .env
load_dotenv()

logger = logging.getLogger(__name__)


HAS_PLAYWRIGHT = True


class URLResolver:
    """
    Resolves special job site URLs that require authentication or redirection.
    Currently supports HireMeTech.
    """

    def __init__(self, hireme_token: Optional[str] = None):
        """
        Initialize the resolver with authentication tokens.
        If no token is provided, it attempts to fetch from HIRE_ME_TECH_TOKEN env var.
        """
        # אם לא התקבל טוקן, נסה למשוך מה-env
        self.hireme_token = hireme_token or os.getenv("HIRE_ME_TECH_TOKEN")

    def resolve(self, url: str) -> str:
        """
        Resolves a URL to its final destination.
        """
        if "hiremetech.com" in url:
            return self._resolve_hiremetech(url)

        return url

    def _resolve_hiremetech(self, url: str) -> str:
        """
        Resolves HireMeTech job URLs to actual company URLs.
        Matches the logic of the successful standalone script.
        """
        if not HAS_PLAYWRIGHT:
            logger.warning("Playwright is not installed!")
            return url

        if not self.hireme_token:
            logger.warning("HIRE_ME_TECH_TOKEN not set in environment or constructor!")
            return url

        logger.info(f"INIT: Starting VIP resolution for HireMeTech: {url}")

        try:
            with sync_playwright() as p:
                # שינוי ל-headless=False כדי שתוכל לראות את התהליך במידת הצורך
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                )
                page = context.new_page()

                # 1. Access the job page
                logger.info(f"Navigating to: {url}")
                page.goto(url, wait_until="domcontentloaded")

                # 2. Inject token into local storage
                page.evaluate(
                    f"window.localStorage.setItem('auth_token', '{self.hireme_token}');"
                )

                # 3. Reload and wait for session to apply
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(4000)

                # 4. Smart Button Detection
                apply_button = None
                for text in ["הגש מועמדות", "Apply Now"]:
                    btn = page.get_by_role("button", name=text, exact=False)
                    if btn.is_visible():
                        apply_button = btn
                        logger.info(f"MATCH: Found button with text '{text}'")
                        break

                if not apply_button:
                    # Fallback to CSS
                    apply_button = page.locator("button.bg-gradient-to-r").first

                if not apply_button or not apply_button.is_visible():
                    logger.error(
                        "STEP FAILED: Could not find visible Apply button. Taking screenshot."
                    )
                    page.screenshot(path="debug_missing_button.png")
                    browser.close()
                    return url

                # 5. Execute Click and Capture Final URL
                final_url = url
                try:
                    logger.info("Clicking apply button...")
                    with context.expect_page(timeout=10000) as new_page_info:
                        apply_button.click(force=True, delay=300)

                    new_page = new_page_info.value
                    new_page.wait_for_load_state("networkidle")
                    final_url = new_page.url
                    logger.info(f"SUCCESS: Resolved to company URL: {final_url}")
                except Exception:
                    # Check for direct redirect
                    page.wait_for_timeout(4000)
                    if page.url != url:
                        final_url = page.url
                        logger.info(
                            f"SUCCESS: Resolved via direct redirect: {final_url}"
                        )
                    else:
                        logger.warning("No redirect detected after click.")

                browser.close()
                return final_url

        except Exception as e:
            logger.error(f"FATAL in _resolve_hiremetech: {e}")
            return url
