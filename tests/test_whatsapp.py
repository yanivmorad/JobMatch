"""
בוט וואטסאפ: webhook (אימות, חתימה, הרשאה, כפילויות), קליטה, והתראה עם הציון.
שום בקשה לא יוצאת ל-Meta: whatsapp.send_text מוחלף ברשימה.
"""
import hashlib
import hmac
import json

import httpx
import pytest

import server
from db.jobs_repository import (
    add_job_notification,
    add_new_job,
    finish_analysis,
    get_job_by_url,
    mark_failed,
    pending_job_notifications,
)
from services import notifier, whatsapp

SECRET = "app-secret"
OWNER = "972501234567"
STRANGER = "972509999999"
JOB_URL = "https://jobs.lever.co/acme/1111-2222"


@pytest.fixture
def wa_env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", SECRET)
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "access")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_ALLOWED_NUMBERS", "+972-50-123-4567")


@pytest.fixture
def sent(monkeypatch):
    """כל ההודעות ש"נשלחו": [(to, body)]."""
    calls = []

    def fake_send(config, to, body):
        calls.append((to, body))
        return True

    monkeypatch.setattr(whatsapp, "send_text", fake_send)
    return calls


def _payload(text="QA Engineer\n" + JOB_URL, sender=OWNER, message_id="wamid.1", msg_type="text"):
    message = {"from": sender, "id": message_id, "timestamp": "1764100000", "type": msg_type}
    if msg_type == "text":
        message["text"] = {"body": text}
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "15550001111", "phone_number_id": "123456"},
                    "contacts": [{"profile": {"name": "Me"}, "wa_id": sender}],
                    "messages": [message],
                },
            }],
        }],
    }


def _signed(payload: dict, secret: str = SECRET):
    raw = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return raw, {"X-Hub-Signature-256": sig, "Content-Type": "application/json"}


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")


# --- יחידה ---


def test_signature_is_hmac_sha256_of_the_raw_body():
    raw, headers = _signed({"a": 1})
    assert whatsapp.verify_signature(raw, headers["X-Hub-Signature-256"], SECRET)
    assert not whatsapp.verify_signature(raw + b" ", headers["X-Hub-Signature-256"], SECRET)
    assert not whatsapp.verify_signature(raw, headers["X-Hub-Signature-256"], "other")
    assert not whatsapp.verify_signature(raw, None, SECRET)
    assert not whatsapp.verify_signature(raw, headers["X-Hub-Signature-256"][7:], SECRET)


def test_parse_text_message():
    [msg] = whatsapp.parse_messages(_payload(text="שלום"))
    assert (msg.message_id, msg.sender, msg.type, msg.text) == ("wamid.1", OWNER, "text", "שלום")


def test_status_updates_are_not_messages():
    payload = _payload()
    value = payload["entry"][0]["changes"][0]["value"]
    del value["messages"]
    value["statuses"] = [{"id": "wamid.9", "status": "delivered", "recipient_id": OWNER}]
    assert whatsapp.parse_messages(payload) == []


def test_parse_ignores_other_objects_and_keeps_username_senders():
    assert whatsapp.parse_messages({"object": "page", "entry": []}) == []
    payload = _payload()
    msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    del msg["from"]
    msg["from_user_id"] = "US.abc"
    [parsed] = whatsapp.parse_messages(payload)
    assert parsed.sender == "US.abc"


def test_config_requires_every_value(monkeypatch, wa_env):
    assert whatsapp.load_config().allowed == frozenset({OWNER})
    monkeypatch.delenv("WHATSAPP_APP_SECRET")
    assert whatsapp.load_config() is None


def test_long_reply_is_cut_to_the_api_limit(monkeypatch, wa_env):
    bodies = []

    class _Res:
        ok, status_code, text = True, 200, ""

    def fake_post(url, headers, json, timeout):
        bodies.append((url, json))
        return _Res()

    monkeypatch.setattr(whatsapp.requests, "post", fake_post)
    assert whatsapp.send_text(whatsapp.load_config(), OWNER, "א" * 5000)
    url, body = bodies[0]
    assert url == "https://graph.facebook.com/v27.0/123456/messages"
    assert body["to"] == "+" + OWNER
    assert len(body["text"]["body"]) == whatsapp.MAX_TEXT_CHARS


def test_score_message():
    text = notifier.format_job_message({
        "status": "COMPLETED", "job_title": "QA Engineer", "company": "Acme", "source_url": JOB_URL,
        "analysis": {"suitability_score": 82, "recommendation": "להגיש", "showstoppers": [],
                     "job_summary_hebrew": "בדיקות אוטומטיות"},
    })
    assert "QA Engineer · Acme" in text and "82/100 · להגיש" in text and JOB_URL in text


def test_failure_message():
    text = notifier.format_job_message({"status": "NO_DATA", "source_url": JOB_URL, "analysis": {}})
    assert text.startswith("⚠️") and JOB_URL in text


