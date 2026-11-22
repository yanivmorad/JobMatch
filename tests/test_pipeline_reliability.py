"""
שלב 5: אמינות הצינור מול DB אמיתי - משרה לא מטופלת פעמיים, ניסיונות חוזרים מוגבלים,
קריסה באמצע נספרת, 429 מחזיר לתור בלי כישלון, ו-worker שורד שגיאת DB.
"""
import asyncio
from datetime import datetime, timezone

import pytest

from db.jobs_repository import (
    add_new_job,
    fail_or_retry,
    fetch_next_job,
    get_job_by_url,
    queue_snapshot,
    requeue_in_progress,
    reset_stuck_jobs,
    retry_job,
)
from db.postgres import get_pool
from engine import RateLimitError, TransientAIError
from workers import worker_manager
from workers.rate_limiter import AIRateLimiter, ModelPool

pytestmark = pytest.mark.db

VALID = {
    "company": "Acme", "job_title": "Analyst", "suitability_score": 80, "acceptance_probability": 60,
    "job_summary_hebrew": "x", "showstoppers": [], "gap_analysis": [], "recommendation": "להגיש",
    "formatted_message": "x", "url": None,
}


async def _set(url, **fields):
    pool = await get_pool()
    sets = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
    await pool.execute(f"UPDATE jobs SET {sets} WHERE url = $1", url, *fields.values())


async def test_no_job_is_taken_twice_under_concurrency(db):
    """30 משרות, 10 'workers' במקביל: כל משרה נלקחת בדיוק פעם אחת (FOR UPDATE SKIP LOCKED)."""
    for i in range(30):
        await add_new_job(f"https://jobs.example/{i}")

    async def worker():
        taken = []
        while job := await fetch_next_job("PENDING_RESOLVE", "RESOLVING"):
            taken.append(job["id"])
        return taken

    results = await asyncio.gather(*(worker() for _ in range(10)))
    ids = [i for r in results for i in r]
    assert len(ids) == 30 and len(set(ids)) == 30


async def test_transient_failure_is_retried_with_backoff_then_fails(db):
    url = "https://jobs.example/flaky"
    await add_new_job(url)
    job = await get_job_by_url(url)

    assert await fail_or_retry(job["id"], "PENDING_RESOLVE", "FAILED_RESOLVE", "boom", max_attempts=3) == "PENDING_RESOLVE"
    row = await get_job_by_url(url)
    assert row["retry_count"] == 1 and "ניסיון 1/3" in row["error_log"]
    assert row["not_before"] > datetime.now(timezone.utc)  # backoff
    assert await fetch_next_job("PENDING_RESOLVE", "RESOLVING") is None  # לא נלקחת לפני הזמן

    assert await fail_or_retry(job["id"], "PENDING_RESOLVE", "FAILED_RESOLVE", "boom", max_attempts=3) == "PENDING_RESOLVE"
    assert await fail_or_retry(job["id"], "PENDING_RESOLVE", "FAILED_RESOLVE", "boom", max_attempts=3) == "FAILED_RESOLVE"
    row = await get_job_by_url(url)
    assert row["retry_count"] == 3 and row["error_log"] == "boom" and row["not_before"] is None


async def test_manual_retry_resets_the_attempt_counter(db):
    url = "https://jobs.example/failed"
    await add_new_job(url)
    await _set(url, status="FAILED_SCRAPE", retry_count=3)
    assert await retry_job(url) == "WAITING_FOR_SCRAPE"
    row = await get_job_by_url(url)
    assert row["retry_count"] == 0 and row["not_before"] is None


async def test_restart_mid_work_requeues_and_counts_the_crash(db):
    """reset_stuck_jobs אחרי הפעלה מחדש: חוזרות לתור; משרה שהפילה את השרת 3 פעמים - נכשלת."""
    for name, status, count in (("a", "RESOLVING", 0), ("b", "SCRAPING", 1), ("c", "ANALYZING", 2)):
        await add_new_job(f"https://jobs.example/{name}")
        await _set(f"https://jobs.example/{name}", status=status, retry_count=count)

    counts = await reset_stuck_jobs(max_attempts=3)

    assert (await get_job_by_url("https://jobs.example/a"))["status"] == "PENDING_RESOLVE"
    assert (await get_job_by_url("https://jobs.example/b"))["status"] == "WAITING_FOR_SCRAPE"
    crashed = await get_job_by_url("https://jobs.example/c")
    assert crashed["status"] == "FAILED_ANALYSIS" and "השרת הופעל מחדש" in crashed["error_log"]
    assert counts == {"PENDING_RESOLVE": 1, "WAITING_FOR_SCRAPE": 1, "FAILED_ANALYSIS": 1}


async def test_graceful_shutdown_requeues_without_counting(db):
    await add_new_job("https://jobs.example/s")
    await _set("https://jobs.example/s", status="SCRAPING")
    assert await requeue_in_progress() == 1
    row = await get_job_by_url("https://jobs.example/s")
    assert row["status"] == "WAITING_FOR_SCRAPE" and row["retry_count"] == 0


# --- ai worker ---


class _Analyzer:
    model_name = "gemini-test"

    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = 0

    def analyze(self, resume, context, job):
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return {**self.outcome, "url": job["url"]}


def _limiter():
    return AIRateLimiter("gemini-test", rpm=0, rpd=0)


def _pool(analyzer, limiter=None):
    return ModelPool([(analyzer, limiter or _limiter())])


