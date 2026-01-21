# src/server.py
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.jobs_routes import router as jobs_router
from routes.profile_routes import router as profile_router
from workers.worker_manager import start_background_workers

# --- לוגינג ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("Server")


# --- Lifespan (מחליף את startup event) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # קוד שרץ בעליית השרת
    logger.info("🚀 Starting JobMatch Server & Workers...")
    await start_background_workers()
    yield
    # קוד שרץ בירידת השרת (אם נצטרך בעתיד לסגור חיבורים)
    logger.info("🛑 Shutting down server...")


app = FastAPI(title="JobMatch SQL API", version="2.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router, prefix="/api")
app.include_router(profile_router, prefix="/api/profile")

if __name__ == "__main__":
    from services.file_utils import DATA_DIR

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
