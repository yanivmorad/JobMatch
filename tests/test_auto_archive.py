"""
באג (סעיף 8): auto_archive_old_applications לא נקראה מאף מקום, וחישבה 30 יום לפי
created_at (מתי המשרה נוספה) במקום לפי מתי הוגשה המועמדות.
"""
import asyncio

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
from workers import worker_manager

# --- applied_at ---


@pytest.mark.db
async def test_applied_at_set_by_user_action_and_cleared_on_restore(db):
    url = "https://example.com/a"
    await add_new_job(url)
    assert (await get_job_by_url(url))["applied_at"] is None

    await update_user_action(url, "applied")
    assert (await get_job_by_url(url))["applied_at"] is not None

    await update_user_action(url, "none")  # שחזור -> pending
    assert (await get_job_by_url(url))["applied_at"] is None


@pytest.mark.db
async def test_applied_at_kept_when_application_progresses(db, raw_conn):
    url = "https://example.com/b"
    await add_new_job(url)
    await update_application_status(url, ApplicationStatus.APPLIED)
    await raw_conn.execute(
        "UPDATE jobs SET applied_at = '2026-01-01T00:00:00Z' WHERE url = $1", url
    )

    # מעבר לשלב הבא לא "מזיז" את תאריך ההגשה
    await update_application_status(url, ApplicationStatus.INTERVIEW)
    job = await get_job_by_url(url)
    assert job["applied_at"].isoformat().startswith("2026-01-01")

    await update_application_status(url, ApplicationStatus.REJECTED)
    assert (await get_job_by_url(url))["applied_at"].isoformat().startswith("2026-01-01")

    await update_application_status(url, ApplicationStatus.PENDING)
    assert (await get_job_by_url(url))["applied_at"] is None


@pytest.mark.db
async def test_jumping_straight_to_interview_sets_applied_at(db):
    url = "https://example.com/c"
    await add_new_job(url)
    await update_application_status(url, ApplicationStatus.INTERVIEW)
    assert (await get_job_by_url(url))["applied_at"] is not None


# --- הארכוב לפי applied_at ---


@pytest.mark.db
async def test_auto_archive_counts_from_applied_at_not_created_at(db, raw_conn):
    old_job_applied_now = "https://example.com/old-job-applied-yesterday"
    new_job_applied_long_ago = "https://example.com/applied-31-days-ago"
    for url in (old_job_applied_now, new_job_applied_long_ago):
        await add_new_job(url)
        await update_application_status(url, ApplicationStatus.APPLIED)

    # נוספה לפני 60 יום, הוגשה אתמול -> עוד לא ghosted (זה היה הבאג)
    await raw_conn.execute(
        "UPDATE jobs SET created_at = NOW() - INTERVAL '60 days', applied_at = NOW() - INTERVAL '1 day' WHERE url = $1",
        old_job_applied_now,
    )
    # הוגשה לפני 31 יום -> ghosted
    await raw_conn.execute(
        "UPDATE jobs SET applied_at = NOW() - INTERVAL '31 days' WHERE url = $1",
        new_job_applied_long_ago,
    )

    assert await auto_archive_old_applications() == 1

    ghosted = await get_job_by_url(new_job_applied_long_ago)
    assert ghosted["application_status"] == "ghosted"
    assert ghosted["is_archived"] is True  # כמו עדכון ידני ל-ghosted

    assert (await get_job_by_url(old_job_applied_now))["application_status"] == "applied"


@pytest.mark.db
async def test_auto_archive_ignores_later_stages(db, raw_conn):
    url = "https://example.com/interviewing"
    await add_new_job(url)
    await update_application_status(url, ApplicationStatus.INTERVIEW)
    await raw_conn.execute(
        "UPDATE jobs SET applied_at = NOW() - INTERVAL '90 days' WHERE url = $1", url
    )

    assert await auto_archive_old_applications() == 0
    assert (await get_job_by_url(url))["application_status"] == "interview"


# --- migration ---


@pytest.mark.db
async def test_migration_backfills_applied_at_for_existing_applications(empty_db, raw_conn):
    """DB קיים בלי applied_at: הגשות קיימות מקבלות applied_at מ-updated_at, השאר נשארות NULL."""
    await raw_conn.execute(
        """
        CREATE TYPE job_status AS ENUM ('NEW', 'COMPLETED');
        CREATE TABLE jobs (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            status job_status DEFAULT 'NEW',
            company TEXT, job_title TEXT, source TEXT, full_description TEXT,
            analysis_result JSONB, user_action TEXT DEFAULT 'none',
            application_status TEXT DEFAULT 'pending',
            is_archived BOOLEAN DEFAULT FALSE, error_log TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            scraped_at TIMESTAMPTZ, analyzed_at TIMESTAMPTZ
        );
        INSERT INTO jobs (url, application_status, updated_at) VALUES
            ('https://x/applied', 'applied', '2026-03-01T00:00:00Z'),
            ('https://x/interview', 'interview', '2026-04-01T00:00:00Z'),
            ('https://x/pending', 'pending', '2026-05-01T00:00:00Z');
        """
    )

    await postgres.get_pool()

    rows = {
        r["url"]: r["applied_at"]
        for r in await raw_conn.fetch("SELECT url, applied_at FROM jobs")
    }
    assert rows["https://x/applied"].isoformat().startswith("2026-03-01")
    assert rows["https://x/interview"].isoformat().startswith("2026-04-01")
    assert rows["https://x/pending"] is None

    # ריצה שנייה של init לא נוגעת שוב בנתונים
    await raw_conn.execute("UPDATE jobs SET applied_at = NULL WHERE url = 'https://x/applied'")
    pool = await postgres.get_pool()
    async with pool.acquire() as conn:
        await postgres.init_db(conn)
    assert await raw_conn.fetchval("SELECT applied_at FROM jobs WHERE url = 'https://x/applied'") is None


# --- התזמון (בלי DB) ---


async def test_maintenance_worker_runs_at_startup_and_survives_errors(monkeypatch):
    calls = []

    async def fake_archive():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("db down")  # שגיאה בסבב הראשון לא עוצרת את הלולאה
        return 2

    sleeps = []
    real_sleep = asyncio.sleep

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) >= 3:
            raise asyncio.CancelledError
        await real_sleep(0)

    monkeypatch.setattr(worker_manager, "auto_archive_old_applications", fake_archive)
    monkeypatch.setattr(worker_manager.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await worker_manager.maintenance_worker(interval_seconds=123)

    assert len(calls) == 3  # מיד בהפעלה, ואז אחרי כל המתנה
    assert sleeps == [123, 123, 123]


async def test_start_background_workers_schedules_maintenance(monkeypatch):
    started = []

    async def noop(*_args):
        started.append("reset")
        return {}

    def fake_worker(name):
        async def run():
            started.append(name)
        run.__name__ = name
        return run

    monkeypatch.setattr(worker_manager, "reset_stuck_jobs", noop)

    async def no_pending():
        return {}

    monkeypatch.setattr(worker_manager, "pending_retry_times", no_pending)
    for name in ("resolver_worker", "scrape_worker", "ai_worker", "maintenance_worker"):
        monkeypatch.setattr(worker_manager, name, fake_worker(name))

    await worker_manager.start_background_workers()
    await asyncio.gather(*list(worker_manager._background_tasks))

    assert started[0] == "reset"
    assert set(started[1:]) == {"resolver_worker", "scrape_worker", "ai_worker", "maintenance_worker"}
