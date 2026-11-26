"""
Webhook של Telegram Bot API (מחוץ ל-/api: Telegram לא שולחת את API_TOKEN, והאימות הוא סוד
בכותרת X-Telegram-Bot-Api-Secret-Token).

POST /webhooks/telegram  עדכון אחד בכל בקשה. עונים 200 מיד והעבודה רצה ברקע. Telegram שולחת
                         שוב כשלא מקבלת 2XX, וכפילויות מסוננות לפי update_id (inbound_messages).
בלי TELEGRAM_BOT_TOKEN הנתיב מחזיר 404: הבוט כבוי. הלוגיקה המשותפת: services/bot_intake.py.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from db.jobs_repository import claim_inbound_message
from services import telegram
from services.bot_intake import (
    ERROR_TEXT,
    HELP_TEXT,
    content_too_large,
    ingest_for_bot,
    wake_notifier,
)

logger = logging.getLogger("JobMatchServer")

router = APIRouter(tags=["telegram"])

WELCOME_TEXT = "היי 👋 " + HELP_TEXT


def id_text(chat_id: str) -> str:
    return (
        f"ה-chat id שלך: {chat_id}\n"
        "כדי להשתמש בבוט, הוסף אותו ב-Render למשתנה TELEGRAM_ALLOWED_CHAT_IDS ופרוס מחדש."
    )


def _command(text: str) -> str:
    """'/start@MyBot arg' -> '/start'. טקסט שאינו פקודה -> ''."""
    first = (text.strip().split() or [""])[0]
    return first.split("@")[0].lower() if first.startswith("/") else ""


async def handle_message(config: telegram.TelegramConfig, message: telegram.IncomingMessage) -> None:
    command = _command(message.text)
    try:
        has_jobs = False
        if command == "/id":
            reply = id_text(message.chat_id)
        elif command in ("/start", "/help"):
            reply = WELCOME_TEXT
        elif not message.text.strip():
            reply = HELP_TEXT
        else:
            reply, has_jobs = await ingest_for_bot(telegram.CHANNEL, message.chat_id, message.text)
        await asyncio.to_thread(telegram.send_text, config, message.chat_id, reply)
        if has_jobs:
            wake_notifier()  # אחרי האישור, כדי שהציון לא יקדים אותו
    except Exception:
        # העדכון כבר סומן כמטופל ו-Telegram קיבלה 200, ולכן הוא לא יגיע שוב: מודיעים למשתמש
        logger.exception(f"❌ Telegram: failed to handle update {message.update_id}")
        await asyncio.to_thread(telegram.send_text, config, message.chat_id, ERROR_TEXT)


async def _send_quietly(config: telegram.TelegramConfig, chat_id: str, text: str) -> None:
    try:
        await asyncio.to_thread(telegram.send_text, config, chat_id, text)
    except Exception:
        logger.exception("❌ Telegram: send failed")


@router.post("/telegram")
async def receive_webhook(request: Request, background: BackgroundTasks):
    config = telegram.load_config()
    if config is None:
        raise HTTPException(status_code=404, detail="Not Found")
    if not telegram.verify_secret(request.headers.get("x-telegram-bot-api-secret-token"), config):
        raise HTTPException(status_code=401, detail="Invalid secret")
    if content_too_large(request.headers.get("content-length")):
        raise HTTPException(status_code=413, detail="Payload too large")
    try:
        update = json.loads(await request.body())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    message = telegram.parse_update(update)
    if message is None:
        return {"ok": True}
    if not telegram.is_allowed(message, config):
        # מצב הקמה (הרשימה ריקה): /id מחזיר לשולח את ה-chat id שלו, ברקע (לא בתוך הבקשה, כדי
        # שטלגרם לא תשלח שוב בגלל המתנה). אחרי שהרשימה מולאה, הבוט שותק לזרים לגמרי.
        if not config.allowed_chat_ids and _command(message.text) == "/id":
            background.add_task(_send_quietly, config, message.chat_id, id_text(message.chat_id))
        else:
            logger.warning("⚠️ Telegram: message from a chat that is not in TELEGRAM_ALLOWED_CHAT_IDS")
        return {"ok": True}
    if not await claim_inbound_message(telegram.CHANNEL, message.update_id):
        return {"ok": True}  # עדכון שנשלח שוב
    background.add_task(handle_message, config, message)
    return {"ok": True}
