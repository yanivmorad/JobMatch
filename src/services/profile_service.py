"""
הפרופיל של המועמד: קורות חיים (resume) והקשר אישי / כללי ניקוד (context).

המקור הקובע הוא טבלת profile ב-DB (עריכה בלשונית הפרופיל נשמרת שם ושורדת דיפלוי).
כשאין עדיין שורה ב-DB, הערך נטען פעם אחת ונשמר ב-DB, לפי הסדר:
  1. משתנה סביבה עם הטקסט:      RESUME_TEXT / PERSONAL_CONTEXT_TEXT
  2. משתנה סביבה עם נתיב לקובץ: RESUME_FILE / PERSONAL_CONTEXT_FILE
  3. Secret File של Render:      /etc/secrets/resume.txt, /etc/secrets/personal_context.txt
  4. הקבצים המקומיים:            data/resume.txt, "data/Personal Context.txt"
"""
import logging
import os
from typing import Optional

from db.postgres import get_pool
from services.file_utils import CONTEXT_PATH, RESUME_PATH, read_text_file

logger = logging.getLogger("JobMatchServer")

SECRETS_DIR = "/etc/secrets"

_SOURCES = {
    "resume": ("RESUME_TEXT", "RESUME_FILE", "resume.txt"),
    "context": ("PERSONAL_CONTEXT_TEXT", "PERSONAL_CONTEXT_FILE", "personal_context.txt"),
}


def _local_path(key: str) -> str:
    # נקרא בזמן ריצה (ולא בזמן import) כדי שבדיקות יוכלו להחליף את הנתיב
    return RESUME_PATH if key == "resume" else CONTEXT_PATH


def _initial_content(key: str) -> Optional[str]:
    text_var, file_var, secret_name = _SOURCES[key]
    text = (os.getenv(text_var) or "").strip()
    if text:
        return text
    for path in (os.getenv(file_var), os.path.join(SECRETS_DIR, secret_name), _local_path(key)):
        if path and os.path.exists(path):
            content = read_text_file(path)
            if content:
                return content
    return None


async def get_profile(key: str) -> str:
    if key not in _SOURCES:
        raise KeyError(key)
    pool = await get_pool()
    content = await pool.fetchval("SELECT content FROM profile WHERE key = $1", key)
    if content is not None:
        return content
    initial = _initial_content(key)
    if initial is None:
        logger.warning(f"⚠️ Profile '{key}' is empty (no DB row, env var, secret file or data/ file)")
        return ""
    # ON CONFLICT: אם בקשה אחרת שמרה בינתיים - לא דורסים
    await pool.execute(
        "INSERT INTO profile (key, content) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING", key, initial
    )
    logger.info(f"📄 Profile '{key}' seeded into the DB ({len(initial)} chars)")
    return await pool.fetchval("SELECT content FROM profile WHERE key = $1", key)


async def set_profile(key: str, content: str) -> None:
    if key not in _SOURCES:
        raise KeyError(key)
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO profile (key, content, updated_at) VALUES ($1, $2, NOW())
        ON CONFLICT (key) DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
        """,
        key,
        content,
    )
    logger.info(f"✅ Profile '{key}' updated: {len(content)} characters")


async def get_resume_content() -> str:
    return await get_profile("resume")


async def update_resume_content(content: str):
    await set_profile("resume", content)


async def get_context_content() -> str:
    return await get_profile("context")


async def update_context_content(content: str):
    await set_profile("context", content)
