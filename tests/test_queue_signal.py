"""התעוררות ה-workers: notify מעיר מיד, ובלי עבודה ההמתנה גדלה בהדרגה (במקום sleep(5) קבוע)."""
import asyncio
import time

from datetime import datetime, timedelta, timezone

from workers.queue_signal import DEFAULT_MAX_IDLE_SECONDS, IdleWaiter, notify, notify_at


async def test_notify_wakes_a_waiting_worker_immediately():
    waiter = IdleWaiter("WAITING_FOR_AI", min_seconds=10, max_seconds=10)
    t0 = time.monotonic()
    task = asyncio.create_task(waiter.wait())
    await asyncio.sleep(0.05)
    notify("WAITING_FOR_AI")
    assert await task is True
    assert time.monotonic() - t0 < 1


async def test_notify_for_another_status_does_not_wake():
    waiter = IdleWaiter("PENDING_RESOLVE", min_seconds=0.2, max_seconds=0.2)
    task = asyncio.create_task(waiter.wait())
    await asyncio.sleep(0.05)
    notify("WAITING_FOR_AI")
    assert await task is False  # הסתיים ב-timeout


async def test_idle_wait_grows_and_resets():
    waiter = IdleWaiter("WAITING_FOR_SCRAPE", min_seconds=0.01, max_seconds=0.04)
    delays = []
    for _ in range(4):
        await waiter.wait()
        delays.append(waiter.delay)
    assert delays == [0.02, 0.04, 0.04, 0.04]
    waiter.reset()
    assert waiter.delay == 0.01


async def test_notify_before_wait_is_not_lost():
    """משרה שנוספה בדיוק בין הבדיקה לתחילת ההמתנה - ה-worker לא יפספס אותה."""
    waiter = IdleWaiter("NEW", min_seconds=5, max_seconds=5)
    notify("NEW")
    assert await asyncio.wait_for(waiter.wait(), timeout=1) is True


def test_notify_outside_event_loop_is_harmless():
    notify("WAITING_FOR_AI")


async def test_notify_at_wakes_the_worker_at_the_scheduled_time():
    waiter = IdleWaiter("FAILED_RETRY_TEST", min_seconds=10, max_seconds=10)
    t0 = time.monotonic()
    notify_at("FAILED_RETRY_TEST", datetime.now(timezone.utc) + timedelta(seconds=0.2))
    assert await waiter.wait() is True
    assert 0.15 < time.monotonic() - t0 < 2


def test_idle_polling_is_rare_by_default(monkeypatch):
    """Neon החינמי נרדם רק אחרי 5 דקות בלי שאילתות - בדיקה תקופתית צריכה להיות נדירה בהרבה."""
    monkeypatch.delenv("IDLE_POLL_MAX_SECONDS", raising=False)
    assert IdleWaiter("X").max_seconds == DEFAULT_MAX_IDLE_SECONDS >= 30 * 60
