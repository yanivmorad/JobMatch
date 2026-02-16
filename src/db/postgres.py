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

    # --- MIGRATION: Ensure all job_status enum values exist ---
    # Note: ADD VALUE IF NOT EXISTS requires Postgres 12+
    await conn.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
                CREATE TYPE job_status AS ENUM (
                    'NEW', 'PENDING_RESOLVE', 'RESOLVING', 'WAITING_FOR_SCRAPE', 
                    'SCRAPING', 'WAITING_FOR_AI', 'ANALYZING', 'COMPLETED', 
                    'FAILED_RESOLVE', 'FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA',
                    'DUPLICATE'
                );
            ELSE
                BEGIN
                    ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'PENDING_RESOLVE';
                EXCEPTION WHEN others THEN NULL; END;
                
                BEGIN
                    ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'RESOLVING';
                EXCEPTION WHEN others THEN NULL; END;
                
                BEGIN
                    ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'FAILED_RESOLVE';
                EXCEPTION WHEN others THEN NULL; END;

                BEGIN
                    ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'DUPLICATE';
                EXCEPTION WHEN others THEN NULL; END;
            END IF;
        END $$;
    """)

    # --- MIGRATION: Ensure updated_at column and trigger exist ---
    await conn.execute("""
        DO $$ 
        BEGIN
            -- 1. Check for column
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'jobs' AND column_name = 'updated_at') THEN
                ALTER TABLE jobs ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
            END IF;

            -- 2. Create function
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $inner$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $inner$ language 'plpgsql';

            -- 3. Create trigger
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_jobs_updated_at') THEN
                CREATE TRIGGER update_jobs_updated_at
                BEFORE UPDATE ON jobs
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
    """)

    if not table_exists:
        logger.info("🛠️ Initializing Database schema...")

        # 2. יצירת פונקציית טריגר לעדכון updated_at
        await conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)

        # 3. יצירת הטבלה
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
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                scraped_at TIMESTAMP WITH TIME ZONE,
                analyzed_at TIMESTAMP WITH TIME ZONE
            );
        """)

        # 4. יצירת הטריגר
        await conn.execute("""
            DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
            CREATE TRIGGER update_jobs_updated_at
            BEFORE UPDATE ON jobs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """)

        # 5. אינדקסים
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at);"
        )
        logger.info("✅ Database schema is ready with updated_at trigger.")
