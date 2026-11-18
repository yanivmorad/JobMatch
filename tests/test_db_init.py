import pytest

from db import postgres
from db.jobs_repository import (
    ApplicationStatus,
    add_new_job,
    auto_archive_old_applications,
    get_job_by_url,
    update_application_status,
    update_user_action,
)

pytestmark = pytest.mark.db


async def _columns(conn) -> set:
    rows = await conn.fetch(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'jobs'"
    )
    return {r["column_name"] for r in rows}


async def test_init_on_empty_database(empty_db, raw_conn):
    """באג: על DB ריק השרת קרס (set_type_codec על טיפוס שלא קיים + ALTER לפני CREATE)."""
    await postgres.get_pool()

    cols = await _columns(raw_conn)
    assert {"id", "url", "status", "application_status", "updated_at"} <= cols


async def test_init_is_idempotent(empty_db):
    await postgres.get_pool()
    await postgres.close_pool()
    await postgres.get_pool()  # לא אמור לזרוק
    pool = await postgres.get_pool()
    async with pool.acquire() as conn:
        await postgres.init_db(conn)  # ריצה שלישית


async def test_init_migrates_legacy_schema(empty_db, raw_conn):
    """DB שנוצר בגרסה ישנה: Enum חלקי, בלי updated_at ובלי application_status."""
    await raw_conn.execute(
        """
        CREATE TYPE job_status AS ENUM ('NEW', 'PENDING_RESOLVE', 'COMPLETED');
        CREATE TABLE jobs (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            status job_status DEFAULT 'NEW',
            company TEXT, job_title TEXT, source TEXT, full_description TEXT,
            analysis_result JSONB, user_action TEXT DEFAULT 'none',
            is_archived BOOLEAN DEFAULT FALSE, error_log TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            scraped_at TIMESTAMPTZ, analyzed_at TIMESTAMPTZ
        );
        INSERT INTO jobs (url, status) VALUES ('https://old.example/job', 'COMPLETED');
        """
    )

    await postgres.get_pool()

    cols = await _columns(raw_conn)
    assert {"application_status", "updated_at"} <= cols

    enum_values = {
        r["enumlabel"]
        for r in await raw_conn.fetch(
            "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'job_status'"
        )
    }
    assert set(postgres.JOB_STATUSES) <= enum_values

    old = await get_job_by_url("https://old.example/job")
    assert old["application_status"] == "pending"


async def test_status_enum_is_returned_as_str(db):
    await add_new_job("https://example.com/job/1")
    job = await get_job_by_url("https://example.com/job/1")
    assert job["status"] == "PENDING_RESOLVE"
    assert isinstance(job["status"], str)


async def test_update_user_action_writes_application_status(db):
    """באג: update_user_action כתב לעמודה application_status שלא הייתה קיימת."""
    url = "https://example.com/job/2"
    await add_new_job(url)

    await update_user_action(url, "applied")
    job = await get_job_by_url(url)
    assert job["application_status"] == "applied"
    assert job["user_action"] == "applied"
    assert job["is_archived"] is True

    await update_user_action(url, "ignored")
    assert (await get_job_by_url(url))["application_status"] == "not_relevant"


async def test_update_application_status(db):
    url = "https://example.com/job/3"
    await add_new_job(url)

    await update_application_status(url, ApplicationStatus.INTERVIEW)
    job = await get_job_by_url(url)
    assert job["application_status"] == "interview"
    assert job["is_archived"] is False

    await update_application_status(url, ApplicationStatus.REJECTED)
    job = await get_job_by_url(url)
    assert job["application_status"] == "rejected"
    assert job["is_archived"] is True
    assert job["user_action"] == "ignored"


async def test_auto_archive_old_applications(db, raw_conn):
    url = "https://example.com/job/4"
    await add_new_job(url)
    await update_application_status(url, ApplicationStatus.APPLIED)
    await raw_conn.execute(
        "UPDATE jobs SET created_at = NOW() - INTERVAL '31 days' WHERE url = $1", url
    )

    await auto_archive_old_applications()
    assert (await get_job_by_url(url))["application_status"] == "ghosted"
