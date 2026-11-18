# src/db/postgres.py
import asyncio
import logging
import os

import asyncpg
from dotenv import load_dotenv

logger = logging.getLogger("JobMatchServer")

load_dotenv()

_pool = None
_pool_lock = None

# כל הערכים של ה-Enum. ערכים חדשים מתווספים כאן בלבד (ADD VALUE IF NOT EXISTS).
JOB_STATUSES = (
    "NEW",
    "PENDING_RESOLVE",
    "RESOLVING",
    "WAITING_FOR_SCRAPE",
    "SCRAPING",
    "WAITING_FOR_AI",
    "ANALYZING",
    "COMPLETED",
    "FAILED_RESOLVE",
    "FAILED_SCRAPE",
    "FAILED_ANALYSIS",
    "NO_DATA",
    "DUPLICATE",
)


def _connect_kwargs() -> dict:
    """
    DATABASE_URL (Neon / Supabase / Render) מקבל עדיפות.
    אחרת - משתני PG_* הישנים, לסביבה מקומית.
    נקרא בזמן יצירת ה-pool (ולא בזמן import) כדי שאפשר יהיה להחליף DB בבדיקות.
    """
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        return {"dsn": dsn}
    return {
        "user": os.getenv("PG_USER"),
        "password": os.getenv("PG_PASSWORD"),
        "database": os.getenv("PG_DB"),
        "host": os.getenv("PG_HOST", "localhost"),
        "port": int(os.getenv("PG_PORT", 5432)),
    }


async def get_pool():
    global _pool, _pool_lock
    if _pool is not None:
        return _pool

    if _pool_lock is None:
        _pool_lock = asyncio.Lock()

    async with _pool_lock:
        if _pool is None:
            # הערה: asyncpg מחזיר ערכי Enum כ-str כברירת מחדל, ולכן אין צורך ב-set_type_codec.
            # (הקריאה הקודמת ל-set_type_codec נכשלה על DB ריק, כי הטיפוס עוד לא היה קיים)
            pool = await asyncpg.create_pool(**_connect_kwargs())
            try:
                async with pool.acquire() as conn:
                    await init_db(conn)
            except Exception:
                await pool.close()
                raise
            _pool = pool

    return _pool


async def close_pool():
    """סוגר את ה-pool (בכיבוי השרת ובין בדיקות)."""
    global _pool, _pool_lock
    if _pool is not None:
        await _pool.close()
    _pool = None
    _pool_lock = None


async def init_db(conn):
    """
    יוצר / מעדכן את הסכמה. כל הפעולות idempotent, כך שבטוח להריץ שוב ושוב:
    על DB ריק (Docker / Neon) ועל DB קיים שנוצר בגרסה ישנה.
    """
    # 1. טיפוס הסטטוס
    await conn.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
                CREATE TYPE job_status AS ENUM ('NEW');
            END IF;
        END $$;
        """
    )
    # כל ערך בנפרד: ADD VALUE IF NOT EXISTS (Postgres 12+)
    for status in JOB_STATUSES:
        await conn.execute(f"ALTER TYPE job_status ADD VALUE IF NOT EXISTS '{status}'")

    # 2. הטבלה (נוצרת רק אם לא קיימת)
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            status job_status DEFAULT 'NEW',
            company TEXT DEFAULT 'Identifying...',
            job_title TEXT DEFAULT 'Identifying...',
            source TEXT,
            full_description TEXT,
            analysis_result JSONB,
            user_action TEXT DEFAULT 'none',
            application_status TEXT DEFAULT 'pending',
            is_archived BOOLEAN DEFAULT FALSE,
            error_log TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            scraped_at TIMESTAMP WITH TIME ZONE,
            analyzed_at TIMESTAMP WITH TIME ZONE
        );
        """
    )

    # 3. Migrations לטבלאות שנוצרו בגרסאות קודמות
    await conn.execute(
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
    )
    await conn.execute(
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_status TEXT DEFAULT 'pending'"
    )

    # 4. טריגר updated_at
    await conn.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    await conn.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_jobs_updated_at') THEN
                CREATE TRIGGER update_jobs_updated_at
                BEFORE UPDATE ON jobs
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
        """
    )

    # 5. אינדקסים
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at)"
    )
    logger.info("✅ Database schema is ready")
