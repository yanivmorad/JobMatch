"""קצב הבקשות ל-Gemini: מרווח RPM, תקרה יומית, והמתנה אחרי 429 (שעון מזויף, בלי המתנות אמיתיות)."""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from workers.rate_limiter import (
    MAX_BACKOFF_SECONDS,
    AIRateLimiter,
    next_pacific_midnight,
    pacific_day,
)


class FakeClock:
    def __init__(self, start: datetime):
        self.now = start
        self.sleeps = []

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.sleeps.append(round(seconds, 3))
        self.now += timedelta(seconds=seconds)


START = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)  # 02:00 שעון פסיפיק (PST)


def _limiter(clock, **kw):
    return AIRateLimiter("gemini-test", now=clock, sleep=clock.sleep, **kw)


def test_pacific_midnight():
    assert pacific_day(START) == date(2026, 11, 22)
    # חצות PST = 08:00 UTC
    assert next_pacific_midnight(START) == datetime(2026, 11, 23, 8, 0, 5, tzinfo=timezone.utc)
    # שעון קיץ (PDT, UTC-7): חצות = 07:00 UTC
    summer = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    assert next_pacific_midnight(summer) == datetime(2026, 7, 2, 7, 0, 5, tzinfo=timezone.utc)


async def test_rpm_spacing():
    clock = FakeClock(START)
    limiter = _limiter(clock, rpm=10, rpd=0)
    for _ in range(3):
        await limiter.wait_until_allowed()
        await limiter.record_request()
    assert clock.sleeps == [6.0, 6.0]  # 60/10 שניות בין בקשות
    assert clock.now - START == timedelta(seconds=12)


async def test_no_wait_when_requests_are_already_spaced():
    clock = FakeClock(START)
    limiter = _limiter(clock, rpm=10, rpd=0)
    await limiter.wait_until_allowed()
    await limiter.record_request()
    clock.now += timedelta(seconds=30)  # הניתוח עצמו לקח 30 שניות
    await limiter.wait_until_allowed()
    assert clock.sleeps == []


async def test_daily_cap_counts_from_the_db_and_pauses_until_pacific_midnight():
    clock = FakeClock(START)
    store = {}

    async def get_usage(day, model):
        return store.get((day, model), 0)

    async def add_usage(day, model):
        store[(day, model)] = store.get((day, model), 0) + 1
        return store[(day, model)]

    store[(date(2026, 11, 22), "gemini-test")] = 4  # 4 בקשות היום, לפני הפעלה מחדש
    limiter = _limiter(clock, rpm=0, rpd=5, get_usage=get_usage, add_usage=add_usage)

    await limiter.wait_until_allowed()
    await limiter.record_request()  # הבקשה ה-5
    assert limiter.status()["requests_today"] == 5

    await limiter.wait_until_allowed()  # השישית מחכה ליום הבא
    assert clock.now >= datetime(2026, 11, 23, 8, 0, 5, tzinfo=timezone.utc)
    assert limiter.status()["requests_today"] == 0 or limiter._day == date(2026, 11, 23)


def _err(per_day=False, retry_after=None):
    return SimpleNamespace(per_day=per_day, retry_after=retry_after, quota_ids=["q"], quota_values=["20"])


def test_429_daily_quota_pauses_until_midnight():
    clock = FakeClock(START)
    limiter = _limiter(clock, rpm=10, rpd=0)
    until = limiter.on_rate_limited(_err(per_day=True, retry_after=30))
    assert until == next_pacific_midnight(START)
    assert limiter.status()["last_rate_limit"]["quota_values"] == ["20"]


def test_429_backoff_respects_retry_after_and_grows_exponentially():
    clock = FakeClock(START)
    limiter = _limiter(clock, rpm=10, rpd=0)
    assert limiter.on_rate_limited(_err(retry_after=45)) == START + timedelta(seconds=45)
    limiter.paused_until = None
    # בלי retry_after: 10, 20, 40...
    assert limiter.on_rate_limited(_err()) == START + timedelta(seconds=20)
    limiter.paused_until = None
    assert limiter.on_rate_limited(_err()) == START + timedelta(seconds=40)
    limiter.on_success()
    limiter.paused_until = None
    assert limiter.on_rate_limited(_err()) == START + timedelta(seconds=10)


def test_429_backoff_is_capped():
    clock = FakeClock(START)
    limiter = _limiter(clock, rpm=10, rpd=0)
    for _ in range(20):
        limiter.paused_until = None
        until = limiter.on_rate_limited(_err(retry_after=10_000))
    assert until == START + timedelta(seconds=MAX_BACKOFF_SECONDS)


async def test_wait_until_allowed_sleeps_through_a_pause():
    clock = FakeClock(START)
    limiter = _limiter(clock, rpm=0, rpd=0)
    limiter.on_rate_limited(_err(retry_after=90))
    await limiter.wait_until_allowed()
    assert clock.now == START + timedelta(seconds=90)
    assert limiter.status()["paused_until"] is None


# --- שרשרת מודלים ---

from workers.rate_limiter import ModelPool  # noqa: E402


def _pool(clock, *names):
    members = [(SimpleNamespace(model_name=n), _limiter(clock, rpm=0, rpd=0)) for n in names]
    for (analyzer, limiter) in members:
        limiter.model = analyzer.model_name
    return ModelPool(members, now=clock, sleep=clock.sleep)


async def test_pool_uses_the_first_model_while_it_is_available():
    clock = FakeClock(START)
    pool = _pool(clock, "a", "b")
    analyzer, _ = await pool.acquire()
    assert analyzer.model_name == "a"


async def test_pool_moves_to_the_next_model_when_the_daily_quota_is_hit_and_comes_back():
    clock = FakeClock(START)
    pool = _pool(clock, "a", "b")
    pool.members[0][1].on_rate_limited(_err(per_day=True))

    analyzer, _ = await pool.acquire()
    assert analyzer.model_name == "b"
    assert clock.sleeps == []  # לא חיכה - עבר מיד למודל הבא

    clock.now = next_pacific_midnight(START)  # אחרי האיפוס - חוזרים למודל הראשון
    analyzer, _ = await pool.acquire()
    assert analyzer.model_name == "a"


async def test_pool_waits_when_every_model_is_paused():
    clock = FakeClock(START)
    pool = _pool(clock, "a", "b")
    pool.members[0][1].on_rate_limited(_err(retry_after=120))
    pool.members[1][1].on_rate_limited(_err(retry_after=60))

    analyzer, _ = await pool.acquire()
    assert analyzer.model_name == "b"  # זה שמתפנה ראשון
    assert clock.now - START == timedelta(seconds=60)


async def test_pool_respects_a_local_daily_cap_per_model():
    clock = FakeClock(START)
    pool = _pool(clock, "a", "b")
    pool.members[0][1].rpd = 1
    first, limiter = await pool.acquire()
    await limiter.record_request()
    second, _ = await pool.acquire()
    assert (first.model_name, second.model_name) == ("a", "b")


@pytest.mark.parametrize("value, expected", [("", 10), ("abc", 10), ("30", 30)])
def test_rpm_from_env(monkeypatch, value, expected):
    monkeypatch.setenv("GEMINI_RPM", value)
    assert AIRateLimiter("m").rpm == expected
