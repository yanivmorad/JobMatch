"""
הזרימה הבסיסית מקצה לקצה, כמו שבוט ישתמש בה: הודעה עם קישור -> משרה ב-DB -> צינור
(resolve -> scrape -> AI) -> ציון נשמר ב-DB ונשלף לפי id. הסורק וה-AI מזויפים (בלי רשת),
אבל ה-API, ה-DB וה-workers הם האמיתיים.
"""
import httpx
import pytest

import server
from services.profile_service import set_profile
from workers import worker_manager
from workers.rate_limiter import AIRateLimiter, ModelPool

pytestmark = pytest.mark.db

MESSAGE = """בוקר טוב! משרה חדשה:
*שם המשרה:* Junior Backend Developer
*לינק להגשה:* https://jobs.lever.co/acme/123?utm_source=whatsapp
וגם האפליקציה שלנו: https://apps.apple.com/il/app/x/id1"""

ANALYSIS = {
    "company": "Acme", "job_title": "Junior Backend Developer", "suitability_score": 78,
    "acceptance_probability": 55, "job_summary_hebrew": "משרת backend", "showstoppers": [],
    "gap_analysis": ["Go"], "recommendation": "להגיש", "formatted_message": "שווה להגיש",
}


class _Resolver:
    hireme_token = ""

    def resolve(self, url, job_id=None):
        return url


class _Scraper:
    def scrape(self, url, job_id=None, trace=None):
        return {"source": "jina", "full_description": "Junior Backend Developer. Requirements: Python, SQL. Experience: 1 year."}


class _Analyzer:
    model_name = "gemini-test"

    def analyze(self, resume, context, job):
        return {**ANALYSIS, "url": job["url"], "model": self.model_name}


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")


async def test_message_with_link_becomes_a_scored_job_in_the_db(db):
    await set_profile("resume", "Full Stack Developer: Python, React, SQL")

    async with _client() as client:
        r = await client.post("/api/jobs/raw", json={"text": MESSAGE})
        body = r.json()
        assert body["added"] == 1 and len(body["ignored"]) == 1
        job_id = body["added_jobs"][0]["id"]
        assert body["added_jobs"][0]["url"] == "https://jobs.lever.co/acme/123"

        assert (await client.get(f"/api/jobs/{job_id}")).json()["status"] == "PENDING_RESOLVE"

        # הצינור: כל worker מעבד את המשרה פעם אחת
        assert await worker_manager.resolve_next(_Resolver())
        assert await worker_manager.scrape_next(_Scraper())
        pool = ModelPool([(_Analyzer(), AIRateLimiter("gemini-test", rpm=0, rpd=0))])
        assert await worker_manager.analyze_next(pool)

        job = (await client.get(f"/api/jobs/{job_id}")).json()
        assert job["status"] == "COMPLETED"
        assert job["suitability_score"] == 78
        assert job["recommendation"] == "להגיש"
        assert job["company"] == "Acme" and job["job_title"] == "Junior Backend Developer"
        assert job["model"] == "gemini-test"

        # אותה הודעה שוב: לא נוצרת משרה חדשה, ומקבלים את ה-id של הקיימת (עם הציון)
        again = (await client.post("/api/jobs/raw", json={"text": MESSAGE})).json()
        assert again["added"] == 0
        assert again["skipped_urls"][0]["id"] == job_id


async def test_unknown_job_id_is_404_and_queue_route_still_works(db):
    async with _client() as client:
        assert (await client.get("/api/jobs/999999")).status_code == 404
        assert (await client.get("/api/jobs/queue")).status_code == 200
