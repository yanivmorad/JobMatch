"""
בוט טלגרם: webhook (סוד, הרשאה, כפילויות, /id), קליטה, התראה עם הציון, ורישום ה-webhook.
שום בקשה לא יוצאת ל-Telegram: telegram.send_text / requests.post מוחלפים.
"""
import json

import httpx
import pytest

import server
from db.jobs_repository import (
    add_job_notification,
    add_new_job,
    finish_analysis,
    get_job_by_url,
    pending_job_notifications,
)
from services import notifier, telegram

TOKEN = "123456:ABC-test-token"
OWNER = "555001"
STRANGER = "999002"
JOB_URL = "https://jobs.lever.co/acme/3333-4444"


@pytest.fixture
def tg_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_IDS", f" {OWNER} ")


@pytest.fixture
def sent(monkeypatch):
    calls = []

    def fake_send(config, chat_id, text):
        calls.append((chat_id, text))
        return True

    monkeypatch.setattr(telegram, "send_text", fake_send)
    return calls


def _update(text="QA Engineer\n" + JOB_URL, chat_id=OWNER, update_id=1):
    return {
        "update_id": update_id,
        "message": {
            "message_id": 10,
            "date": 1764100000,
            "from": {"id": int(chat_id), "is_bot": False, "first_name": "Me"},
            "chat": {"id": int(chat_id), "type": "private"},
            "text": text,
        },
    }


def _secret_headers(secret=None):
    config = telegram.TelegramConfig(bot_token=TOKEN, allowed_chat_ids=frozenset())
    return {"X-Telegram-Bot-Api-Secret-Token": secret or config.webhook_secret}


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")


async def _post(update, headers=None):
    async with _client() as client:
        return await client.post(
            "/webhooks/telegram", content=json.dumps(update), headers=headers or _secret_headers()
        )


# --- יחידה ---


def test_secret_is_derived_from_the_token_and_allowed_by_telegram():
    a = telegram.TelegramConfig(bot_token=TOKEN, allowed_chat_ids=frozenset()).webhook_secret
    b = telegram.TelegramConfig(bot_token="other", allowed_chat_ids=frozenset()).webhook_secret
    assert a != b and len(a) == 64 and a.isalnum()  # 1-256 תווים, A-Z a-z 0-9 _ -
    assert TOKEN not in a


def test_config_needs_only_the_token(monkeypatch):
    assert telegram.load_config() is None
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    assert telegram.load_config().allowed_chat_ids == frozenset()


def test_parse_update():
    msg = telegram.parse_update(_update(text="שלום", update_id=7))
    assert (msg.update_id, msg.chat_id, msg.text) == ("7", OWNER, "שלום")
    assert telegram.parse_update({"update_id": 8, "edited_message": {}}) is None
    assert telegram.parse_update({"message": {}}) is None


def test_send_text_disables_previews_and_cuts_to_the_limit(monkeypatch, tg_env):
    calls = []

    class _Res:
        ok, status_code = True, 200

        def json(self):
            return {"ok": True}

    def fake_post(url, json, timeout):
        calls.append((url, json))
        return _Res()

    monkeypatch.setattr(telegram.requests, "post", fake_post)
    assert telegram.send_text(telegram.load_config(), OWNER, "א" * 5000)
    url, body = calls[0]
    assert url == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert body["link_preview_options"] == {"is_disabled": True}
    assert len(body["text"]) == telegram.MAX_TEXT_CHARS


def test_register_webhook_uses_render_url_and_secret(monkeypatch, tg_env):
    calls = []

    class _Res:
        ok, status_code = True, 200

        def json(self):
            return {"ok": True, "result": True}

    monkeypatch.setattr(telegram.requests, "post", lambda url, json, timeout: calls.append((url, json)) or _Res())
    config = telegram.load_config()

    assert telegram.register_webhook(config) is False  # מקומית: אין RENDER_EXTERNAL_URL
    assert calls == []

    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://my-app.onrender.com/")
    assert telegram.register_webhook(config) is True
    url, body = calls[0]
    assert url.endswith("/setWebhook")
    assert body == {
        "url": "https://my-app.onrender.com/webhooks/telegram",
        "secret_token": config.webhook_secret,
        "allowed_updates": ["message"],
    }


def test_failed_telegram_call_is_false_and_does_not_log_the_token(monkeypatch, tg_env, caplog):
    class _Res:
        ok, status_code = False, 401

        def json(self):
            return {"ok": False, "description": "Unauthorized"}

    monkeypatch.setattr(telegram.requests, "post", lambda url, json, timeout: _Res())
    assert telegram.send_text(telegram.load_config(), OWNER, "x") is False
    assert TOKEN not in caplog.text


# --- webhook בלי DB ---


async def test_webhook_is_off_without_a_token():
    assert (await _post(_update())).status_code == 404


async def test_wrong_secret_is_rejected(tg_env, sent):
    r = await _post(_update(), headers=_secret_headers("wrong"))
    assert r.status_code == 401 and sent == []


async def test_stranger_links_are_ignored(tg_env, sent):
    r = await _post(_update(text=JOB_URL, chat_id=STRANGER, update_id=2))
    assert r.status_code == 200 and sent == []


async def test_id_works_before_any_chat_is_allowed(monkeypatch, sent):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    await _post(_update(text="/id@JobMatchBot", chat_id=STRANGER))
    assert STRANGER in sent[0][1]


# --- עם DB ---


