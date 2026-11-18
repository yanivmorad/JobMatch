import pytest
from fastapi.testclient import TestClient

import server
from services import profile_service


@pytest.fixture
def client(tmp_path, monkeypatch):
    resume = tmp_path / "resume.txt"
    context = tmp_path / "context.txt"
    resume.write_text("קורות חיים לבדיקה", encoding="utf-8")
    context.write_text("הקשר לבדיקה", encoding="utf-8")
    monkeypatch.setattr(profile_service, "RESUME_PATH", str(resume))
    monkeypatch.setattr(profile_service, "CONTEXT_PATH", str(context))
    # בלי "with" כדי שה-lifespan (workers + DB) לא ירוץ
    return TestClient(server.app)


def test_profile_routes_are_mounted_under_api_profile(client):
    """באג: profile_routes לא היה מחובר, והדשבורד קיבל 404 על /api/profile/*."""
    assert client.get("/api/profile/resume").json() == {"content": "קורות חיים לבדיקה"}
    assert client.get("/api/profile/context").json() == {"content": "הקשר לבדיקה"}


def test_profile_update_roundtrip(client):
    r = client.post("/api/profile/context", json={"content": "הקשר חדש"})
    assert r.status_code == 200
    assert client.get("/api/profile/context").json() == {"content": "הקשר חדש"}
