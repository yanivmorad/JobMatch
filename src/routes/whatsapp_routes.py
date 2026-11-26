"""
Webhook של WhatsApp Cloud API (מחוץ ל-/api: Meta לא שולחת את API_TOKEN, והאימות הוא חתימה).

GET  /webhooks/whatsapp  אימות חד-פעמי כשמגדירים את ה-webhook ב-App Dashboard
POST /webhooks/whatsapp  הודעות נכנסות. עונים 200 מיד, והעבודה רצה ברקע: Meta שולחת שוב
                         כשלא מקבלת 200, וכפילויות מסוננות לפי id ההודעה (inbound_messages).
כשההגדרות חסרות (services/whatsapp.py) שני הנתיבים מחזירים 404: הבוט כבוי.
הלוגיקה המשותפת לכל הבוטים: services/bot_intake.py.
"""
import asyncio
import json
import logging
import secrets

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from db.jobs_repository import claim_inbound_message
from services import whatsapp
from services.bot_intake import (
    ERROR_TEXT,
    HELP_TEXT,
    content_too_large,
    ingest_for_bot,
    wake_notifier,
)

logger = logging.getLogger("JobMatchServer")

router = APIRouter(tags=["whatsapp"])

# סוגים שאינם בקשה מהמשתמש: תגובת אימוג'י (👍 על הודעת ציון), הודעות מערכת. לא עונים עליהם:
# כל תשובה נספרת במכסת הודעות השירות.
SILENT_TYPES = {"reaction", "system", "unsupported"}


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


async def handle_message(config: whatsapp.WhatsAppConfig, message: whatsapp.IncomingMessage) -> None:
    if message.type in SILENT_TYPES:
        return
    try:
        has_jobs = False
        if message.type != "text" or not message.text.strip():
            reply = HELP_TEXT
        else:
            reply, has_jobs = await ingest_for_bot(whatsapp.CHANNEL, message.sender, message.text)
        await asyncio.to_thread(whatsapp.send_text, config, message.sender, reply)
        if has_jobs:
            wake_notifier()  # אחרי האישור, כדי שהציון לא יקדים אותו
    except Exception:
        # ההודעה כבר סומנה כמטופלת ו-Meta קיבלה 200, ולכן היא לא תגיע שוב: מודיעים למשתמש
        logger.exception(f"❌ WhatsApp: failed to handle message {message.message_id}")
        await asyncio.to_thread(whatsapp.send_text, config, message.sender, ERROR_TEXT)


@router.post("/whatsapp")
async def receive_webhook(request: Request, background: BackgroundTasks):
    config = _config_or_404()
    if content_too_large(request.headers.get("content-length")):
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
