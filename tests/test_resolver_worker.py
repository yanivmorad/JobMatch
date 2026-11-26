"""resolver_worker: fallback לדף הציבורי של HireMeTech, נרמול הקישור שפוענח וזיהוי כפילויות."""
import pytest

from db.jobs_repository import add_new_job, get_job_by_url
from scraper_service.resolvers import ResolveError
from workers import worker_manager

pytestmark = pytest.mark.db


async def _run_resolver_once(monkeypatch, resolve):
    """מעבד את כל המשרות שבתור הפענוח (resolve_next עד שאין עבודה)."""

    class FakeResolver:
        hireme_token = "t"

        def resolve(self, url, job_id=None):
            return resolve(url)

    while await worker_manager.resolve_next(FakeResolver()):
        pass


async def test_hiremetech_failure_falls_back_to_scraping_the_public_page(db, monkeypatch):
    url = "https://hiremetech.com/job/147318715"
    await add_new_job(url)

    def expired(_url):
        raise ResolveError("HireMeTech: הטוקן פג ב-22/02/2026", public_fallback=True)

    await _run_resolver_once(monkeypatch, expired)

    job = await get_job_by_url(url)
    assert job["status"] == "WAITING_FOR_SCRAPE"  # ולא FAILED_RESOLVE
    assert "הטוקן פג" in job["error_log"] and "הדף הציבורי" in job["error_log"]


async def test_resolve_error_without_fallback_still_fails(db, monkeypatch):
    url = "https://short.example/abc"
    await add_new_job(url)

    def broken(_url):
        raise ResolveError("broken link")

    await _run_resolver_once(monkeypatch, broken)
    assert (await get_job_by_url(url))["status"] == "FAILED_RESOLVE"


async def test_resolved_url_is_normalized_and_checked_for_duplicates(db, monkeypatch):
    company_job = "https://www.comeet.com/jobs/acme/1A.2B3/dev/4C.5D6"
    await add_new_job(company_job)  # המשרה כבר קיימת (נשלחה ישירות)
    await add_new_job("https://hiremetech.com/job/1")

    await _run_resolver_once(monkeypatch, lambda u: company_job + "?utm_source=hiremetech" if "hiremetech" in u else u)

    dup = await get_job_by_url("https://hiremetech.com/job/1")
    assert dup["status"] == "DUPLICATE"


async def test_resolved_url_is_stored_without_tracking_params(db, monkeypatch):
    await add_new_job("https://hiremetech.com/job/2")

    await _run_resolver_once(monkeypatch, lambda u: "https://jobs.lever.co/acme/9?utm_source=hiremetech&lever-origin=applied")

    job = await get_job_by_url("https://jobs.lever.co/acme/9?lever-origin=applied")
    assert job is not None and job["status"] == "WAITING_FOR_SCRAPE"
    assert job["source_url"] == "https://hiremetech.com/job/2"


async def test_duplicate_hands_the_bot_notification_to_the_original(db, monkeypatch):
    """הצד של ה-resolver: מסמן DUPLICATE ומעביר את ההתראה למשרה המקורית."""
    from db.jobs_repository import add_job_notification
    from db.postgres import get_pool

    company_job = "https://www.comeet.com/jobs/acme/1A.2B3/dev/4C.5D6"
    original = await add_new_job(company_job)
    dup = await add_new_job("https://hiremetech.com/job/7", source="whatsapp")
    await add_job_notification(dup, "whatsapp", "972501234567")

    await _run_resolver_once(monkeypatch, lambda u: company_job)

    assert (await get_job_by_url("https://hiremetech.com/job/7"))["status"] == "DUPLICATE"
    rows = await (await get_pool()).fetch("SELECT job_id FROM job_notifications")
    assert [r["job_id"] for r in rows] == [original]