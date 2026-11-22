# src/scraper_service/resolvers.py
import base64
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv

from scraper_service.utils import playwright_allowed

try:
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# טעינת משתני סביבה מהקובץ .env
load_dotenv()

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
DEBUG_DIR = os.path.join(
    (os.getenv("LOG_DIR") or "").strip() or os.path.join(_PROJECT_ROOT, "logs"),
    "debug",
)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class ResolveError(Exception):
    """
    פענוח הקישור נכשל. ההודעה מוצגת למשתמש ב-UI (error_log).
    public_fallback=True: לדף המקורי יש תיאור משרה ציבורי (HireMeTech מציג את כל התיאור
    גם בלי התחברות, רק בלי שם החברה), ולכן אפשר לסרוק אותו במקום לעצור.
    """

    def __init__(self, message: str, public_fallback: bool = False):
        super().__init__(message)
        self.public_fallback = public_fallback


def token_expiry(token: str) -> Optional[datetime]:
    """מועד התפוגה (exp) של JWT, בלי לאמת חתימה. None אם זה לא JWT או שאין exp."""
    try:
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)
    except Exception:
        return None


def hiremetech_token_status(token: Optional[str] = None) -> dict:
    """מצב הטוקן (ל-/health ולוגים): configured / expires_at / expired. לא חושף את הטוקן עצמו."""
    token = token if token is not None else (os.getenv("HIRE_ME_TECH_TOKEN") or "").strip()
    if not token:
        return {"configured": False, "expires_at": None, "expired": None}
    exp = token_expiry(token)
    return {
        "configured": True,
        "expires_at": exp.isoformat() if exp else None,
        "expired": (exp <= datetime.now(timezone.utc)) if exp else None,
    }


def _debug_screenshot(page, name: str) -> None:
    """
    צילום מסך לדיבאג - רק כש-DEBUG_SCREENSHOTS=true, ורק לתוך logs/debug/.
    (קודם נשמר תמיד לתיקיית העבודה, כלומר לשורש הפרויקט / לדיסק של השרת בענן)
    """
    if os.getenv("DEBUG_SCREENSHOTS", "").strip().lower() not in ("1", "true", "yes"):
        return
    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        path = os.path.join(DEBUG_DIR, name)
        page.screenshot(path=path)
        logger.info(f"Debug screenshot saved: {path}")
    except Exception as e:
        logger.warning(f"Could not save debug screenshot {name}: {e}")


