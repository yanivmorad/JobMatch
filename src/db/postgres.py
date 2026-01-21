# src/db/postgres.py
import logging
import os

import asyncpg
from dotenv import load_dotenv

logger = logging.getLogger("JobMatchServer")

load_dotenv()

DB_CONFIG = {
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD"),
    "database": os.getenv("PG_DB"),
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", 5432)),
}
_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        # פונקציה שתרוץ על כל חיבור חדש - רק כדי ללמד אותו להכיר את ה-Enum
        async def setup_connection(conn):
            await conn.set_type_codec(
                "job_status", schema="public", encoder=str, decoder=str
            )

        # יצירת ה-Pool
        _pool = await asyncpg.create_pool(**DB_CONFIG, setup=setup_connection)

        # --- אתחול חד פעמי של הטבלאות ---
        # אנחנו לוקחים חיבור אחד באופן יזום ומריצים עליו את ההקמה
        async with _pool.acquire() as conn:
            await init_db(conn)

    return _pool


async def init_db(conn):
    """יוצר את הטיפוסים והטבלאות אם הם לא קיימים"""
    # בדיקה מהירה אם הטבלה קיימת כדי לא להציף את הלוגים סתם
    table_exists = await conn.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'jobs')"
    )

    if not table_exists:
        logger.info("🛠️ Initializing Database schema...")

        # 1. יצירת ה-Enum
        await conn.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
                    CREATE TYPE job_status AS ENUM (
                        'NEW', 'WAITING_FOR_SCRAPE', 'SCRAPING', 'WAITING_FOR_AI', 
                        'ANALYZING', 'COMPLETED', 'FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA'
                    );
                END IF;
            END $$;
        """)

        # 2. יצירת הטבלה
        await conn.execute("""
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
                is_archived BOOLEAN DEFAULT FALSE,
                error_log TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                scraped_at TIMESTAMP WITH TIME ZONE,
                analyzed_at TIMESTAMP WITH TIME ZONE
            );
        """)

        # 3. אינדקס
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);"
        )
        logger.info("✅ Database schema is ready.")