async def _ai_job(url="https://jobs.example/ai"):
    from services.profile_service import set_profile

    await set_profile("resume", "Full Stack Developer: React, Python, SQL")
    await add_new_job(url, manual_text="Requirements: SQL. Experience: 2 years.")
    return url


async def test_429_puts_the_job_back_without_failing_it(db):
    url = await _ai_job()
    limiter = _limiter()
    err = RateLimitError("429", retry_after=30, quota_ids=["GenerateRequestsPerMinutePerProjectPerModel-FreeTier"])

    assert await worker_manager.analyze_next(_pool(_Analyzer(err), limiter)) is True

    row = await get_job_by_url(url)
    assert row["status"] == "WAITING_FOR_AI"  # לא FAILED_ANALYSIS
    assert row["retry_count"] == 0  # 429 לא נספר כניסיון
    assert limiter.paused_until is not None


async def test_transient_ai_error_is_retried_then_success_clears_the_note(db):
    url = await _ai_job()
    await worker_manager.analyze_next(_pool(_Analyzer(TransientAIError("Gemini HTTP 503"))))
    row = await get_job_by_url(url)
    assert row["status"] == "WAITING_FOR_AI" and row["retry_count"] == 1
    assert "מנסה שוב" in row["error_log"]

    await _set(url, not_before=None)  # בלי לחכות ל-backoff
    await worker_manager.analyze_next(_pool(_Analyzer(VALID)))
    row = await get_job_by_url(url)
    assert row["status"] == "COMPLETED" and row["error_log"] is None


async def test_other_notes_survive_a_successful_analysis(db):
    url = await _ai_job()
    await _set(url, error_log="HireMeTech: הטוקן פג (נותח לפי הדף הציבורי, בלי שם החברה)")
    await worker_manager.analyze_next(_pool(_Analyzer(VALID)))
    assert "הטוקן פג" in (await get_job_by_url(url))["error_log"]


async def test_ai_requests_are_counted_per_pacific_day(db):
    await _ai_job()
    from db.jobs_repository import get_api_usage, increment_api_usage

    limiter = AIRateLimiter("gemini-test", rpm=0, rpd=0, get_usage=get_api_usage, add_usage=increment_api_usage)
    await worker_manager.analyze_next(_pool(_Analyzer(VALID), limiter))
    assert limiter.status()["requests_today"] == 1
    assert await get_api_usage(limiter._day, "gemini-test") == 1


async def test_loop_survives_a_db_error(monkeypatch):
    calls = []

    async def step():
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionError("db down")
        raise asyncio.CancelledError

    async def no_sleep(_):
        pass

    monkeypatch.setattr(worker_manager.asyncio, "sleep", no_sleep)
    with pytest.raises(asyncio.CancelledError):
        await worker_manager._run_loop("test_worker", "NEW", step)
    assert len(calls) == 2  # המשיך אחרי השגיאה
    assert "db down" in worker_manager._state["test_worker"]["last_error"]


async def test_queue_snapshot_version_changes_on_updates(db):
    url = await _ai_job()
    first = await queue_snapshot()
    assert first["counts"] == {"WAITING_FOR_AI": 1}
    await asyncio.sleep(0.01)
    await _set(url, status="COMPLETED")
    second = await queue_snapshot()
    assert second["counts"] == {"COMPLETED": 1}
    assert second["version"] != first["version"]


async def test_missing_resume_fails_with_a_clear_message_without_calling_the_ai(db, monkeypatch):
    from services import profile_service

    monkeypatch.setattr(profile_service, "_initial_content", lambda key: None)  # אין קובץ / env
    url = "https://jobs.example/no-cv"
    await add_new_job(url, manual_text="Requirements: SQL. Experience: 2 years.")
    analyzer = _Analyzer(VALID)
    await worker_manager.analyze_next(_pool(analyzer))
    row = await get_job_by_url(url)
    assert analyzer.calls == 0
    assert "אין קורות חיים" in row["error_log"]


async def test_removed_model_is_disabled_and_the_next_model_takes_the_job(db):
    from engine import ModelUnavailableError

    url = await _ai_job()
    gone = _Analyzer(ModelUnavailableError("gemini-old: HTTP 404"))
    gone.model_name = "gemini-old"
    good = _Analyzer(VALID)
    pool = ModelPool([(gone, AIRateLimiter("gemini-old", rpm=0, rpd=0)), (good, _limiter())])

    await worker_manager.analyze_next(pool)  # המודל הראשון מחזיר 404
    row = await get_job_by_url(url)
    assert row["status"] == "WAITING_FOR_AI" and row["retry_count"] == 0  # לא נספר ככישלון
    assert pool.members[0][1].available_at() is not None  # המודל מושבת

    await worker_manager.analyze_next(pool)  # עובר למודל הבא
    assert (await get_job_by_url(url))["status"] == "COMPLETED"
    assert gone.calls == 1 and good.calls == 1


def test_ai_availability_reports_only_when_every_model_is_paused(monkeypatch):
    a, b = _limiter(), _limiter()
    monkeypatch.setattr(worker_manager, "ai_pool", ModelPool([(_Analyzer(VALID), a), (_Analyzer(VALID), b)]))
    assert worker_manager.ai_availability()["paused_until"] is None

    a.disable_for(3600, "daily quota")
    assert worker_manager.ai_availability()["paused_until"] is None  # b עדיין זמין

    b.disable_for(600, "Gemini 429")
    status = worker_manager.ai_availability()
    assert status["paused_until"] == b.paused_until.isoformat()  # הראשון שמתפנה
    assert status["reason"] == "Gemini 429"
