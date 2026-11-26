"""
בוט טלגרם דרך Telegram Bot API: שולחים לבוט הודעה עם קישורי משרות, והשרת מקבל אותה ב-webhook,
מכניס את המשרות לתור ושולח ציון לכל אחת.

  TELEGRAM_BOT_TOKEN          הטוקן מ-@BotFather. בלעדיו הבוט כבוי (ה-webhook מחזיר 404).
  TELEGRAM_ALLOWED_CHAT_IDS   ה-chat id שמותר להם להשתמש בבוט, מופרדים בפסיקים. עד שממלאים
                              אותו, הבוט עונה רק על /id (מחזיר לשולח את ה-chat id שלו).

סוד ה-webhook נגזר מהטוקן (אין משתנה נוסף למלא): Telegram שולחת אותו בכל בקשה בכותרת
X-Telegram-Bot-Api-Secret-Token, ומי שלא יודע את הטוקן לא יכול לחשב אותו.
ה-webhook נרשם בכל הפעלה (register_webhook) לכתובת ש-Render מגדיר ב-RENDER_EXTERNAL_URL.

מקורות (נבדק 2026-11-26):
- https://core.telegram.org/bots/api#setwebhook  secret_token: 1-256 תווים, A-Z a-z 0-9 _ -;
  Telegram שולחת שוב כשהתשובה אינה 2XX; עדכונים נשמרים עד 24 שעות (#getting-updates)
- https://core.telegram.org/bots/api#update  update_id מאפשר לזהות עדכון שהגיע פעמיים
- https://core.telegram.org/bots/api#sendmessage  text: עד 4096 תווים
- https://core.telegram.org/bots/faq  לא יותר מהודעה אחת בשנייה לאותו צ'אט
"""
import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from typing import FrozenSet, Optional

import requests

logger = logging.getLogger("JobMatchServer")

CHANNEL = "telegram"
API_URL = "https://api.telegram.org/bot{token}/{method}"
MAX_TEXT_CHARS = 4096
REQUEST_TIMEOUT_SECONDS = 15
WEBHOOK_PATH = "/webhooks/telegram"


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    allowed_chat_ids: FrozenSet[str]

    @property
    def webhook_secret(self) -> str:
        # 64 תווים hex: בתוך המגבלה של secret_token (1-256, A-Z a-z 0-9 _ -)
        return hashlib.sha256(f"jobmatch-telegram-webhook:{self.bot_token}".encode()).hexdigest()


@dataclass(frozen=True)
class IncomingMessage:
    update_id: str
    chat_id: str
    text: str


def load_config() -> Optional[TelegramConfig]:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        return None
    allowed = frozenset(
        c.strip() for c in (os.getenv("TELEGRAM_ALLOWED_CHAT_IDS") or "").split(",") if c.strip()
    )
    return TelegramConfig(bot_token=token, allowed_chat_ids=allowed)


def verify_secret(header: Optional[str], config: TelegramConfig) -> bool:
    if not header:
        return False
    return hmac.compare_digest(
        config.webhook_secret.encode(), header.strip().encode("utf-8", "replace")
    )


def parse_update(update: dict) -> Optional[IncomingMessage]:
    """
    רק message (הודעה חדשה). עדכונים אחרים (עריכה, הצטרפות לקבוצה) מחזירים None.
    הודעה בלי טקסט (תמונה, מדבקה) מחזירה text ריק: הבוט עונה עליה בהסבר.
    """
    if not isinstance(update, dict) or "update_id" not in update:
        return None
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return None
    text = str(message.get("text") or message.get("caption") or "")
    # קישור "מוסתר" (מילה שהיא קישור, נפוץ בערוצי משרות) לא מופיע בטקסט: הוא ב-entities מסוג
    # text_link (https://core.telegram.org/bots/api#messageentity). מוסיפים אותו בסוף הטקסט.
    hidden = [
        e.get("url")
        for e in (message.get("entities") or []) + (message.get("caption_entities") or [])
        if isinstance(e, dict) and e.get("type") == "text_link" and e.get("url")
    ]
    hidden = [url for url in hidden if url not in text]
    if hidden:
        text = text + "\n" + "\n".join(hidden)
    return IncomingMessage(update_id=str(update["update_id"]), chat_id=str(chat_id), text=text)


def is_allowed(message: IncomingMessage, config: TelegramConfig) -> bool:
    return message.chat_id in config.allowed_chat_ids


def _call(config: TelegramConfig, method: str, payload: dict) -> bool:
    # הטוקן הוא חלק מה-URL: לא רושמים את ה-URL ולא את החריגה. שימו לב: ברמת לוג DEBUG,
    # urllib3 עצמו רושם את שורת הבקשה (כולל הטוקן). השרת רץ ב-INFO (server.py).
    url = API_URL.format(token=config.bot_token, method=method)
    try:
        res = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        # לא רושמים את החריגה עצמה: ה-URL שבה כולל את הטוקן
        logger.error(f"❌ Telegram: {method} failed: {type(e).__name__}")
        return False
    try:
        body = res.json()
    except ValueError:
        body = {}
    if res.ok and body.get("ok"):
        return True
    logger.error(f"❌ Telegram: {method} failed ({res.status_code}): {str(body.get('description'))[:300]}")
    return False


def send_text(config: TelegramConfig, chat_id: str, text: str) -> bool:
    if len(text) > MAX_TEXT_CHARS:
        text = text[: MAX_TEXT_CHARS - 1] + "…"
    return _call(
        config,
        "sendMessage",
        {"chat_id": chat_id, "text": text, "link_preview_options": {"is_disabled": True}},
    )


def public_webhook_url() -> Optional[str]:
    """Render מגדיר את RENDER_EXTERNAL_URL לשירות web. מקומית אין כתובת HTTPS ציבורית."""
    base = (os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
    return f"{base}{WEBHOOK_PATH}" if base.startswith("https://") else None


def register_webhook(config: TelegramConfig) -> bool:
    """
    setWebhook לכתובת של השירות, עם הסוד. בטוח לקרוא בכל הפעלה (אותם ערכים).
    בלי drop_pending_updates: הודעות שנשלחו בזמן שהשירות ישן נשמרות אצל Telegram ומגיעות.
    """
    url = public_webhook_url()
    if url is None:
        logger.info("ℹ️ Telegram: no RENDER_EXTERNAL_URL - webhook not registered (local run)")
        return False
    ok = _call(
        config,
        "setWebhook",
        {"url": url, "secret_token": config.webhook_secret, "allowed_updates": ["message"]},
    )
    if ok:
        logger.info(f"✅ Telegram: webhook registered at {url}")
    return ok
