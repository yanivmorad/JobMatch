import os
import re
import time
from typing import Optional

import requests
from dotenv import load_dotenv

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
        self.hireme_token = os.getenv("HIRE_ME_TECH_TOKEN")

        if not self.api_key:
            raise ValueError("❌ JINA_API_KEY missing!")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Timeout": "40",
            "X-With-Iframe": "true",
            "X-With-Shadow-Dom": "true",
        }

    # --- פונקציות עזר לניקוי ותקינות ---
    def is_content_valid(self, text: str) -> bool:
        if not text or len(text) < 250:
            return False
        invalid_markers = ["access denied", "robot check", "captcha", "404 not found"]
        return not any(marker in text.lower() for marker in invalid_markers)

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"^>?\s*https?://[^\n]+\n?", "", text, flags=re.MULTILINE)
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # --- טיפול מיוחד באתרים ספציפיים (The Resolvers) ---

    def _resolve_hiremetech(self, url: str) -> str:
        """מזריק טוקן, לוחץ על כפתור ומחזיר את ה-URL הסופי של החברה"""
        if not HAS_PLAYWRIGHT or not self.hireme_token:
            print("⚠️ Playwright missing or Token not set in .env")
            return url

        print(f"🔑 מבצע VIP Access עבור HireMeTech: {url}")
        try:
            with sync_playwright() as p:
                # בשרת נריץ headless=True, בבדיקות מקומיות אפשר False כדי לראות את הקסם
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1280, "height": 800})
                page = context.new_page()

                # 1. הזרקת הטוקן - שים לב לתיקון ל-auth_token
                page.goto("https://hiremetech.com")
                page.evaluate(
                    f"localStorage.setItem('auth_token', '{self.hireme_token}')"
                )

                # 2. ניווט למשרה והמתנה לכפתור
                page.goto(url, wait_until="networkidle")
                apply_button = 'button:has-text("הגש מועמדות")'

                # מחכה שהכפתור יופיע (לפעמים לוקח רגע ל-JS להתרנדר)
                page.wait_for_selector(apply_button, timeout=10000)

                # 3. לחיצה חכמה
                # האתר בדרך כלל פותח טאב חדש. נתפוס את ה-Event הזה.
                with context.expect_page() as new_page_info:
                    page.click(apply_button)

                new_page = new_page_info.value
                new_page.wait_for_load_state("networkidle")

                final_url = new_page.url
                print(f"🚀 הצלחנו! הלינק האמיתי הוא: {final_url}")

                browser.close()
                return final_url
        except Exception as e:
            print(f"❌ נכשל בחילוץ לינק (HireMeTech): {e}")
            return url

    # --- מנגנוני הסריקה המרכזיים ---

    def _scrape_with_playwright(self, url: str) -> Optional[str]:
        """גיבוי למקרה ש-Jina לא מצליח לקרוא את אתר היעד"""
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
        except:
            return None

    def scrape(self, url: str, retries: int = 2) -> Optional[dict]:
        """הפונקציה המרכזית שאתה קורא לה"""

        # --- שלב 1: זיהוי וטיפול באתרים ספציפיים ---
        target_url = url
        if "hiremetech.com" in url:
            resolved = self._resolve_hiremetech(url)
            # אם הלינק השתנה, נמשיך לסרוק את הלינק החדש
            if resolved != url:
                target_url = resolved

        # --- שלב 2: סריקה באמצעות Jina (המסלול המהיר והנקי) ---
        jina_url = f"https://r.jina.ai/{target_url}"
        print(f"📡 סורק באמצעות Jina: {target_url}")

        for attempt in range(retries):
            try:
                headers = self.headers.copy()
                if attempt > 0:
                    headers["X-No-Cache"] = "true"

                res = self.session.get(jina_url, headers=headers, timeout=40)
                if res.status_code == 200 and self.is_content_valid(res.text):
                    return {
                        "source": "jina",
                        "url": target_url,
                        "full_description": self.clean_text(res.text),
                    }
            except Exception as e:
                print(f"⚠️ ניסיון Jina {attempt + 1} נכשל: {e}")
            time.sleep(1)

        # --- שלב 3: גיבוי Playwright (המסלול הכבד) ---
        print("🚨 עובר לגיבוי Playwright מלא...")
        local_content = self._scrape_with_playwright(target_url)
        if local_content and self.is_content_valid(local_content):
            return {
                "source": "local_browser",
                "url": target_url,
                "full_description": self.clean_text(local_content),
            }

        return None


if __name__ == "__main__":
    scraper = Scraper()
    # בדיקה על לינק של HireMeTech
    test_url = "https://hiremetech.com/job/106273229"
    res = scraper.scrape(test_url)

    if res:
        print("\n✅ סריקה הושלמה!")
        print(f"מקור: {res['source']}")
        print(f"לינק יעד: {res['url']}")
        print(f"תוכן: {res['full_description'][:200]}...")
