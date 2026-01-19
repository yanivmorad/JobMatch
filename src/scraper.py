import os
import re
import time
from typing import Optional

import requests
from dotenv import load_dotenv

# ניסיון ייבוא ספריות גיבוי
try:
    from markdownify import markdownify as md
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

load_dotenv()


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

    def is_content_valid(self, text: str) -> bool:
        if not text or len(text) < 250:
            return False
        invalid_markers = [
            "access denied",
            "robot check",
            "captcha",
            "404 not found",
            "page not found",
        ]
        low_text = text.lower()
        return not any(marker in low_text for marker in invalid_markers)

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"^>?\s*https?://[^\n]+\n?", "", text, flags=re.MULTILINE)
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _scrape_with_playwright(self, url: str) -> Optional[str]:
        if not HAS_PLAYWRIGHT:
            return None

        print(f"🕵️ מפעיל דפדפן מקומי (Playwright) עבור {url}...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()

                # תיקון ייבוא Stealth
                try:
                    from playwright_stealth import stealth_sync

                    stealth_sync(page)
                except Exception:
                    # אם נכשל, נמשיך בלי stealth
                    pass

                page.goto(url, timeout=60000, wait_until="networkidle")
                page.wait_for_timeout(5000)  # המתנה לרינדור של Civi

                all_text = []
                # חילוץ מהדף הראשי
                all_text.append(md(page.content()))

                # חילוץ מכל ה-Frames (חשוב לאתרי משרות)
                for frame in page.frames:
                    try:
                        f_content = frame.content()
                        if len(f_content) > 200:
                            all_text.append(md(f_content))
                    except:
                        continue

                browser.close()
                return "\n\n".join(all_text)
        except Exception as e:
            print(f"❌ שגיאה בדפדפן: {e}")
            return None

    def scrape(self, url: str, retries: int = 2) -> Optional[dict]:
        jina_url = f"https://r.jina.ai/{url}"

        # שלב 1: Jina
        for attempt in range(retries):
            try:
                headers = self.headers.copy()
                if attempt > 0:
                    headers["X-No-Cache"] = "true"

                res = self.session.get(jina_url, headers=headers, timeout=40)
                if res.status_code == 200 and self.is_content_valid(res.text):
                    return {
                        "source": "jina",
                        "full_description": self.clean_text(res.text),
                    }
            except:
                pass
            time.sleep(2)

        # שלב 2: Playwright
        print("🚨 עובר לגיבוי מקומי...")
        local_content = self._scrape_with_playwright(url)
        if local_content and self.is_content_valid(local_content):
            return {
                "source": "local_browser",
                "full_description": self.clean_text(local_content),
            }

        return None


if __name__ == "__main__":
    scraper = Scraper()
    # לינקים תקינים לבדיקה (שים לב לתיקון ה-ID ב-Civi)
    test_urls = [
        "https://app.civi.co.il/promo/id=598750&src=927",
        "https://careers.riverside.com/careers/junior-marketing-analyst",
    ]

    for url in test_urls:
        print(f"\n--- בודק: {url} ---")
        res = scraper.scrape(url)
        if res:
            print(f"✅ הצלחה! מקור: {res['source']}")
            print(f"טקסט (חלקי): {res['full_description'][:200]}...")
        else:
            print("🛑 נכשל סופית")
