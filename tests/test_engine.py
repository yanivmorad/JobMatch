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


VALID = {
    "company": "Acme",
    "job_title": "Data Analyst",
    "suitability_score": 72,
    "acceptance_probability": 55,
    "job_summary_hebrew": "סיכום",
    "showstoppers": [],
    "gap_analysis": ["Tableau"],
    "recommendation": "להגיש",
    "formatted_message": "הודעה",
}


@pytest.fixture
def analyzer(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    return JobAnalyzer()


def test_api_key_is_sent_in_header_not_in_url(analyzer, monkeypatch):
    """באג: המפתח היה ב-query string, ולכן הופיע בהודעות שגיאה ובלוגים."""
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append((url, headers))
        return _FakeResponse(200, _gemini_body(VALID), url)

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


def test_model_chain_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_MODELS", " gemini-2.5-flash-lite, gemini-3.5-flash-lite ,,gemini-2.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL", "ignored-when-chain-set")
    assert engine.configured_models() == ["gemini-2.5-flash-lite", "gemini-3.5-flash-lite"]
    monkeypatch.delenv("GEMINI_MODELS")
    assert engine.configured_models() == ["ignored-when-chain-set"]


def test_result_records_which_model_analyzed(analyzer, monkeypatch):
    monkeypatch.setattr(
        engine.requests, "post", lambda url, headers=None, json=None, timeout=None: _FakeResponse(200, _gemini_body(VALID), url)
    )
    assert analyzer.analyze("cv", "ctx", {"url": "u", "full_description": "d"})["model"] == engine.DEFAULT_MODEL


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


# --- שלב 4/5: סכמה, retry ושגיאות מסווגות ---

from engine import AIError, InvalidAIResponse, RateLimitError, TransientAIError


class _Resp(_FakeResponse):
    def __init__(self, status_code, body, headers=None):
        super().__init__(status_code, body, "https://generativelanguage.googleapis.com/x")
        self.headers = headers or {}


def _sequence(monkeypatch, *responses):
    """fake requests.post שמחזיר את התשובות לפי הסדר (Exception = נזרק)."""
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        r = responses[len(calls) - 1]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(engine.requests, "post", fake_post)
    return calls


_JOB = {"url": "https://jobs.example/1", "full_description": "Data Analyst. Requirements: SQL. Experience: 2 years."}


def test_valid_answer_is_returned_with_all_fields(analyzer, monkeypatch):
    _sequence(monkeypatch, _Resp(200, _gemini_body(VALID)))
    result = analyzer.analyze("cv", "ctx", _JOB)
    assert result["url"] == _JOB["url"]
    assert {k: result[k] for k in VALID} == VALID


def test_request_uses_structured_output_schema(analyzer, monkeypatch):
    calls = _sequence(monkeypatch, _Resp(200, _gemini_body(VALID)))
    analyzer.analyze("cv", "ctx", _JOB)
    config = calls[0]["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert set(config["responseSchema"]["required"]) >= {"company", "job_title", "suitability_score", "recommendation"}


def test_missing_field_is_retried_then_succeeds(analyzer, monkeypatch):
    partial = {k: v for k, v in VALID.items() if k != "job_title"}
    calls = _sequence(monkeypatch, _Resp(200, _gemini_body(partial)), _Resp(200, _gemini_body(VALID)))
    assert analyzer.analyze("cv", "ctx", _JOB)["job_title"] == "Data Analyst"
    assert len(calls) == 2


def test_broken_json_twice_raises_invalid_response(analyzer, monkeypatch):
    broken = {"candidates": [{"content": {"parts": [{"text": "{not json"}]}}]}
    _sequence(monkeypatch, _Resp(200, broken), _Resp(200, broken))
    with pytest.raises(InvalidAIResponse):
        analyzer.analyze("cv", "ctx", _JOB)


def test_score_out_of_range_is_rejected(analyzer, monkeypatch):
    bad = {**VALID, "suitability_score": 140}
    _sequence(monkeypatch, _Resp(200, _gemini_body(bad)), _Resp(200, _gemini_body(bad)))
    with pytest.raises(InvalidAIResponse):
        analyzer.analyze("cv", "ctx", _JOB)


def test_recommendation_variants_are_normalized(analyzer, monkeypatch):
    _sequence(monkeypatch, _Resp(200, _gemini_body({**VALID, "recommendation": "לא כדאי להגיש."})))
    assert analyzer.analyze("cv", "ctx", _JOB)["recommendation"] == "לא להגיש"


def test_429_per_day_quota_is_parsed(analyzer, monkeypatch):
    body = {
        "error": {
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier", "quotaValue": "20"}],
                },
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "39s"},
            ],
        }
    }
    calls = _sequence(monkeypatch, _Resp(429, body))
    with pytest.raises(RateLimitError) as err:
        analyzer.analyze("cv", "ctx", _JOB)
    assert err.value.retry_after == 39
    assert err.value.per_day is True
    assert err.value.quota_values == ["20"]
    assert len(calls) == 1  # 429 לא נשלח שוב בתוך המנוע - ה-worker מחכה ומחזיר לתור


