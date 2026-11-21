import logging
import os
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# הוספת תיקיית src לנתיב
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.postgres import close_pool, get_pool
from routes.jobs_routes import router as jobs_router
from routes.profile_routes import router as profile_router
from scraper_service.resolvers import hiremetech_token_status
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting JobMatch Server...")
    await start_background_workers()
    yield
    logger.info("🛑 Shutting down...")
    await stop_background_workers()
    await close_pool()


app = FastAPI(title="JobMatch Lite", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router, prefix="/api")
# הדשבורד קורא ל- /api/profile/resume ו- /api/profile/context
app.include_router(profile_router, prefix="/api/profile")


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


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
