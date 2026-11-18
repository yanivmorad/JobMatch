import httpx
import pytest
from fastapi.testclient import TestClient

import server
from db.jobs_repository import add_new_job, get_all_jobs, get_job_by_url, mark_failed, retry_job


def _client():
    # ASGITransport לא מריץ lifespan, כך שה-workers לא עולים בבדיקות
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=server.app), base_url="http://test"
    )


@pytest.mark.db
async def test_manual_jobs_with_same_title_are_not_dropped(db):
    """באג: URL מזויף מהשם בלבד -> משרה ידנית שנייה עם אותו שם נבלעה בשקט."""
    payload = {"text": "תיאור משרה", "title": "משרה ידנית"}
    async with _client() as client:
        r1 = await client.post("/api/jobs/text", json=payload)
        r2 = await client.post("/api/jobs/text", json=payload)

    assert r1.status_code == r2.status_code == 200
    url1, url2 = r1.json()["url"], r2.json()["url"]
    assert url1 != url2
    assert url1.startswith("manual://")

    manual = [j for j in await get_all_jobs() if j["source"] == "manual"]
    assert len(manual) == 2
    assert all(j["status"] == "WAITING_FOR_AI" for j in manual)


def test_invalid_application_status_returns_400():
    """באג: הוחזר tuple, ו-FastAPI ענה 200 עם רשימה."""
    r = TestClient(server.app).post(
        "/api/jobs/application-status", json={"url": "x", "status": "bogus"}
    )
    assert r.status_code == 400


# --- retry לפי שלב הכישלון ---


@pytest.mark.db
async def test_retry_manual_job_goes_to_ai(db):
    """באג: retry שלח הכל לסריקה, כולל משרה ידנית עם URL שאי אפשר לסרוק."""
    await add_new_job("manual://1", source="manual", manual_text="t")
    job = await get_job_by_url("manual://1")
    await mark_failed(job["id"], "FAILED_ANALYSIS", "boom")

    await retry_job("manual://1")
    assert (await get_job_by_url("manual://1"))["status"] == "WAITING_FOR_AI"


@pytest.mark.db
async def test_retry_failed_resolve_goes_back_to_resolver(db):
    url = "https://hiremetech.com/job/1"
    await add_new_job(url)
    job = await get_job_by_url(url)
    await mark_failed(job["id"], "FAILED_RESOLVE", "boom")

    await retry_job(url)
    row = await get_job_by_url(url)
    assert row["status"] == "PENDING_RESOLVE"
    assert row["error_log"] is None


@pytest.mark.db
async def test_retry_failed_analysis_with_description_goes_to_ai(db, raw_conn):
    url = "https://jobs.example.com/a"
    await add_new_job(url)
    await raw_conn.execute(
        "UPDATE jobs SET full_description = 'desc', status = 'FAILED_ANALYSIS' WHERE url = $1",
        url,
    )

    await retry_job(url)
    assert (await get_job_by_url(url))["status"] == "WAITING_FOR_AI"


@pytest.mark.db
async def test_retry_failed_scrape_goes_to_scrape(db):
    url = "https://jobs.example.com/b"
    await add_new_job(url)
    job = await get_job_by_url(url)
    await mark_failed(job["id"], "FAILED_SCRAPE", "boom")

    await retry_job(url)
    assert (await get_job_by_url(url))["status"] == "WAITING_FOR_SCRAPE"
