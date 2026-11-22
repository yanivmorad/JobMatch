"""
שלב 6: אימות ל-API (API_TOKEN) והגדרות ענן (ENABLE_PLAYWRIGHT).
באג: ה-API היה פתוח לכל מי שמכיר את הכתובת.
"""
import httpx
import pytest

import server
from scraper_service import resolvers
from scraper_service import scraper as scraper_module
from scraper_service.resolvers import ResolveError, URLResolver

TOKEN = "s3cret-token-for-tests"


def _client(headers=None):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=server.app), base_url="http://test", headers=headers or {}
    )


async def test_api_is_open_when_no_token_is_configured(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    async with _client() as client:
        r = await client.post("/api/jobs/extract-links", json={"text": "https://jobs.lever.co/a/1"})
    assert r.status_code == 200


@pytest.mark.parametrize(
    "headers, status",
    [
        ({}, 401),
        ({"Authorization": "Bearer wrong"}, 401),
        ({"Authorization": f"Bearer {TOKEN}"}, 200),
        ({"X-API-Key": TOKEN}, 200),
    ],
)
async def test_api_requires_the_token(monkeypatch, headers, status):
    monkeypatch.setenv("API_TOKEN", TOKEN)
    async with _client(headers) as client:
        r = await client.post("/api/jobs/extract-links", json={"text": "https://jobs.lever.co/a/1"})
    assert r.status_code == status


async def test_profile_routes_are_protected_too(monkeypatch):
    monkeypatch.setenv("API_TOKEN", TOKEN)
    async with _client() as client:
        assert (await client.get("/api/profile/resume")).status_code == 401


@pytest.mark.db
async def test_health_stays_open_for_the_platform_health_check(db, monkeypatch):
    monkeypatch.setenv("API_TOKEN", TOKEN)
    async with _client() as client:
        r = await client.get("/health")
    assert r.status_code in (200, 503)  # 503 = ה-workers לא רצים בבדיקה; העיקר שלא 401
    assert r.json()["db"]["ok"] is True


async def test_cors_preflight_does_not_need_the_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", TOKEN)
    async with _client() as client:
        r = await client.options(
            "/api/results",
            headers={"Origin": "https://dash.example", "Access-Control-Request-Method": "GET",
                     "Access-Control-Request-Headers": "authorization"},
        )
    assert r.status_code == 200


# --- ENABLE_PLAYWRIGHT=false (שרת עם מעט זיכרון) ---


def test_scraper_skips_the_browser_when_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_PLAYWRIGHT", "false")
    monkeypatch.setattr(scraper_module, "HAS_PLAYWRIGHT", True)
    s = scraper_module.Scraper()
    monkeypatch.setattr(s, "_try_jina", lambda url, tag, trace: None)
    monkeypatch.setattr(s, "_scrape_with_playwright", lambda *a, **k: pytest.fail("browser launched"))
    assert s.scrape("https://careers.example.com/jobs/1", trace=[]) is None


def test_hiremetech_uses_the_public_page_when_the_browser_is_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_PLAYWRIGHT", "false")
    monkeypatch.setattr(resolvers, "HAS_PLAYWRIGHT", True)
    with pytest.raises(ResolveError) as err:
        URLResolver(hireme_token="t").resolve("https://hiremetech.com/job/1")
    assert err.value.public_fallback is True


@pytest.mark.parametrize("value, expected", [(None, True), ("true", True), ("false", False), ("0", False), ("off", False)])
def test_playwright_switch(monkeypatch, value, expected):
    from scraper_service.utils import playwright_allowed

    if value is None:
        monkeypatch.delenv("ENABLE_PLAYWRIGHT", raising=False)
    else:
        monkeypatch.setenv("ENABLE_PLAYWRIGHT", value)
    assert playwright_allowed() is expected


async def test_ping_needs_no_token_and_no_db(monkeypatch):
    monkeypatch.setenv("API_TOKEN", TOKEN)
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:x@127.0.0.1:1/none")  # DB לא זמין
    async with _client() as client:
        r = await client.get("/ping")
    assert r.status_code == 200 and r.json() == {"ok": True}
