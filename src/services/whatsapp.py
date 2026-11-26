"""
בוט וואטסאפ דרך WhatsApp Cloud API של Meta (הרשמי): המשתמש שולח הודעה עם קישורי משרות
למספר של הבוט, והשרת מקבל אותה ב-webhook, מכניס את המשרות לתור ושולח ציון לכל אחת.

כל ההגדרות חייבות להיות קיימות, אחרת הבוט כבוי (ה-webhook מחזיר 404):
  WHATSAPP_VERIFY_TOKEN     מחרוזת שאתה בוחר, ומקלידים אותה גם ב-App Dashboard (אימות ה-webhook)
  WHATSAPP_APP_SECRET       App Secret של האפליקציה ב-Meta (חתימת ה-webhook)
  WHATSAPP_ACCESS_TOKEN     טוקן לשליחת הודעות (System User קבוע, לא הטוקן הזמני)
  WHATSAPP_PHONE_NUMBER_ID  ה-id של מספר הבוט (לא מספר הטלפון עצמו)
  WHATSAPP_ALLOWED_NUMBERS  המספרים שמותר להם לשלוח, מופרדים בפסיקים (למשל 972501234567)
אופציונלי: WHATSAPP_GRAPH_VERSION (ברירת מחדל v27.0, הגרסה בדוגמאות של התיעוד ב-2026-11-26).

מקורות (נבדק 2026-11-26):
- אימות ו-webhook: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks
- חתימה X-Hub-Signature-256: https://developers.facebook.com/docs/graph-api/webhooks/getting-started
- שליחת טקסט (עד 4096 תווים):
  https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/text-messages
"""
import hashlib
import hmac
import logging
import os
import re
from dataclasses import dataclass
from typing import FrozenSet, List, Optional

import requests

logger = logging.getLogger("JobMatchServer")

CHANNEL = "whatsapp"
DEFAULT_GRAPH_VERSION = "v27.0"
MAX_TEXT_CHARS = 4096
SEND_TIMEOUT_SECONDS = 15

_REQUIRED = (
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_ALLOWED_NUMBERS",
)


@dataclass(frozen=True)
class WhatsAppConfig:
    verify_token: str
    app_secret: str
    access_token: str
    phone_number_id: str
    allowed: FrozenSet[str]
    graph_version: str = DEFAULT_GRAPH_VERSION


@dataclass(frozen=True)
class IncomingMessage:
    message_id: str
    sender: str  # למי עונים: wa_id (מספר), או from_user_id כשלמשתמש יש שם משתמש
    sender_ids: FrozenSet[str]  # כל המזהים של השולח, לבדיקת ההרשאה
    type: str
    text: str


def normalize_number(value: str) -> str:
    """'+972-50-123 4567' -> '972501234567'. מזהה שאינו מספר (from_user_id) נשאר כמו שהוא."""
    value = (value or "").strip()
    digits = re.sub(r"[\s\-+()]", "", value)
    return digits if digits.isdigit() else value


def load_config() -> Optional[WhatsAppConfig]:
    values = {key: (os.getenv(key) or "").strip() for key in _REQUIRED}
    if not all(values.values()):
        return None
    allowed = frozenset(
        normalize_number(n) for n in values["WHATSAPP_ALLOWED_NUMBERS"].split(",") if n.strip()
    )
    if not allowed:
        return None
    return WhatsAppConfig(
        verify_token=values["WHATSAPP_VERIFY_TOKEN"],
        app_secret=values["WHATSAPP_APP_SECRET"],
        access_token=values["WHATSAPP_ACCESS_TOKEN"],
        phone_number_id=values["WHATSAPP_PHONE_NUMBER_ID"],
        allowed=allowed,
        graph_version=(os.getenv("WHATSAPP_GRAPH_VERSION") or "").strip() or DEFAULT_GRAPH_VERSION,
    )


def verify_signature(raw_body: bytes, header: Optional[str], app_secret: str) -> bool:
    """X-Hub-Signature-256: sha256=<HMAC-SHA256 של גוף הבקשה הגולמי עם ה-App Secret>."""
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest().encode()
    # bytes ולא str: compare_digest זורק TypeError על str עם תו שאינו ASCII (500 במקום 401)
    provided = header[len("sha256="):].strip().lower().encode("utf-8", "replace")
    return hmac.compare_digest(expected, provided)


def parse_messages(payload: dict) -> List[IncomingMessage]:
    """
    entry[].changes[].value.messages[] בלבד. עדכוני סטטוס (value.statuses: sent / delivered /
    read) מגיעים באותו מבנה בלי messages, ולכן לא נאספים. Meta יכולה לאחד כמה עדכונים בבקשה אחת.
    """
    messages = []
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        return messages
    for entry in payload.get("entry") or []:
        for change in (entry or {}).get("changes") or []:
            value = (change or {}).get("value") or {}
            for msg in value.get("messages") or []:
                if not isinstance(msg, dict) or not msg.get("id"):
                    continue
                ids = {normalize_number(msg.get(k) or "") for k in ("from", "from_user_id")}
                ids.discard("")
                sender = normalize_number(msg.get("from") or "") or normalize_number(
                    msg.get("from_user_id") or ""
                )
                if not sender:
                    continue
                text = ((msg.get("text") or {}).get("body") or "") if msg.get("type") == "text" else ""
                messages.append(
                    IncomingMessage(
                        message_id=str(msg["id"]),
                        sender=sender,
                        sender_ids=frozenset(ids),
                        type=str(msg.get("type") or ""),
                        text=text,
                    )
                )
    return messages


def is_allowed(message: IncomingMessage, config: WhatsAppConfig) -> bool:
    return bool(message.sender_ids & config.allowed)


def send_text(config: WhatsAppConfig, to: str, body: str) -> bool:
    """שולח הודעת טקסט. True אם Meta קיבלה את הבקשה (המסירה עצמה מדווחת ב-webhook אחר)."""
    if len(body) > MAX_TEXT_CHARS:
        body = body[: MAX_TEXT_CHARS - 1] + "…"
    url = f"https://graph.facebook.com/{config.graph_version}/{config.phone_number_id}/messages"
    to = f"+{to}" if to.isdigit() else to
    try:
        res = requests.post(
            url,
            headers={"Authorization": f"Bearer {config.access_token}"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"preview_url": False, "body": body},
            },
            timeout=SEND_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        logger.error(f"❌ WhatsApp: send failed: {type(e).__name__}")
        return False
    if res.ok:
        return True
    # גוף השגיאה של Meta מתאר את הבעיה (טוקן פג, מספר לא מאושר) ולא מכיל את הטוקן
    logger.error(f"❌ WhatsApp: send failed ({res.status_code}): {res.text[:300]}")
    return False
