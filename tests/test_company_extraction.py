import pytest

from db.jobs_repository import (
    add_new_job,
    fetch_next_job,
    finish_analysis,
    finish_scrape,
    get_all_jobs,
    get_job_by_url,
)

pytestmark = pytest.mark.db


async def _scraped_job(url: str) -> dict:
    """מכניס משרה ומריץ אותה עד אחרי שלב הסריקה (כמו ה-workers)."""
    await add_new_job(url)
    job = await fetch_next_job("PENDING_RESOLVE", "RESOLVING")
    return job


async def test_scrape_does_not_overwrite_company_with_unknown(db):
    """באג: הסורק לא מחזיר company/title, וה-worker כתב 'Unknown' לעמודות."""
    job = await _scraped_job("https://jobs.example.com/1")
    await finish_scrape(job["id"], "תיאור משרה ארוך")

    row = await get_job_by_url("https://jobs.example.com/1")
    assert row["company"] != "Unknown"
    assert row["job_title"] != "Unknown"
    assert row["status"] == "WAITING_FOR_AI"


async def test_analysis_fills_company_and_title(db):
    job = await _scraped_job("https://jobs.example.com/2")
    await finish_scrape(job["id"], "תיאור")

    await finish_analysis(
        job["id"],
        {"company": " Wix ", "job_title": "Backend Developer", "suitability_score": 80},
    )

    row = await get_job_by_url("https://jobs.example.com/2")
    assert row["company"] == "Wix"
    assert row["job_title"] == "Backend Developer"
    assert row["status"] == "COMPLETED"


async def test_analysis_does_not_override_manual_values(db):
    url = "manual://abc"
    await add_new_job(
        url, source="manual", manual_text="t", manual_meta={"company": "Monday", "title": "QA"}
    )
    job = await get_job_by_url(url)

    await finish_analysis(job["id"], {"company": "Other Co", "job_title": "Other"})

    row = await get_job_by_url(url)
    assert row["company"] == "Monday"
    assert row["job_title"] == "QA"


async def test_analysis_placeholder_does_not_replace_value(db):
    """אם Gemini לא מצא ('לא צוין') - לא כותבים placeholder חדש על הקיים."""
    job = await _scraped_job("https://jobs.example.com/3")
    await finish_analysis(job["id"], {"company": "לא צוין", "job_title": "Unknown"})

    row = await get_job_by_url("https://jobs.example.com/3")
    assert row["company"] == "https://jobs.example.com/3"  # ה-placeholder המקורי נשאר
    assert row["status"] == "COMPLETED"


async def test_get_all_jobs_uses_db_columns_over_analysis_json(db):
    url = "manual://def"
    await add_new_job(
        url, source="manual", manual_text="t", manual_meta={"company": "Monday", "title": "QA"}
    )
    job = await get_job_by_url(url)
    await finish_analysis(
        job["id"], {"company": "Other Co", "url": "x", "suitability_score": 70}
    )

    listed = next(j for j in await get_all_jobs() if j["id"] == job["id"])
    assert listed["company"] == "Monday"
    assert listed["url"] == url
    assert listed["suitability_score"] == 70
