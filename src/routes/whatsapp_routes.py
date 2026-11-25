"""
Webhook של WhatsApp Cloud API (מחוץ ל-/api: Meta לא שולחת את API_TOKEN, והאימות הוא חתימה).

GET  /webhooks/whatsapp  אימות חד-פעמי כשמגדירים את ה-webhook ב-App Dashboard
POST /webhooks/whatsapp  הודעות נכנסות. עונים 200 מיד, והעבודה רצה ברקע: Meta שולחת שוב
                         כשלא מקבלת 200, וכפילויות מסוננות לפי id ההודעה (inbound_messages).
כשההגדרות חסרות (services/whatsapp.py) שני הנתיבים מחזירים 404: הבוט כבוי.
"""
import asyncio
import json
import logging
import secrets

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from db.jobs_repository import add_job_notification, claim_inbound_message
from services import whatsapp
from services.intake import ingest_text
from services.notifier import NOTIFY_SIGNAL
from workers.queue_signal import notify

logger = logging.getLogger("JobMatchServer")

router = APIRouter(tags=["whatsapp"])

HELP_TEXT = "שלח לי הודעה עם קישורים למשרות (אפשר להעביר הודעה מקבוצת משרות), ואחזיר ציון לכל משרה."


def _config_or_404() -> whatsapp.WhatsAppConfig:
    config = whatsapp.load_config()
    if config is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return config


@router.get("/whatsapp", response_class=PlainTextResponse)
async def verify_webhook(
    mode: str = Query(default="", alias="hub.mode"),
    token: str = Query(default="", alias="hub.verify_token"),
    challenge: str = Query(default="", alias="hub.challenge"),
):
    config = _config_or_404()
    if mode == "subscribe" and secrets.compare_digest(token.encode(), config.verify_token.encode()):
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


def _ack_text(result: dict) -> str:
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


# סוגים שאינם בקשה מהמשתמש: תגובת אימוג'י (👍 על הודעת ציון), הודעות מערכת. לא עונים עליהם:
# כל תשובה נספרת במכסת הודעות השירות.
SILENT_TYPES = {"reaction", "system", "unsupported"}

# Meta מאחדת עד 1000 עדכונים ב-webhook אחד, עד 3MB (תיעוד ה-webhooks). גוף גדול יותר לא מגיע
# מ-Meta, ולא קוראים אותו לזיכרון (נתיב בלי טוקן, ו-512MB ב-Render החינמי).
MAX_BODY_BYTES = 4 * 1024 * 1024

ERROR_TEXT = "משהו השתבש בטיפול בהודעה. נסה לשלוח אותה שוב בעוד כמה דקות."


async def handle_message(config: whatsapp.WhatsAppConfig, message: whatsapp.IncomingMessage) -> None:
    if message.type in SILENT_TYPES:
        return
    try:
        if message.type != "text" or not message.text.strip():
            await asyncio.to_thread(whatsapp.send_text, config, message.sender, HELP_TEXT)
            return
        result = await ingest_text(message.text, source=whatsapp.CHANNEL)
        job_ids = [j["id"] for j in result.get("added_jobs") or []]
        job_ids += [s["id"] for s in result.get("skipped_urls") or [] if s.get("id")]
        for job_id in job_ids:
            await add_job_notification(job_id, whatsapp.CHANNEL, message.sender)
        await asyncio.to_thread(whatsapp.send_text, config, message.sender, _ack_text(result))
        if job_ids:
            notify(NOTIFY_SIGNAL)  # משרות שכבר הסתיימו בעבר נשלחות מיד
    except Exception:
        # ההודעה כבר סומנה כמטופלת ו-Meta קיבלה 200, ולכן היא לא תגיע שוב: מודיעים למשתמש
        logger.exception(f"❌ WhatsApp: failed to handle message {message.message_id}")
        await asyncio.to_thread(whatsapp.send_text, config, message.sender, ERROR_TEXT)


@router.post("/whatsapp")
async def receive_webhook(request: Request, background: BackgroundTasks):
    config = _config_or_404()
    try:
        too_big = int(request.headers.get("content-length") or 0) > MAX_BODY_BYTES
    except ValueError:
        too_big = True
    if too_big:
        raise HTTPException(status_code=413, detail="Payload too large")
    raw = await request.body()
    if not whatsapp.verify_signature(raw, request.headers.get("x-hub-signature-256"), config.app_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")
    try:
        payload = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    for message in whatsapp.parse_messages(payload):
        if not whatsapp.is_allowed(message, config):
            # לא עונים: לא חושפים שיש כאן בוט, ולא שולחים הודעות (בתשלום) לזרים
            logger.warning("⚠️ WhatsApp: message from a number that is not in WHATSAPP_ALLOWED_NUMBERS")
            continue
        if not await claim_inbound_message(whatsapp.CHANNEL, message.message_id):
            continue  # webhook שנשלח שוב
        background.add_task(handle_message, config, message)
    return {"ok": True}
