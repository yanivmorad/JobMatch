"""
התראות לבוטים: כשמשרה שנשלחה מבוט מגיעה למצב סופי (ציון / כישלון), שולחים לשולח הודעה.

השולחים רשומים ב-_SENDERS לפי ערוץ. ערוץ חדש (למשל טלגרם) = פונקציה (recipient, text) -> bool
ושורה ב-_SENDERS, ו-enabled_channels יחזיר אותו כשההגדרות שלו קיימות.
"""
import asyncio
import logging
import os
from typing import Callable, Dict, List

from db.jobs_repository import mark_job_notified, pending_job_notifications
from services import whatsapp

logger = logging.getLogger("JobMatchServer")

# הסיגנל (queue_signal) שמעיר את notifier_worker: כל צעד בצינור, והודעה חדשה מבוט
NOTIFY_SIGNAL = "NOTIFY"


def _send_whatsapp(recipient: str, text: str) -> bool:
    config = whatsapp.load_config()
    return bool(config) and whatsapp.send_text(config, recipient, text)


_SENDERS: Dict[str, Callable[[str, str], bool]] = {whatsapp.CHANNEL: _send_whatsapp}


def enabled_channels() -> List[str]:
    return [whatsapp.CHANNEL] if whatsapp.load_config() else []


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
    שליחה שנכשלה נשארת בתור ותישלח בסבב הבא.
    """
    channels = enabled_channels()
    if not channels:
        return False
    sent = False
    for job in await pending_job_notifications(channels):
        sender = _SENDERS.get(job["channel"])
        if sender is None:
            continue
        text = format_job_message(job)
        ok = await asyncio.to_thread(sender, job["recipient"], text)
        if ok:
            await mark_job_notified(job["job_id"], job["channel"], job["recipient"])
            sent = True
        else:
            logger.warning(f"⚠️ Notify [{job['channel']}] job {job['job_id']}: send failed, will retry")
    return sent
