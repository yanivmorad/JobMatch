import pytest

from db.jobs_repository import (
    add_new_job,
    fetch_next_job,
    finish_analysis,
    finish_scrape,
    get_all_jobs,
    get_job_by_url,
    update_manual_job,
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


async def test_analysis_title_replaces_the_title_guessed_from_the_message(db):
    """
    באג (בדיקת קצה לקצה בענן, 26.11): הכותרת שנוחשה מההודעה ("GitLab - remote", "להיום")
    הוצגה בדשבורד במקום שם המשרה שה-AI קרא בדף ("Customer Success Engineer, EMEA").
    הכותרת מההודעה היא רמז ל-AI, לא ערך שהמשתמש הקליד.
    """
    url = "https://jobs.example.com/msg"
    await add_new_job(url, source="web", manual_meta={"title": "GitLab - remote"})
    job = await fetch_next_job("PENDING_RESOLVE", "RESOLVING")
    await finish_scrape(job["id"], "תיאור")

    await finish_analysis(
        job["id"], {"company": "GitLab", "job_title": "Customer Success Engineer, EMEA"}
    )

    row = await get_job_by_url(url)
    assert row["job_title"] == "Customer Success Engineer, EMEA"


async def test_analysis_keeps_the_message_title_when_the_ai_finds_none(db):
    url = "https://jobs.example.com/msg2"
    await add_new_job(url, source="web", manual_meta={"title": "QA Engineer"})
    job = await get_job_by_url(url)

    await finish_analysis(job["id"], {"company": "Acme", "job_title": "לא צוין"})

    assert (await get_job_by_url(url))["job_title"] == "QA Engineer"


async def test_analysis_does_not_override_a_title_the_user_edited(db):
    """עריכה במסך המשרה (update_manual_job) היא ערך של המשתמש, גם למשרה שנכנסה מקישור."""
    url = "https://jobs.example.com/edited"
    await add_new_job(url, source="web", manual_meta={"title": "מההודעה"})
    await update_manual_job(url, "Monday", "QA Lead", "תיאור שהמשתמש הדביק")
    job = await get_job_by_url(url)

    await finish_analysis(job["id"], {"company": "Other Co", "job_title": "Other"})

    row = await get_job_by_url(url)
    assert row["company"] == "Monday"
    assert row["job_title"] == "QA Lead"


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
    # קודם ה-URL (placeholder זמני מההוספה) נשאר והוצג ב-UI כשם החברה; אחרי הניתוח - "לא צוין"
    assert row["company"] == "לא צוין"
    assert row["job_title"] == "לא צוין"
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


@pytest.mark.db
async def test_unknown_company_becomes_not_specified_instead_of_the_url(db):
    """ה-AI לא מצא חברה (למשל HireMeTech בלי טוקן): לא משאירים את ה-URL כשם החברה ב-UI."""
    from db.jobs_repository import add_new_job, finish_analysis, get_job_by_url

    url = "https://hiremetech.com/job/1"
    await add_new_job(url)
    job = await get_job_by_url(url)
    await finish_analysis(job["id"], {"company": "Company | HireMe", "job_title": "RPA Developer"})
    row = await get_job_by_url(url)
    assert row["company"] == "לא צוין"
    assert row["job_title"] == "RPA Developer"


@pytest.mark.parametrize(
    "value",
    ["HireMeTech", "hiremetech.com", "שם החברה מוסתר בדף הציבורי של HireMeTech", "(שם החברה מוסתר)"],
)
def test_platform_or_masked_note_is_not_a_company(value):
    """באג (E2E): ה-AI החזיר 'HireMeTech' או את הערת ההסתרה כשם החברה."""
    from services.job_fields import clean_field

    assert clean_field(value) is None


def test_real_companies_are_kept():
    from services.job_fields import clean_field

    for name in ("Giv Solutions", "Medatech (דרך מטריקס)", "חברת ביטוח מובילה", "Applied Materials"):
        assert clean_field(name) == name
