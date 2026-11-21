"""התעוררות ה-workers: notify מעיר מיד, ובלי עבודה ההמתנה גדלה בהדרגה (במקום sleep(5) קבוע)."""
import asyncio
import time

from workers.queue_signal import IdleWaiter, notify


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
