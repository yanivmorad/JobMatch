"""
הצד המשותף לכל הבוטים (וואטסאפ, טלגרם): הודעה עם קישורים -> משרות בתור + התראה לשולח.

כל ערוץ מטפל רק במה שייחודי לו: אימות ה-webhook, פענוח ההודעה, שליחת טקסט. הלוגיקה,
הטקסטים והרישום להתראה כאן, כדי ששני הבוטים יתנהגו אותו דבר.
"""
from typing import Tuple

from db.jobs_repository import add_job_notification
from services.intake import ingest_text
from services.notifier import NOTIFY_SIGNAL
from workers.queue_signal import notify

HELP_TEXT = "שלח לי הודעה עם קישורים למשרות (אפשר להעביר הודעה מקבוצת משרות), ואחזיר ציון לכל משרה."
ERROR_TEXT = "משהו השתבש בטיפול בהודעה. נסה לשלוח אותה שוב בעוד כמה דקות."

# Meta מאחדת עד 1000 עדכונים ב-webhook אחד, עד 3MB (תיעוד ה-webhooks של Meta). גוף גדול יותר
# לא מגיע מהפלטפורמות, ולא קוראים אותו לזיכרון (נתיב בלי API_TOKEN, ו-512MB ב-Render החינמי).
MAX_BODY_BYTES = 4 * 1024 * 1024


def ack_text(result: dict) -> str:
    added, skipped = result.get("added", 0), result.get("skipped", 0)
    ignored = len(result.get("ignored") or [])
    if not added and not skipped:
        extra = f" (סיננתי {ignored} קישורים שאינם משרות)" if ignored else ""
        return f"לא מצאתי קישורי משרות בהודעה{extra}.\n{HELP_TEXT}"
    parts = []
    if added:
        parts.append(f"קיבלתי {added} משרות חדשות ✅ אשלח ציון לכל אחת כשהניתוח יסתיים.")
    if skipped:
        parts.append(f"{skipped} כבר נסרקו בעבר: אשלח את התוצאה הקיימת.")
    if ignored:
        parts.append(f"סיננתי {ignored} קישורים שאינם משרות.")
    return "\n".join(parts)


async def ingest_for_bot(channel: str, recipient: str, text: str) -> Tuple[str, bool]:
    """
    מכניס את קישורי המשרות שבהודעה לתור ורושם את השולח להתראה על כל משרה (גם על משרות
    שכבר נסרקו בעבר). מחזיר (טקסט האישור, האם נרשמו התראות).
    ה-handler שולח את האישור ורק אז קורא ל-wake_notifier: אחרת ציון של משרה שכבר הסתיימה
    יכול להגיע לפני "אשלח את התוצאה הקיימת".
    """
    result = await ingest_text(text, source=channel)
    job_ids = [j["id"] for j in result.get("added_jobs") or []]
    job_ids += [s["id"] for s in result.get("skipped_urls") or [] if s.get("id")]
    for job_id in job_ids:
        await add_job_notification(job_id, channel, recipient)
    return ack_text(result), bool(job_ids)


def wake_notifier() -> None:
    """משרות שכבר הסתיימו בעבר נשלחות מיד, בלי לחכות לצעד הבא בצינור."""
    notify(NOTIFY_SIGNAL)


def content_too_large(content_length: str) -> bool:
    try:
        return int(content_length or 0) > MAX_BODY_BYTES
    except ValueError:
        return True