@pytest.mark.db
async def test_message_queues_the_job_and_acknowledges(db, tg_env, sent):
    r = await _post(_update())
    assert r.status_code == 200
    job = await get_job_by_url(JOB_URL)
    assert job["status"] == "PENDING_RESOLVE" and job["source"] == "telegram"
    assert sent[0][0] == OWNER and "קיבלתי 1 משרות" in sent[0][1]


@pytest.mark.db
async def test_redelivered_update_is_handled_once(db, tg_env, sent):
    await _post(_update())
    await _post(_update())
    assert len(sent) == 1


@pytest.mark.db
async def test_start_gets_welcome(db, tg_env, sent):
    await _post(_update(text="/start"))
    from routes.telegram_routes import WELCOME_TEXT

    assert sent == [(OWNER, WELCOME_TEXT)]


@pytest.mark.db
async def test_failure_while_handling_tells_the_user(db, tg_env, sent, monkeypatch):
    from routes import telegram_routes

    async def broken(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(telegram_routes, "ingest_for_bot", broken)
    await _post(_update())
    assert sent == [(OWNER, telegram_routes.ERROR_TEXT)]


@pytest.mark.db
async def test_score_is_sent_to_the_telegram_chat(db, tg_env, sent):
    job_id = await add_new_job(JOB_URL, source="telegram")
    await add_job_notification(job_id, "telegram", OWNER)
    await finish_analysis(job_id, {"company": "Acme", "job_title": "QA", "suitability_score": 73})

    assert await notifier.send_pending_notifications() is True
    [(chat, body)] = sent
    assert chat == OWNER and "73/100" in body
    assert await pending_job_notifications(["telegram"], 48) == []


@pytest.mark.db
async def test_telegram_window_is_48_hours(db, tg_env, sent, raw_conn):
    job_id = await add_new_job(JOB_URL, source="telegram")
    await add_job_notification(job_id, "telegram", OWNER)
    await finish_analysis(job_id, {"company": "Acme", "job_title": "QA", "suitability_score": 73})
    await raw_conn.execute("UPDATE job_notifications SET created_at = NOW() - INTERVAL '30 hours'")

    await notifier.send_pending_notifications()
    assert len(sent) == 1  # 30 שעות: מחוץ לחלון של וואטסאפ, בתוך החלון של טלגרם


def test_both_channels_can_be_enabled(monkeypatch, tg_env):
    assert notifier.enabled_channels() == ["telegram"]
    for key, value in {
        "WHATSAPP_VERIFY_TOKEN": "v", "WHATSAPP_APP_SECRET": "s", "WHATSAPP_ACCESS_TOKEN": "a",
        "WHATSAPP_PHONE_NUMBER_ID": "1", "WHATSAPP_ALLOWED_NUMBERS": "972501234567",
    }.items():
        monkeypatch.setenv(key, value)
    assert set(notifier.enabled_channels()) == {"whatsapp", "telegram"}


# --- תיקונים מהסקירה ---


def test_hidden_links_in_entities_are_part_of_the_text():
    """באג (סקירה): קישור "מוסתר" (text_link) מערוץ משרות לא נקלט, והבוט ענה "לא מצאתי קישורים"."""
    update = _update(text="משרת QA חדשה - להגשה")
    update["message"]["entities"] = [
        {"type": "text_link", "offset": 14, "length": 5, "url": JOB_URL},
        {"type": "bold", "offset": 0, "length": 4},
    ]
    msg = telegram.parse_update(update)
    assert JOB_URL in msg.text and msg.text.startswith("משרת QA")


def test_caption_with_hidden_link():
    update = _update()
    del update["message"]["text"]
    update["message"]["caption"] = "QA Engineer"
    update["message"]["caption_entities"] = [{"type": "text_link", "offset": 0, "length": 2, "url": JOB_URL}]
    assert JOB_URL in telegram.parse_update(update).text


def test_network_error_does_not_log_the_token(monkeypatch, tg_env, caplog):
    def boom(url, json, timeout):
        raise telegram.requests.ConnectionError(f"Max retries exceeded with url: {url}")

    monkeypatch.setattr(telegram.requests, "post", boom)
    assert telegram.send_text(telegram.load_config(), OWNER, "x") is False
    assert TOKEN not in caplog.text


async def test_stranger_gets_no_id_once_the_allowlist_is_set(tg_env, sent):
    """אחרי ההקמה הבוט שותק לזרים, גם על /id (לא חושף שהוא חי, ולא נשלחות תשובות לכל מי שמוצף)."""
    r = await _post(_update(text="/id", chat_id=STRANGER))
    assert r.status_code == 200 and sent == []


@pytest.mark.db
async def test_ack_is_sent_before_the_existing_score(db, tg_env, sent):
    """באג (סקירה): notify קרה לפני שליחת האישור, והציון הקיים יכול היה להקדים אותו."""
    from routes import telegram_routes

    job_id = await add_new_job(JOB_URL)
    await finish_analysis(job_id, {"company": "Acme", "job_title": "QA", "suitability_score": 64})

    order = []
    original_wake = telegram_routes.wake_notifier
    telegram_routes.wake_notifier = lambda: order.append(("wake", len(sent)))
    try:
        await _post(_update())
    finally:
        telegram_routes.wake_notifier = original_wake
    assert order == [("wake", 1)]  # הוער אחרי שהאישור כבר נשלח
    assert "כבר נסרקו" in sent[0][1]