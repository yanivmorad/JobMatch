import logging
import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [RESOLVER] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


def resolve_hireme_link(url: str):
    token = os.getenv("HIRE_ME_TECH_TOKEN")

    with sync_playwright() as p:
        # נשארים עם headless=False כדי שתראה מה קורה
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        try:
            # שלב 1: הזרקה
            logger.info("ניגש לדומיין להזרקת טוקן...")
            page.goto("https://hiremetech.com", wait_until="networkidle")

            # הזרקה של המפתח auth_token
            page.evaluate(f"localStorage.setItem('auth_token', '{token}')")
            logger.info("✅ הטוקן הוזרק")

            # שלב 2: מעבר למשרה
            logger.info(f"עובר לעמוד המשרה: {url}")
            page.goto(url, wait_until="networkidle")

            # המתנה קצרה כדי לוודא שה-JS סיים לרנדר את הכפתורים
            page.wait_for_timeout(4000)

            # שלב 3: בדיקת מצב חיבור
            # נבדוק אם יש אלמנט שמעיד על כך שאנחנו מחוברים (למשל כפתור פרופיל או יציאה)
            is_logged_in = page.evaluate("() => !!localStorage.getItem('auth_token')")
            logger.info(f"בדיקת LocalStorage: auth_token קיים? {is_logged_in}")

            # שלב 4: חיפוש הכפתור לפי סלקטורים חלופיים
            # ננסה למצוא כל כפתור שמכיל את המילה "הגש" או "מועמדות"
            logger.info("מחפש כפתור הגשה...")

            # רשימת סלקטורים אפשריים
            selectors = [
                'button:has-text("הגש מועמדות")',
                'a:has-text("הגש מועמדות")',
                ".bg-gradient-to-r",  # המחלקה ששלחת קודם
                "button.flex-1",
            ]

            target_button = None
            for selector in selectors:
                if page.is_visible(selector):
                    target_button = selector
                    logger.info(f"🎯 נמצא כפתור באמצעות סלקטור: {selector}")
                    break

            if not target_button:
                logger.error("❌ לא נמצא כפתור הגשה. מצלם מסך לדיבאג...")
                page.screenshot(path="debug_screen.png")
                # נסה להדפיס את כל הטקסט של הכפתורים בדף
                buttons = page.query_selector_all("button")
                logger.info(f"נמצאו {len(buttons)} כפתורים בדף:")
                for i, btn in enumerate(buttons[:5]):
                    logger.info(f"Button {i}: {btn.inner_text()}")

                browser.close()
                return url

            # שלב 5: לחיצה
            logger.info(f"לוחץ על {target_button}...")

            # ניסיון תפיסת דף חדש
            try:
                with context.expect_page(timeout=10000) as new_page_info:
                    page.click(target_button)
                new_page = new_page_info.value
                new_page.wait_for_load_state("networkidle")
                resolved_url = new_page.url
            except:
                logger.info("לא נפתח דף חדש, בודק אם ה-URL של הדף הנוכחי השתנה...")
                page.wait_for_timeout(3000)
                resolved_url = page.url

            logger.info(f"🎯 תוצאה: {resolved_url}")
            browser.close()
            return resolved_url

        except Exception as e:
            logger.error(f"שגיאה: {e}")
            browser.close()
            return url


if __name__ == "__main__":
    test_link = "https://hiremetech.com/job/106273229"
    print(f"RESULT: {resolve_hireme_link(test_link)}")
