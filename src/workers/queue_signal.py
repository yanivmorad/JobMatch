"""
התעוררות ה-workers: במקום sleep(5) קבוע כשהתור ריק (3 workers x שאילתה כל 5 שניות = DB
שלא נרדם לעולם, וגם השהיה של עד 5 שניות עד שמשרה חדשה נלקחת):

- notify(status): ה-API (הוספת משרה / ניסיון חוזר) וה-worker הקודם בצינור מעירים מיד
  את ה-worker שמטפל בסטטוס הזה (הכל באותו תהליך).
- IdleWaiter: כשאין עבודה, ממתין עד notify או עד timeout שגדל בהדרגה 1, 2, 4... עד
  IDLE_POLL_MAX_SECONDS (ברירת מחדל 60). הבדיקה התקופתית נשארת בשביל ניסיונות מתוזמנים
  (not_before) ומשרות שהוכנסו מבחוץ.
"""
import asyncio
import os
from typing import Dict, Tuple


def _max_idle() -> float:
    try:
        return float(os.getenv("IDLE_POLL_MAX_SECONDS") or 60)
    except ValueError:
        return 60.0


# Event לכל (event loop, סטטוס): Event של asyncio קשור ללולאה שבה חיכו לו לראשונה
_events: Dict[Tuple[int, str], asyncio.Event] = {}


def _event(status: str) -> asyncio.Event:
    key = (id(asyncio.get_running_loop()), status)
    if key not in _events:
        _events[key] = asyncio.Event()
    return _events[key]


def notify(*statuses: str) -> None:
    """מעיר את ה-workers של הסטטוסים האלה (בטוח לקרוא גם כשאף אחד לא מחכה)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    for status in statuses:
        _event(status).set()


class IdleWaiter:
    def __init__(self, status: str, min_seconds: float = 1.0, max_seconds: float = None):
        self.status = status
        self.min_seconds = min_seconds
        self.max_seconds = max_seconds if max_seconds is not None else _max_idle()
        self.delay = min_seconds

    def reset(self) -> None:
        self.delay = self.min_seconds

    async def wait(self) -> bool:
        """True אם הוער ע"י notify, False אם עבר הזמן."""
        event = _event(self.status)
        try:
            await asyncio.wait_for(event.wait(), timeout=self.delay)
            woken = True
        except asyncio.TimeoutError:
            woken = False
        event.clear()
        self.delay = self.min_seconds if woken else min(self.delay * 2, self.max_seconds)
        return woken
