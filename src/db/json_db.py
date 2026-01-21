# src/db/json_db.py
import asyncio
import json
import logging
import os
from typing import List, Optional

from services.file_utils import RESULTS_FILE

logger = logging.getLogger("JobMatchServer")
DB_LOCK = asyncio.Lock()

# --- פונקציות עזר סינכרוניות (לשימוש בתוך Threads) ---


def _read_db_sync() -> List[dict]:
    if not os.path.exists(RESULTS_FILE):
        return []
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error reading DB file: {e}")
        return []


def _save_db_sync(db_content: List[dict]):
    try:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(db_content, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error writing to DB file: {e}")


# --- פונקציות API ציבוריות (אסינכרוניות) ---


async def load_db() -> List[dict]:
    async with DB_LOCK:
        return await asyncio.to_thread(_read_db_sync)


async def update_job_in_db(job_data: dict):
    """עדכון משרה קיים או הוספת חדש בצורה אטומית"""
    async with DB_LOCK:
        db = await asyncio.to_thread(_read_db_sync)

        target_url = job_data.get("url")
        if not target_url:
            return

        existing_job = next((j for j in db if j["url"] == target_url), None)

        if existing_job:
            # עדכון שדות קיימים בלבד (מונע דריסה של שדות שלא נשלחו)
            existing_job.update(job_data)
        else:
            db.append(job_data)

        await asyncio.to_thread(_save_db_sync, db)


async def get_job_by_url(url: str) -> Optional[dict]:
    db = await load_db()
    return next((item for item in db if item["url"] == url), None)


async def delete_job_by_url(url: str) -> bool:
    """מחיקת משרה בודדת לפי URL"""
    async with DB_LOCK:
        db = await asyncio.to_thread(_read_db_sync)
        initial_count = len(db)
        new_db = [j for j in db if j["url"] != url]

        if len(new_db) == initial_count:
            return False

        await asyncio.to_thread(_save_db_sync, new_db)
        return True


async def clear_history_db():
    """מחיקת כל המשרות שבארכיון (שאורכבו ולא הוגשו)"""
    async with DB_LOCK:
        db = await asyncio.to_thread(_read_db_sync)
        # שומרים רק משרות שלא אורכבו, או כאלו שאורכבו אבל סומנו כ-"Applied"
        new_db = [
            j
            for j in db
            if not (j.get("is_archived") and j.get("user_action") != "applied")
        ]
        await asyncio.to_thread(_save_db_sync, new_db)
