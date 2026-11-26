"""
התראות לבוטים: כשמשרה שנשלחה מבוט מגיעה למצב סופי (ציון / כישלון), שולחים לשולח הודעה.

ערוץ = שורה ב-_CHANNELS: איך טוענים את ההגדרות שלו, איך שולחים, וכמה זמן אחרי ההודעה של
המשתמש עוד שולחים (CHANNEL_WINDOW_HOURS). ערוץ פעיל כשההגדרות שלו קיימות.
"""
import asyncio
import logging
import os
from typing import Callable, Dict, List, NamedTuple

from db.jobs_repository import mark_job_notified, pending_job_notifications
from services import telegram, whatsapp

logger = logging.getLogger("JobMatchServer")

# הסיגנל (queue_signal) שמעיר את notifier_worker: כל צעד בצינור, והודעה חדשה מבוט
NOTIFY_SIGNAL = "NOTIFY"


class _Channel(NamedTuple):
    load_config: Callable[[], object]
    send_text: Callable[[object, str, str], bool]


# וואטסאפ: הודעה חופשית מותרת רק בתוך 24 שעות מההודעה של המשתמש (חלון השירות של Meta).
# טלגרם: אין חלון כזה, אבל ציון שמגיע אחרי יומיים כבר לא שימושי, ושליחה שנכשלת לא תנוסה לנצח.
CHANNEL_WINDOW_HOURS = {whatsapp.CHANNEL: 24, telegram.CHANNEL: 48}

# send_text נקרא דרך המודול בזמן ריצה (ולא נשמר כאן), כדי שבדיקות יוכלו להחליף אותו
_CHANNELS: Dict[str, _Channel] = {
    whatsapp.CHANNEL: _Channel(whatsapp.load_config, lambda c, to, text: whatsapp.send_text(c, to, text)),
    telegram.CHANNEL: _Channel(telegram.load_config, lambda c, to, text: telegram.send_text(c, to, text)),
}


def enabled_channels() -> List[str]:
    return [name for name, channel in _CHANNELS.items() if channel.load_config()]


def _dashboard_url() -> str:
    # Render מגדיר את RENDER_EXTERNAL_URL לשירות web; מקומית אין קישור
    return (os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")


def format_job_message(job: dict) -> str:
    link = job.get("source_url") or job.get("url") or ""
    status = job.get("status")
    if status != "COMPLETED":
        reason = {
            "NO_DATA": "לא נמצא תיאור משרה בדף (אולי המשרה נסגרה)",
            "DUPLICATE": "המשרה כבר נסרקה בעבר",
        }.get(status) or (job.get("error_log") or "הניתוח נכשל")
        return f"⚠️ לא הצלחתי לנתח משרה\n{link}\n{reason[:300]}"

    analysis = job.get("analysis") or {}
    title = job.get("job_title") or analysis.get("job_title") or "משרה"
    company = job.get("company") or analysis.get("company") or ""
    score = analysis.get("suitability_score")
    recommendation = analysis.get("recommendation") or ""
    lines = [f"🎯 {title}" + (f" · {company}" if company else "")]
    if score is not None:
        lines.append(f"ציון התאמה: {score}/100" + (f" · {recommendation}" if recommendation else ""))
    showstoppers = analysis.get("showstoppers") or []
    if isinstance(showstoppers, list) and showstoppers:
        lines.append(f"⛔ {str(showstoppers[0])[:200]}")
    summary = (analysis.get("job_summary_hebrew") or "").strip()
    if summary:
        lines.append(summary[:400])
    lines.append(link)
    dashboard = _dashboard_url()
    if dashboard:
        lines.append(f"בדשבורד: {dashboard}")
    return "\n".join(lines)


async def send_pending_notifications() -> bool:
    """
    שולח את כל ההתראות שמחכות. True אם נשלחה לפחות אחת (כמו step של worker).
    שליחה שנכשלה נשארת בתור ותישלח בסבב הבא (עד שהחלון של הערוץ נסגר).
    """
    sent = False
    for name, channel in _CHANNELS.items():
        config = channel.load_config()
        if config is None:
            continue
        for job in await pending_job_notifications([name], CHANNEL_WINDOW_HOURS[name]):
            text = format_job_message(job)
            ok = await asyncio.to_thread(channel.send_text, config, job["recipient"], text)
            if ok:
                await mark_job_notified(job["job_id"], name, job["recipient"])
                sent = True
            else:
                logger.warning(f"⚠️ Notify [{name}] job {job['job_id']}: send failed, will retry")
    return sent
