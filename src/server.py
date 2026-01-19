# src/server.py
import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.jobs_routes import router as jobs_router
from routes.profile_routes import router as profile_router

# --- הגדרות לוגינג כלליות ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("server.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("JobMatchServer")

app = FastAPI(title="JobMatch API", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # בסביבת ייצור כדאי להגביל
    allow_methods=["*"],
    allow_headers=["*"],
)

# רישום ראוטרים
app.include_router(jobs_router, prefix="/api")
app.include_router(profile_router, prefix="/api/profile")


if __name__ == "__main__":
    # וודא שתיקיית data קיימת
    from services.file_utils import DATA_DIR

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    print("🚀 Server starting on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
