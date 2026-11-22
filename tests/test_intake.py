"""קליטת משרות מטקסט גולמי: POST /api/jobs/raw, /api/jobs/extract-links ו-/api/jobs/url."""
from pathlib import Path

import httpx
import pytest

import server
from db.jobs_repository import add_new_job, find_existing_job, get_all_jobs, get_job_by_url, update_job_after_resolution

SAMPLE = (Path(__file__).parent / "fixtures" / "whatsapp_jobs.txt").read_text(encoding="utf-8")


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")


async def test_extract_links_preview_does_not_need_a_db():
    async with _client() as client:
        r = await client.post("/api/jobs/extract-links", json={"text": SAMPLE})
    assert r.status_code == 200
    body = r.json()
    assert len(body["jobs"]) == 7
    assert len(body["ignored"]) == 4
    assert all(not u.startswith("https://apps.apple.com") for u in body["jobs"])


@pytest.mark.db
async def test_raw_text_adds_only_job_links(db):
    async with _client() as client:
        r = await client.post("/api/jobs/raw", json={"text": SAMPLE})
    assert r.status_code == 200
    body = r.json()
    assert body["added"] == 7
    assert body["skipped"] == 0
    assert {i["url"] for i in body["ignored"]} >= {"https://hiremetech.com/communities"}

    jobs = await get_all_jobs()
    urls = {j["url"] for j in jobs}
    assert "https://hiremetech.com/job/147318715" in urls  # בלי utm
    assert all("utm_" not in u and "apps.apple.com" not in u for u in urls)
    assert all(j["status"] == "PENDING_RESOLVE" for j in jobs)
    assert all(j["source_url"] == j["url"] for j in jobs)


@pytest.mark.db
async def test_sending_the_same_messages_again_adds_nothing(db):
    async with _client() as client:
        await client.post("/api/jobs/raw", json={"text": SAMPLE})
        r = await client.post("/api/jobs/raw", json={"text": SAMPLE})
    body = r.json()
    assert body["added"] == 0
    assert body["skipped"] == 7
    assert len(await get_all_jobs()) == 7


@pytest.mark.db
async def test_resolved_job_is_still_found_by_the_link_the_user_sent(db):
    """HireMeTech: אחרי פענוח url הוא אתר החברה. אותו קישור שנשלח שוב = כפילות, בלי פענוח נוסף."""
    original = "https://hiremetech.com/job/147318715"
    await add_new_job(original)
    job = await get_job_by_url(original)
    await update_job_after_resolution(job["id"], "https://www.comeet.com/jobs/acme/1A.2B3/dev/4C.5D6", "WAITING_FOR_SCRAPE")

    assert (await find_existing_job(original))["id"] == job["id"]

    async with _client() as client:
        r = await client.post("/api/jobs/raw", json={"text": f"{original}?utm_source=other_group"})
    assert r.json()["added"] == 0
    assert r.json()["skipped_urls"][0]["url"] == original


@pytest.mark.db
async def test_url_endpoint_normalizes_and_detects_duplicates(db):
    async with _client() as client:
        r1 = await client.post("/api/jobs/url", json={"urls": ["https://jobs.lever.co/acme/1?utm_source=x"]})
        r2 = await client.post("/api/jobs/url", json={"urls": ["https://jobs.lever.co/acme/1"]})
    assert r1.status_code == 200 and r1.json()["added"] == 1
    assert r2.status_code == 409  # לינק בודד שכבר קיים
    assert (await get_job_by_url("https://jobs.lever.co/acme/1")) is not None


@pytest.mark.db
async def test_find_existing_job_can_exclude_itself(db):
    await add_new_job("https://jobs.lever.co/acme/2")
    job = await get_job_by_url("https://jobs.lever.co/acme/2")
    assert await find_existing_job("https://jobs.lever.co/acme/2", exclude_id=job["id"]) is None


async def test_extract_links_preview_includes_titles():
    async with _client() as client:
        r = await client.post("/api/jobs/extract-links", json={"text": SAMPLE})
    assert r.json()["titles"]["https://rapaport.bamboohr.com/careers/307"] == (
        "Customer Success Operations Specialist - Student"
    )


@pytest.mark.db
async def test_title_from_the_message_is_saved_with_the_job(db):
    async with _client() as client:
        await client.post("/api/jobs/raw", json={"text": SAMPLE})
    job = await get_job_by_url("https://hiremetech.com/job/147318715")
    assert job["job_title"] == "C# Software Developer"
    # החברה לא כתובה בהודעה - נשארת placeholder עד שה-AI / הסורק ימצאו אותה
    assert job["company"] == "https://hiremetech.com/job/147318715"


@pytest.mark.db
async def test_link_without_a_title_keeps_the_placeholder(db):
    async with _client() as client:
        await client.post("/api/jobs/raw", json={"text": "https://a.com/jobs/1"})
    job = await get_job_by_url("https://a.com/jobs/1")
    assert job["job_title"] == "https://a.com/jobs/1"
