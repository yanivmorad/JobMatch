import logging
import os
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# הוספת תיקיית src לנתיב
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.postgres import close_pool, get_pool
from routes.jobs_routes import router as jobs_router
from routes.profile_routes import router as profile_router
from scraper_service.resolvers import hiremetech_token_status
from services.auth import configured_token, require_api_token
from workers.worker_manager import (
    start_background_workers,
    stop_background_workers,
    workers_status,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Server")

STARTED_AT = time.time()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# הדשבורד הבנוי (npm run build). בענן ה-Dockerfile בונה אותו, והשרת מגיש אותו מאותה
# כתובת כמו ה-API - שירות אחד, בלי CORS. בפיתוח מריצים את Vite בנפרד (npm run dev).
DASHBOARD_DIR = os.getenv("DASHBOARD_DIR") or os.path.join(PROJECT_ROOT, "dashboard", "dist")


def _cors_origins() -> list:
    """CORS_ORIGINS="https://a.com,https://b.com" (ברירת מחדל: *). האימות הוא בטוקן ב-header, לא ב-cookies."""
    origins = [o.strip() for o in (os.getenv("CORS_ORIGINS") or "").split(",") if o.strip()]
    return origins or ["*"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting JobMatch Server...")
    if not configured_token():
        logger.warning("⚠️ API_TOKEN is not set - the API is open to anyone who can reach it (OK only locally)")
    await start_background_workers()
    yield
    logger.info("🛑 Shutting down...")
    await stop_background_workers()
    await close_pool()


app = FastAPI(title="JobMatch Lite", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# כל /api/* דורש את API_TOKEN (כשהוא מוגדר); /health פתוח
_auth = [Depends(require_api_token)]
app.include_router(jobs_router, prefix="/api", dependencies=_auth)
# הדשבורד קורא ל- /api/profile/resume ו- /api/profile/context
app.include_router(profile_router, prefix="/api/profile", dependencies=_auth)


@app.get("/ping")
async def ping():
    """
    בלי DB: ל-health check של Render ול-ping חיצוני ששומר את השירות ער (Render החינמי נרדם
    אחרי 15 דקות בלי תעבורה נכנסת). /health מריץ שאילתה, ושימוש בו לבדיקות התכופות האלה
    היה מונע מ-Neon להירדם ושורף את מכסת ה-CU-hours.
    """
    return {"ok": True}


@app.get("/health")
async def health():
    """
    מצב השירות: DB, ה-workers (חיים? מתי עבדו לאחרונה? מכסת Gemini) והטוקן של HireMeTech.
    503 אם ה-DB לא זמין או ש-worker מת - כך ש-health check של הפלטפורמה יזהה תקלה.
    """
    db = {"ok": False}
    try:
        t0 = time.time()
        pool = await get_pool()
        await pool.fetchval("SELECT 1")
        db = {"ok": True, "latency_ms": round((time.time() - t0) * 1000)}
    except Exception as e:
        db["error"] = f"{type(e).__name__}: {e}"[:200]

    workers = workers_status()
    all_running = all(w.get("running") for w in workers.values())
    body = {
        "status": "ok" if db["ok"] and all_running else "degraded",
        "uptime_seconds": round(time.time() - STARTED_AT),
        "db": db,
        "workers": workers,
        "hiremetech_token": hiremetech_token_status(),
    }
    return JSONResponse(body, status_code=200 if body["status"] == "ok" else 503)


# אחרון: "/" תופס כל נתיב, ולכן נרשם אחרי /api ו-/health
if os.path.isdir(DASHBOARD_DIR):
    app.mount("/", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
