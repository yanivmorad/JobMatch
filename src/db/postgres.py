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
        # asyncpg מחזיר ערכי Enum כמחרוזות כברירת מחדל, אין צורך ב-codec
        _pool = await asyncpg.create_pool(**DB_CONFIG)

        # אתחול חד פעמי של הסכמה
        async with _pool.acquire() as conn:
            await init_db(conn)

    return _pool


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


async def init_db(conn):
    """
    יוצר/מעדכן את הסכמה. כל הפעולות אידמפוטנטיות, כך שבטוח להריץ
    גם על מסד ריק וגם על מסד קיים מגרסה ישנה.
    """
    # 1. טיפוס הסטטוס (Enum) + הוספת ערכים חסרים במסדים ישנים
    enum_values = ", ".join(f"'{v}'" for v in JOB_STATUSES)
    await conn.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
                CREATE TYPE job_status AS ENUM ({enum_values});
            END IF;
        END $$;
    """)
    for value in JOB_STATUSES:
        await conn.execute(f"ALTER TYPE job_status ADD VALUE IF NOT EXISTS '{value}'")

    # 2. הטבלה עצמה
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
            application_status TEXT DEFAULT 'pending',
            is_archived BOOLEAN DEFAULT FALSE,
            error_log TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            scraped_at TIMESTAMP WITH TIME ZONE,
            analyzed_at TIMESTAMP WITH TIME ZONE,
            applied_at TIMESTAMP WITH TIME ZONE
        );
    """)

    # 3. עמודות שנוספו בגרסאות מאוחרות (למסדים קיימים)
    await conn.execute("""
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_status TEXT DEFAULT 'pending';
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS applied_at TIMESTAMP WITH TIME ZONE;
    """)

    # 4. טריגר לעדכון updated_at
    await conn.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
        CREATE TRIGGER update_jobs_updated_at
        BEFORE UPDATE ON jobs
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # 5. אינדקסים
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at);
    """)
    logger.info("✅ Database schema is ready.")
