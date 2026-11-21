"""
קצב הבקשות ל-Gemini (תוכנית חינמית).

המגבלות החינמיות לכל מודל לא מפורסמות בתיעוד (הוא מפנה ל-AI Studio), ומשתנות. לכן:
- GEMINI_RPM (ברירת מחדל 10): מרווח מינימלי בין בקשות = 60/RPM שניות.
- GEMINI_RPD (ברירת מחדל 0 = בלי תקרה מקומית): תקרה יומית. נספרת ב-DB (api_usage),
  לפי יום בשעון פסיפיק - בדיוק כמו איפוס המכסה של Gemini - כך ששורדת הפעלה מחדש.
- 429: ה-worker מחזיר את המשרה לתור (לא נכשלת) ומחכה:
    * מכסה יומית (quotaId ...PerDay...) -> עד חצות פסיפיק.
    * אחרת -> max(retryDelay של Gemini, backoff אקספוננציאלי), עד 15 דקות.
  ערכי המכסה שהגיעו ב-429 נשמרים ב-status() (ומוצגים ב-/health), כך שרואים את המגבלה האמיתית.
"""
import asyncio
import logging
import os
from datetime import date, datetime, time, timedelta, timezone
from typing import Awaitable, Callable, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger("RateLimiter")

PACIFIC = ZoneInfo("America/Los_Angeles")
BASE_BACKOFF_SECONDS = 10
MAX_BACKOFF_SECONDS = 15 * 60


def _env_int(name: str, default: int) -> int:
    try:
        return int((os.getenv(name) or "").strip() or default)
    except ValueError:
        logger.warning(f"Invalid {name}={os.getenv(name)!r}, using {default}")
        return default


def pacific_day(now: datetime) -> date:
    return now.astimezone(PACIFIC).date()


def next_pacific_midnight(now: datetime) -> datetime:
    tomorrow = pacific_day(now) + timedelta(days=1)
    # 5 שניות אחרי חצות - שלא נגיע רגע לפני האיפוס
    return datetime.combine(tomorrow, time(0, 0, 5), PACIFIC).astimezone(timezone.utc)


class AIRateLimiter:
    def __init__(
        self,
        model: str,
        rpm: Optional[int] = None,
        rpd: Optional[int] = None,
        get_usage: Optional[Callable[[date, str], Awaitable[int]]] = None,
        add_usage: Optional[Callable[[date, str], Awaitable[int]]] = None,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.model = model
        self.rpm = _env_int("GEMINI_RPM", 10) if rpm is None else rpm
        self.rpd = _env_int("GEMINI_RPD", 0) if rpd is None else rpd
        self.min_interval = 60.0 / self.rpm if self.rpm > 0 else 0.0
        self._get_usage = get_usage
        self._add_usage = add_usage
        self._now = now
        self._sleep = sleep

        self._last_request_at: Optional[datetime] = None
        self._day: Optional[date] = None
        self._day_count = 0
        self.paused_until: Optional[datetime] = None
        self.pause_reason: Optional[str] = None
        self.consecutive_429 = 0
        self.last_rate_limit: Optional[dict] = None

    async def _requests_today(self) -> int:
        day = pacific_day(self._now())
        if day != self._day:
            self._day = day
            self._day_count = await self._get_usage(day, self.model) if self._get_usage else 0
        return self._day_count

    async def wait_until_allowed(self) -> None:
        """מחכה עד שמותר לשלוח בקשה (הפסקה אחרי 429 / תקרה יומית / מרווח RPM)."""
        while True:
            now = self._now()
            if self.paused_until and now < self.paused_until:
                await self._sleep((self.paused_until - now).total_seconds())
                continue
            if self.paused_until:
                logger.info("▶️ AI rate limit pause is over")
                self.paused_until = self.pause_reason = None
            if self.rpd and await self._requests_today() >= self.rpd:
                self._pause(next_pacific_midnight(now), f"GEMINI_RPD={self.rpd} reached")
                continue
            if self._last_request_at and self.min_interval:
                wait = self.min_interval - (now - self._last_request_at).total_seconds()
                if wait > 0:
                    await self._sleep(wait)
                    continue
            return

    async def record_request(self) -> None:
        """נקרא רגע לפני שליחת בקשה."""
        self._last_request_at = self._now()
        await self._requests_today()
        self._day_count += 1
        if self._add_usage:
            try:
                self._day_count = await self._add_usage(self._day, self.model)
            except Exception as e:  # ספירה ב-DB היא עזר; לא עוצרים בגללה את הניתוח
                logger.warning(f"Could not persist API usage: {e}")

    def on_success(self) -> None:
        self.consecutive_429 = 0

    def on_rate_limited(self, err) -> datetime:
        """429: מחשב עד מתי להמתין. מחזיר את הזמן."""
        now = self._now()
        self.consecutive_429 += 1
        self.last_rate_limit = {
            "at": now.isoformat(),
            "quota_ids": getattr(err, "quota_ids", []),
            "quota_values": getattr(err, "quota_values", []),
            "retry_after": getattr(err, "retry_after", None),
        }
        if getattr(err, "per_day", False):
            until, reason = next_pacific_midnight(now), "Gemini daily quota exhausted"
        else:
            backoff = min(BASE_BACKOFF_SECONDS * 2 ** (self.consecutive_429 - 1), MAX_BACKOFF_SECONDS)
            delay = max(getattr(err, "retry_after", None) or 0, backoff)
            until, reason = now + timedelta(seconds=min(delay, MAX_BACKOFF_SECONDS)), "Gemini 429"
        self._pause(until, reason)
        return self.paused_until

    def _pause(self, until: datetime, reason: str) -> None:
        if not self.paused_until or until > self.paused_until:
            self.paused_until, self.pause_reason = until, reason
            logger.warning(f"⏸️ AI paused until {until.isoformat()} ({reason})")

    def status(self) -> dict:
        return {
            "model": self.model,
            "rpm_limit": self.rpm,
            "rpd_limit": self.rpd or None,
            "requests_today": self._day_count if self._day == pacific_day(self._now()) else None,
            "day_pacific": str(self._day) if self._day else None,
            "paused_until": self.paused_until.isoformat() if self.paused_until else None,
            "pause_reason": self.pause_reason,
            "last_rate_limit": self.last_rate_limit,
        }
