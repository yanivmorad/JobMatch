"""
הפרופיל (קורות חיים + הקשר) נשמר ב-DB.
באג (שלב 6): עריכה בלשונית הפרופיל נכתבה לקובץ ב-data/, שנמחק בכל דיפלוי ב-Render.
"""
import httpx
import pytest

import server
from db.postgres import get_pool
from services import profile_service

pytestmark = pytest.mark.db


@pytest.fixture
def files(tmp_path, monkeypatch):
    resume = tmp_path / "resume.txt"
    context = tmp_path / "context.txt"
    resume.write_text("קורות חיים מקובץ", encoding="utf-8")
    context.write_text("הקשר מקובץ", encoding="utf-8")
    monkeypatch.setattr(profile_service, "RESUME_PATH", str(resume))
    monkeypatch.setattr(profile_service, "CONTEXT_PATH", str(context))
    monkeypatch.setattr(profile_service, "SECRETS_DIR", str(tmp_path / "no-secrets"))
    for var in ("RESUME_TEXT", "RESUME_FILE", "PERSONAL_CONTEXT_TEXT", "PERSONAL_CONTEXT_FILE"):
        monkeypatch.delenv(var, raising=False)
    return resume, context


def _client():
    # ASGITransport לא מריץ lifespan (workers)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")


async def test_profile_routes_are_mounted_under_api_profile(db, files):
    """באג: profile_routes לא היה מחובר, והדשבורד קיבל 404 על /api/profile/*."""
    async with _client() as client:
        assert (await client.get("/api/profile/resume")).json() == {"content": "קורות חיים מקובץ"}
        assert (await client.get("/api/profile/context")).json() == {"content": "הקשר מקובץ"}


async def test_first_read_seeds_the_db_and_edits_stay_in_the_db(db, files):
    resume_file, _ = files
    async with _client() as client:
        await client.get("/api/profile/resume")  # seed מהקובץ
        r = await client.post("/api/profile/resume", json={"content": "קורות חיים חדשים"})
        assert r.status_code == 200
        assert (await client.get("/api/profile/resume")).json() == {"content": "קורות חיים חדשים"}

    pool = await get_pool()
    assert await pool.fetchval("SELECT content FROM profile WHERE key = 'resume'") == "קורות חיים חדשים"
    # הקובץ לא נגע (בענן הוא בכלל לא קיים / נמחק בדיפלוי)
    assert resume_file.read_text(encoding="utf-8") == "קורות חיים מקובץ"


async def test_edit_survives_a_deploy_without_the_file(db, files):
    resume_file, _ = files
    await profile_service.set_profile("resume", "נשמר ב-DB")
    resume_file.unlink()  # "דיפלוי": הדיסק המקומי נמחק
    assert await profile_service.get_profile("resume") == "נשמר ב-DB"


async def test_seed_order_env_text_then_env_file_then_secret_file(db, files, tmp_path, monkeypatch):
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "personal_context.txt").write_text("הקשר מ-secret file", encoding="utf-8")
    monkeypatch.setattr(profile_service, "SECRETS_DIR", str(secrets))
    assert await profile_service.get_profile("context") == "הקשר מ-secret file"

    other = tmp_path / "cv.txt"
    other.write_text("קורות חיים מ-RESUME_FILE", encoding="utf-8")
    monkeypatch.setenv("RESUME_FILE", str(other))
    monkeypatch.setenv("RESUME_TEXT", "קורות חיים מ-RESUME_TEXT")
    assert await profile_service.get_profile("resume") == "קורות חיים מ-RESUME_TEXT"


async def test_missing_profile_returns_empty(db, files):
    for f in files:
        f.unlink()
    assert await profile_service.get_profile("resume") == ""