def is_hiremetech(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "hiremetech.com" or host.endswith(".hiremetech.com")


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
        self.hireme_token = hireme_token or (os.getenv("HIRE_ME_TECH_TOKEN") or "").strip()

    def resolve(self, url: str, job_id: Optional[int] = None) -> str:
        """
        Resolves a URL to its final destination.
        Raises ResolveError when a special site cannot be resolved: scraping the
        HireMeTech page itself would only return its login wall.
        """
        id_tag = f"[ID {job_id}] " if job_id else ""
        if is_hiremetech(url):
            logger.info(
                f"{id_tag}Resolver: HireMeTech detected for {url}, starting VIP resolution"
            )
            return self._resolve_hiremetech(url, job_id=job_id)

        return url

    def _resolve_hiremetech(self, url: str, job_id: Optional[int] = None) -> str:
        """
        Resolves HireMeTech job URLs to actual company URLs.
        Matches the logic of the successful standalone script.
        """
        id_tag = f"[ID {job_id}] " if job_id else ""
        # כל כישלון כאן מאפשר fallback: הדף הציבורי של HireMeTech מכיל את תיאור המשרה
        if not HAS_PLAYWRIGHT or not playwright_allowed():
            raise ResolveError(
                "HireMeTech: הדפדפן (Playwright) לא זמין בשרת, אי אפשר לפענח את הקישור",
                public_fallback=True,
            )

        if not self.hireme_token:
            raise ResolveError(
                "HireMeTech: חסר HIRE_ME_TECH_TOKEN בהגדרות השרת", public_fallback=True
            )

        # הטוקן תקף שבוע. בלי הבדיקה הזו פתחנו דפדפן (~20 שניות) רק כדי לגלות שאנחנו לא מחוברים
        expires = token_expiry(self.hireme_token)
        if expires and expires <= datetime.now(timezone.utc):
            raise ResolveError(
                f"HireMeTech: הטוקן (HIRE_ME_TECH_TOKEN) פג ב-{expires:%d/%m/%Y} - "
                "יש להתחבר לאתר ולעדכן אותו",
                public_fallback=True,
            )

        logger.info(f"{id_tag}Resolver: Starting Playwright for HireMeTech: {url}")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    return self._click_through_hiremetech(browser, url, job_id, id_tag)
                finally:
                    # נסגר תמיד, גם בשגיאה / timeout
                    browser.close()
        except ResolveError as e:
            e.public_fallback = True
            raise
        except Exception as e:
            logger.error(
                f"{id_tag}Resolver: FATAL error in _resolve_hiremetech for {url}: {e}"
            )
            raise ResolveError(
                f"HireMeTech: שגיאה בפענוח הקישור ({type(e).__name__})", public_fallback=True
            ) from e

    def _click_through_hiremetech(self, browser, url, job_id, id_tag) -> str:
        context = browser.new_context(
            viewport={"width": 1280, "height": 800}, user_agent=_USER_AGENT
        )
        page = context.new_page()

        # 1. Access the job page
        logger.info(f"{id_tag}Resolver: Navigating to HireMeTech job page: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # 2. Inject token into local storage (כארגומנט, לא משורשר לקוד JS)
        page.evaluate(
            "token => window.localStorage.setItem('auth_token', token)",
            self.hireme_token,
        )

        # 3. Reload and wait for session to apply
        logger.debug(f"{id_tag}Resolver: Injecting token and reloading for {url}")
        page.reload(wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(4000)

        # טוקן שהאתר דחה (פג / בוטל) נמחק מ-localStorage אחרי הטעינה, והדף מוצג כאורח:
        # הכפתור "הגש מועמדות" עדיין קיים אבל לא מוביל לאתר החברה
        if not page.evaluate("() => !!window.localStorage.getItem('auth_token')"):
            raise ResolveError(
                "HireMeTech: האתר דחה את הטוקן (HIRE_ME_TECH_TOKEN) - יש להתחבר לאתר ולעדכן אותו"
            )

        # 4. Smart Button Detection
        apply_button = None
        for text in ["הגש מועמדות", "Apply Now"]:
            btn = page.get_by_role("button", name=text, exact=False)
            if btn.is_visible():
                apply_button = btn
                logger.info(
                    f"{id_tag}Resolver: Found Apply button with text '{text}' for {url}"
                )
                break

        if not apply_button:
            # Fallback to CSS
            apply_button = page.locator("button.bg-gradient-to-r").first

        if not apply_button or not apply_button.is_visible():
            logger.error(f"{id_tag}Resolver: FAILED to find Apply button for {url}.")
            _debug_screenshot(
                page, f"missing_button_{job_id}.png" if job_id else "missing_button.png"
            )
            raise ResolveError(
                "HireMeTech: לא נמצא כפתור הגשה - ייתכן שהטוקן פג או שהמשרה הוסרה"
            )

        # 5. Execute Click and Capture Final URL
        logger.info(f"{id_tag}Resolver: Clicking apply button for {url}")
        new_page = None
        try:
            with context.expect_page(timeout=10000) as new_page_info:
                apply_button.click(force=True, delay=300)
            new_page = new_page_info.value
        except Exception:
            pass  # לא נפתח טאב חדש - אולי הפניה באותו טאב

        if new_page is not None:
            # timeout של טעינה לא מבטל את ה-URL שכבר הגענו אליו (אתרים כבדים לא מגיעים ל-networkidle)
            for state, timeout in (("domcontentloaded", 20000), ("networkidle", 10000)):
                try:
                    new_page.wait_for_load_state(state, timeout=timeout)
                except Exception:
                    break
            final_url = new_page.url
        else:
            page.wait_for_timeout(4000)
            final_url = page.url

        if not final_url.startswith("http") or is_hiremetech(final_url):
            logger.warning(f"{id_tag}Resolver: No redirect detected for {url} after click.")
            raise ResolveError(
                "HireMeTech: הלחיצה על 'הגש מועמדות' לא הובילה לאתר החברה"
            )

        logger.info(f"{id_tag}Resolver: SUCCESS! Resolved {url} to {final_url}")
        return final_url
