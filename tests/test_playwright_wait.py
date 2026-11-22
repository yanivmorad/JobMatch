"""
באג: ה-fallback של Playwright חיכה 2 שניות קבועות אחרי domcontentloaded, ובדפי SPA
(Workday / BambooHR) חזר שלד ריק (9 / 25 תווים). עכשיו מחכים לתוכן.
בדיקה אמיתית עם Chromium על דף מקומי שמרנדר את המשרה רק אחרי 3 שניות.
"""
import pytest

from scraper_service import scraper as scraper_module
from scraper_service.scraper import Scraper

pytestmark = pytest.mark.skipif(not scraper_module.HAS_PLAYWRIGHT, reason="Playwright not installed")

_SPA = """<!doctype html><html><head><title>Careers</title></head><body><div id="app">Loading...</div>
<script>
setTimeout(() => {
  document.getElementById('app').innerText =
    'Data Analyst. Requirements: 2+ years of experience with SQL. Responsibilities: build reports. '.repeat(20)
    + ' SpaContentMarker42';
}, 3000);
</script></body></html>"""


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _chromium_available(), reason="Chromium for Playwright not installed")
def test_playwright_waits_for_spa_content(tmp_path):
    page = tmp_path / "spa.html"
    page.write_text(_SPA, encoding="utf-8")

    content = Scraper()._scrape_with_playwright(page.as_uri())

    assert content is not None
    assert "SpaContentMarker42" in content  # עם המתנה קבועה של 2 שניות היה כאן רק "Loading..."