# --- webhook בלי DB ---


async def test_webhook_is_off_without_config():
    async with _client() as client:
        assert (await client.get("/webhooks/whatsapp")).status_code == 404
        assert (await client.post("/webhooks/whatsapp", json={})).status_code == 404


async def test_verification_echoes_the_challenge(wa_env):
    params = {"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "1158201444"}
    async with _client() as client:
        ok = await client.get("/webhooks/whatsapp", params=params)
        bad = await client.get("/webhooks/whatsapp", params={**params, "hub.verify_token": "x"})
    assert ok.status_code == 200 and ok.text == "1158201444"
    assert bad.status_code == 403


async def test_unsigned_post_is_rejected(wa_env, sent):
    raw, headers = _signed(_payload(), secret="wrong")
    async with _client() as client:
        r = await client.post("/webhooks/whatsapp", content=raw, headers=headers)
    assert r.status_code == 401 and sent == []


async def test_webhook_does_not_need_the_api_token(monkeypatch, wa_env):
    monkeypatch.setenv("API_TOKEN", "secret-api-token")
    params = {"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "7"}
    async with _client() as client:
        assert (await client.get("/webhooks/whatsapp", params=params)).status_code == 200


# --- עם DB ---


@pytest.mark.db
async def test_message_queues_the_job_and_acknowledges(db, wa_env, sent):
    raw, headers = _signed(_payload())
    async with _client() as client:
        r = await client.post("/webhooks/whatsapp", content=raw, headers=headers)

    assert r.status_code == 200
    job = await get_job_by_url(JOB_URL)
    assert job["status"] == "PENDING_RESOLVE" and job["source"] == "whatsapp"
    assert job["job_title"] == "QA Engineer"  # הכותרת מההודעה
    assert sent == [(OWNER, sent[0][1])] and "קיבלתי 1 משרות" in sent[0][1]
    assert [n["job_id"] for n in await pending_job_notifications(["whatsapp"])] == []  # עוד לא סופית


@pytest.mark.db
async def test_redelivered_message_is_handled_once(db, wa_env, sent):
    raw, headers = _signed(_payload())
    async with _client() as client:
        await client.post("/webhooks/whatsapp", content=raw, headers=headers)
        r = await client.post("/webhooks/whatsapp", content=raw, headers=headers)
    assert r.status_code == 200
    assert len(sent) == 1


@pytest.mark.db
async def test_stranger_gets_no_answer_and_nothing_is_queued(db, wa_env, sent):
    raw, headers = _signed(_payload(sender=STRANGER))
    async with _client() as client:
        r = await client.post("/webhooks/whatsapp", content=raw, headers=headers)
    assert r.status_code == 200
    assert sent == [] and await get_job_by_url(JOB_URL) is None


@pytest.mark.db
async def test_message_without_links_gets_help(db, wa_env, sent):
    raw, headers = _signed(_payload(text="היי"))
    async with _client() as client:
        await client.post("/webhooks/whatsapp", content=raw, headers=headers)
    assert "לא מצאתי קישורי משרות" in sent[0][1]


@pytest.mark.db
async def test_image_message_gets_help(db, wa_env, sent):
    raw, headers = _signed(_payload(msg_type="image"))
    async with _client() as client:
        await client.post("/webhooks/whatsapp", content=raw, headers=headers)
    assert sent == [(OWNER, notifier_help())]


def notifier_help():
    from routes.whatsapp_routes import HELP_TEXT

    return HELP_TEXT


@pytest.mark.db
async def test_score_is_sent_once_when_the_job_completes(db, wa_env, sent):
    job_id = await add_new_job(JOB_URL, source="whatsapp")
    await add_job_notification(job_id, "whatsapp", OWNER)

    assert await notifier.send_pending_notifications() is False  # עוד בצינור
    await finish_analysis(job_id, {"company": "Acme", "job_title": "QA", "suitability_score": 77,
                                   "recommendation": "להגיש"})
    assert await notifier.send_pending_notifications() is True
    assert await notifier.send_pending_notifications() is False  # לא שולחים פעמיים

    [(to, body)] = sent
    assert to == OWNER and "77/100" in body


@pytest.mark.db
async def test_failed_send_stays_pending(db, wa_env, monkeypatch):
    monkeypatch.setattr(whatsapp, "send_text", lambda config, to, body: False)
    job_id = await add_new_job(JOB_URL, source="whatsapp")
    await add_job_notification(job_id, "whatsapp", OWNER)
    await mark_failed(job_id, "NO_DATA", "closed")

    assert await notifier.send_pending_notifications() is False
    assert len(await pending_job_notifications(["whatsapp"])) == 1


@pytest.mark.db
async def test_link_scanned_before_gets_the_existing_result(db, wa_env, sent):
    job_id = await add_new_job(JOB_URL)
    await finish_analysis(job_id, {"company": "Acme", "job_title": "QA", "suitability_score": 64})

    raw, headers = _signed(_payload())
    async with _client() as client:
        await client.post("/webhooks/whatsapp", content=raw, headers=headers)
    await notifier.send_pending_notifications()

    assert "כבר נסרקו" in sent[0][1]
    assert "64/100" in sent[1][1]


@pytest.mark.db
async def test_deleting_the_job_deletes_its_notifications(db, wa_env):
    from db.jobs_repository import delete_job_by_id

    job_id = await add_new_job(JOB_URL, source="whatsapp")
    await add_job_notification(job_id, "whatsapp", OWNER)
    await delete_job_by_id(job_id)
    await mark_failed(job_id, "NO_DATA", "x")  # לא קיימת יותר
    assert await pending_job_notifications(["whatsapp"]) == []


# --- תיקונים מהסקירה ---


def test_non_ascii_signature_is_rejected_not_a_crash():
    raw, _ = _signed({"a": 1})
    assert not whatsapp.verify_signature(raw, "sha256=é", SECRET)


async def test_non_ascii_signature_header_gets_401(wa_env, sent):
    raw, headers = _signed(_payload())
    headers["X-Hub-Signature-256"] = "sha256=é".encode("latin-1")  # Starlette מפענח כ-latin-1
    async with _client() as client:
        r = await client.post("/webhooks/whatsapp", content=raw, headers=headers)
    assert r.status_code == 401


async def test_oversized_body_is_refused_before_reading(wa_env, sent):
    async with _client() as client:
        r = await client.post(
            "/webhooks/whatsapp", content=b"{}", headers={"Content-Length": str(10 * 1024 * 1024)}
        )
    assert r.status_code == 413


@pytest.mark.db
async def test_reaction_gets_no_answer(db, wa_env, sent):
    raw, headers = _signed(_payload(msg_type="reaction"))
    async with _client() as client:
        await client.post("/webhooks/whatsapp", content=raw, headers=headers)
    assert sent == []


@pytest.mark.db
async def test_failure_while_handling_tells_the_user(db, wa_env, sent, monkeypatch):
    from routes import whatsapp_routes

    async def broken(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(whatsapp_routes, "ingest_for_bot", broken)
    raw, headers = _signed(_payload())
    async with _client() as client:
        await client.post("/webhooks/whatsapp", content=raw, headers=headers)
    assert sent == [(OWNER, whatsapp_routes.ERROR_TEXT)]


@pytest.mark.db
async def test_link_sent_again_after_its_score_gets_the_score_again(db, wa_env, sent):
    """באג (סקירה): ON CONFLICT DO NOTHING - השורה כבר סומנה כנשלחה, והתוצאה המובטחת לא הגיעה."""
    job_id = await add_new_job(JOB_URL, source="whatsapp")
    await add_job_notification(job_id, "whatsapp", OWNER)
    await finish_analysis(job_id, {"company": "Acme", "job_title": "QA", "suitability_score": 55})
    await notifier.send_pending_notifications()

    raw, headers = _signed(_payload(message_id="wamid.2"))
    async with _client() as client:
        await client.post("/webhooks/whatsapp", content=raw, headers=headers)
    await notifier.send_pending_notifications()

    scores = [body for _to, body in sent if "55/100" in body]
    assert len(scores) == 2


@pytest.mark.db
async def test_notification_outside_the_24h_window_is_dropped(db, wa_env, sent, raw_conn):
    """מחוץ לחלון השירות Meta לא מקבלת הודעה חופשית: לא מנסים לשלוח (ולא שוב ושוב)."""
    job_id = await add_new_job(JOB_URL, source="whatsapp")
    await add_job_notification(job_id, "whatsapp", OWNER)
    await finish_analysis(job_id, {"company": "Acme", "job_title": "QA", "suitability_score": 50})
    await raw_conn.execute("UPDATE job_notifications SET created_at = NOW() - INTERVAL '25 hours'")

    assert await notifier.send_pending_notifications() is False
    assert sent == []


@pytest.mark.db
async def test_duplicate_job_hands_its_notification_to_the_original(db, wa_env, sent):
    """באג (סקירה): קישור HireMeTech שהתפענח למשרה קיימת קיבל 'לא הצלחתי לנתח' במקום הציון."""
    from db.jobs_repository import move_job_notifications

    original = await add_new_job("https://jobs.lever.co/acme/orig")
    await finish_analysis(original, {"company": "Acme", "job_title": "QA", "suitability_score": 91})
    dup = await add_new_job("https://hiremetech.com/job/5", source="whatsapp")
    await add_job_notification(dup, "whatsapp", OWNER)
    await mark_failed(dup, "DUPLICATE", f"Exists as ID: {original}")
    await move_job_notifications(dup, original)

    await notifier.send_pending_notifications()
    [(to, body)] = sent
    assert "91/100" in body and "לא הצלחתי" not in body