import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# הוספת תיקיית src לנתיב
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# מייבאים רק את מה שקיים אצלך בוודאות
from routes.jobs_routes import router as jobs_router
from workers.worker_manager import start_background_workers

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting JobMatch Server...")
    await start_background_workers()
    yield
    logger.info("🛑 Shutting down...")


app = FastAPI(title="JobMatch Lite", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# חיבור הראוטר של המשרות בלבד
app.include_router(jobs_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