def test_429_per_minute_uses_retry_after_header(analyzer, monkeypatch):
    body = {"error": {"details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                                   "violations": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]}]}}
    _sequence(monkeypatch, _Resp(429, body, headers={"Retry-After": "7"}))
    with pytest.raises(RateLimitError) as err:
        analyzer.analyze("cv", "ctx", _JOB)
    assert err.value.retry_after == 7 and err.value.per_day is False


@pytest.mark.parametrize(
    "response, error",
    [
        (_Resp(503, {}), TransientAIError),
        (requests.ConnectionError("down"), TransientAIError),
        (requests.Timeout("slow"), TransientAIError),
        (_Resp(400, {"error": {"message": "API key not valid"}}), AIError),
    ],
)
def test_errors_are_classified(analyzer, monkeypatch, response, error):
    _sequence(monkeypatch, response)
    with pytest.raises(error) as err:
        analyzer.analyze("cv", "ctx", _JOB)
    if error is AIError:
        assert not isinstance(err.value, TransientAIError)
    assert FAKE_KEY not in str(err.value)


def test_long_description_is_condensed_before_sending(analyzer, monkeypatch):
    monkeypatch.setenv("MAX_DESCRIPTION_CHARS", "3000")
    nav = "\n".join(f"[Menu item {i}](https://site/{i})" for i in range(400))
    body = "## Requirements\n" + "\n".join(f"- 3 years of experience with tool {i}" for i in range(40))
    calls = _sequence(monkeypatch, _Resp(200, _gemini_body(VALID)))
    analyzer.analyze("cv", "ctx", {"url": "u", "full_description": nav + "\n\n" + body})
    prompt = calls[0]["contents"][0]["parts"][0]["text"]
    assert "experience with tool 39" in prompt
    assert "https://site/" not in prompt
    assert len(prompt) < 3000 + 2000  # תיאור מקוצר + תבנית הפרומפט


def test_removed_model_404_is_its_own_error(analyzer, monkeypatch):
    from engine import ModelUnavailableError

    _sequence(monkeypatch, _Resp(404, {"error": {"message": "models/x is not found for API version v1beta"}}))
    with pytest.raises(ModelUnavailableError):
        analyzer.analyze("cv", "ctx", _JOB)


def test_default_is_a_model_chain(monkeypatch):
    monkeypatch.delenv("GEMINI_MODELS", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert engine.configured_models() == list(engine.DEFAULT_MODELS)
    assert len(engine.DEFAULT_MODELS) >= 2


def test_prompt_lets_the_personal_context_rules_win():
    prompt = build_prompt("cv", "Hard filters: reject student positions", {"full_description": "d"})
    assert "גוברים על ההוראות הכלליות" in prompt


def test_prompt_lets_the_ai_take_the_company_from_an_application_email():
    """HireMeTech מסתיר את שם החברה, אבל בתיאור יש לפעמים מייל להגשה (jobs@giv-solutions.com)."""
    prompt = build_prompt("cv", "ctx", {"full_description": "d"})
    assert "jobs@acme-tech.com -> Acme Tech" in prompt
    assert "אל תמציא" in prompt


def test_known_title_asks_to_focus_on_that_job_in_a_multi_job_page():
    prompt = build_prompt(
        "cv", "ctx", {"full_description": "Open positions: QA, DevOps", "job_title": "JUNIOR QA ENGINEER"}
    )
    assert "תפקיד: JUNIOR QA ENGINEER" in prompt
    assert "נתח רק את המשרה שתואמת" in prompt


def test_no_focus_instruction_without_a_known_title():
    prompt = build_prompt("cv", "ctx", {"full_description": "d", "company": "Acme", "job_title": "https://x.com/j"})
    assert "חברה: Acme" in prompt
    assert "נתח רק את המשרה שתואמת" not in prompt
