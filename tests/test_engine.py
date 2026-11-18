import json
import logging

import pytest
import requests

import engine
from engine import JobAnalyzer, build_prompt

FAKE_KEY = "AIza-TEST-SECRET-123"


class _FakeResponse:
    def __init__(self, status_code: int, body: dict, url: str):
        self.status_code = status_code
        self._body = body
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            # כמו requests אמיתי: הודעת השגיאה כוללת את ה-URL המלא
            raise requests.HTTPError(
                f"{self.status_code} Client Error: for url: {self.url}"
            )

    def json(self):
        return self._body


def _gemini_body(result: dict) -> dict:
    return {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(result, ensure_ascii=False)}]}}
        ]
    }


@pytest.fixture
def analyzer(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(engine.time, "sleep", lambda *_: None)
    return JobAnalyzer()


def test_api_key_is_sent_in_header_not_in_url(analyzer, monkeypatch):
    """באג: המפתח היה ב-query string, ולכן הופיע בהודעות שגיאה ובלוגים."""
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append((url, headers))
        return _FakeResponse(200, _gemini_body({"suitability_score": 50}), url)

    monkeypatch.setattr(engine.requests, "post", fake_post)
    analyzer.analyze("cv", "ctx", {"url": "u", "full_description": "d"})

    url, headers = calls[0]
    assert FAKE_KEY not in url
    assert "key=" not in url
    assert headers["x-goog-api-key"] == FAKE_KEY


def test_http_errors_do_not_leak_api_key(analyzer, monkeypatch, caplog):
    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse(429, {}, url)

    monkeypatch.setattr(engine.requests, "post", fake_post)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(RuntimeError) as exc:
            analyzer.analyze("cv", "ctx", {"url": "u", "full_description": "d"})

    assert FAKE_KEY not in caplog.text
    assert FAKE_KEY not in str(exc.value)
    assert "429" in caplog.text  # השגיאה עצמה עדיין מתועדת


def test_model_is_configurable(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    assert "/models/gemini-3.5-flash-lite:generateContent" in JobAnalyzer().api_url


def test_empty_model_env_falls_back_to_default(monkeypatch):
    """שורה ריקה GEMINI_MODEL= ב-.env (כמו ב-.env.example) לא אמורה לשבור את ה-URL."""
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("GEMINI_MODEL", "")
    assert f"/models/{engine.DEFAULT_MODEL}:generateContent" in JobAnalyzer().api_url


def test_prompt_has_no_hardcoded_candidate_name():
    """באג: השם 'יניב' היה כתוב בתוך הפרומפט."""
    prompt = build_prompt("cv", "ctx", {"full_description": "d"})
    assert "יניב" not in prompt


def test_prompt_asks_to_extract_company_and_title_from_description():
    """באג: הפרומפט ביקש להחזיר את הערך הגולמי ('Unknown') במקום לחלץ מהתיאור."""
    prompt = build_prompt(
        "cv",
        "ctx",
        {"full_description": "d", "company": "Unknown", "job_title": "https://x.com/job"},
    )
    assert '"company": "Unknown"' not in prompt
    assert "https://x.com/job" not in prompt
    assert "פרטים ידועים" not in prompt  # placeholders לא נשלחים כרמז


def test_prompt_passes_manual_company_as_hint():
    prompt = build_prompt(
        "cv", "ctx", {"full_description": "d", "company": "Wix", "job_title": "Backend"}
    )
    assert "חברה: Wix" in prompt
    assert "תפקיד: Backend" in prompt
