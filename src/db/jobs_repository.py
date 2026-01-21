# src/db/jobs_repository.py
import json
import logging
from typing import List, Optional

from db.postgres import get_pool

logger = logging.getLogger("Repository")

# --- כתיבה / עדכון (עבור Workers & Intake) ---


async def add_new_job(
    url: str, source: str = "web", manual_text: str = None, manual_meta: dict = None
) -> bool:
    pool = await get_pool()
    status = "WAITING_FOR_AI" if manual_text else "WAITING_FOR_SCRAPE"
    company = (
        manual_meta.get("company", "Identifying...")
        if manual_meta
        else "Identifying..."
    )
    title = (
        manual_meta.get("title", "Identifying...") if manual_meta else "Identifying..."
    )

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            INSERT INTO jobs (url, status, source, full_description, company, job_title)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (url) DO NOTHING
            """,
            url,
            status,
            source,
            manual_text,
            company,
            title,
        )
        # conn.execute מחזיר מחרוזת כמו "INSERT 0 1" אם נוספה שורה, או "INSERT 0 0" אם לא
        return " 1" in result


async def fetch_next_job(current_status: str, next_status: str) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                f"""
                UPDATE jobs 
                SET status = '{next_status}'
                WHERE id = (
                    SELECT id FROM jobs 
                    WHERE status = '{current_status}' 
                    ORDER BY created_at ASC 
                    LIMIT 1 
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING *
                """
            )
            return dict(row) if row else None


async def finish_scrape(job_id: int, company: str, title: str, description: str):
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE jobs SET 
            status = 'WAITING_FOR_AI',
            company = $2,
            job_title = $3,
            full_description = $4,
            scraped_at = NOW()
        WHERE id = $1
        """,
        job_id,
        company,
        title,
        description,
    )


async def finish_analysis(job_id: int, result: dict):
    pool = await get_pool()
    # המרת dict ל-json string עבור ה-DB
    json_result = json.dumps(result)
    await pool.execute(
        "UPDATE jobs SET status = 'COMPLETED', analysis_result = $2, analyzed_at = NOW() WHERE id = $1",
        job_id,
        json_result,
    )


async def mark_failed(job_id: int, status: str, error: str):
    pool = await get_pool()
    await pool.execute(
        "UPDATE jobs SET status = $2, error_log = $3 WHERE id = $1",
        job_id,
        status,
        error,
    )


# --- קריאה (עבור API) ---


async def get_all_jobs() -> List[dict]:
    """מחזיר את כל המשרות ממוינות לפי תאריך יצירה"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM jobs ORDER BY created_at DESC")
        # המרה לרשימה של מילונים
        results = []
        for row in rows:
            job = dict(row)
            # אם יש תוצאות AI, נפרק את ה-JSONB חזרה לשדות שטוחים
            analysis = job.get("analysis_result")
            if analysis:
                if isinstance(analysis, str):
                    try:
                        analysis = json.loads(analysis)
                    except:
                        analysis = {}
                if isinstance(analysis, dict):
                    job.update(analysis)
            results.append(job)
        return results


async def delete_job_by_url(url: str):
    pool = await get_pool()
    await pool.execute("DELETE FROM jobs WHERE url = $1", url)


async def update_user_action(url: str, action: str):
    """מעדכן אם המשתמש הגיש מועמדות או התעלם"""
    pool = await get_pool()
    # אם המשתמש בחר פעולה שהיא לא 'none', אנחנו מארכבים את המשרה אוטומטית
    is_archived = action != "none"

    await pool.execute(
        "UPDATE jobs SET user_action = $2, is_archived = $3 WHERE url = $1",
        url,
        action,
        is_archived,
    )


async def update_manual_job(url: str, company: str, title: str, description: str):
    """מעדכן פרטי משרה באופן ידני ומעביר אותה לתור ה-AI"""
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE jobs SET 
            status = 'WAITING_FOR_AI',
            company = $2,
            job_title = $3,
            full_description = $4,
            scraped_at = NOW()
        WHERE url = $1
        """,
        url,
        company,
        title,
        description,
    )


async def clear_archived_jobs():
    """מוחק את כל המשרות שסומנו כארכיון (כמו הפונקציה הישנה שלך)"""
    pool = await get_pool()
    await pool.execute("DELETE FROM jobs WHERE is_archived = TRUE")
