# src/hireme_resolver.py
import logging
import os
import time

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [DEBUG-LOG] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


def resolve_hireme_link(url: str):
    token = os.getenv("HIRE_ME_TECH_TOKEN")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        try:
            # Step 1: Login Injection
            logger.info(f"Navigating to job: {url}")
            page.goto(url, wait_until="domcontentloaded")
            page.evaluate(f"window.localStorage.setItem('auth_token', '{token}');")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(4000)

            # Step 2: Smarter Button Detection (Hebrew or English)
            logger.info("Looking for Apply button (Hebrew/English)...")

            # We try to find any button that matches our known labels
            apply_button = None
            possible_texts = ["הגש מועמדות", "Apply Now"]

            for text in possible_texts:
                btn = page.get_by_role("button", name=text, exact=False)
                if btn.is_visible():
                    apply_button = btn
                    logger.info(f"MATCH: Found button with text: '{text}'")
                    break

            if not apply_button:
                # Fallback to CSS class if text match fails
                logger.info("Text match failed, trying CSS selector...")
                apply_button = page.locator("button.bg-gradient-to-r").first

            if not apply_button or not apply_button.is_visible():
                logger.error("COULD NOT FIND BUTTON. Capturing screenshot...")
                page.screenshot(path="debug_missing_button.png")
                browser.close()
                return url

            # Step 3: Execution of the Click
            logger.info("Clicking the button...")

            final_url = url
            try:
                # Catching redirection
                with context.expect_page(timeout=10000) as new_page_info:
                    # Force click is useful if the modal backdrop is still lingering in the DOM
                    apply_button.click(force=True, delay=200)

                new_page = new_page_info.value
                new_page.wait_for_load_state("networkidle")
                final_url = new_page.url
                logger.info(f"SUCCESS: Captured final URL: {final_url}")

            except Exception:
                logger.info("No new tab. Checking current page for redirection...")
                page.wait_for_timeout(5000)
                if page.url != url:
                    final_url = page.url
                    logger.info(f"SUCCESS: Current page redirected to: {final_url}")
                else:
                    logger.error("FAIL: Button clicked but no redirection happened.")
                    page.screenshot(path="click_but_no_redirect.png")

            time.sleep(2)
            browser.close()
            return final_url

        except Exception as e:
            logger.error(f"SYSTEM ERROR: {e}")
            browser.close()
            return url


if __name__ == "__main__":
    test_link = "https://hiremetech.com/job/106273229"
    result = resolve_hireme_link(test_link)
    print(f"\n--- RESOLVED URL: {result} ---")
