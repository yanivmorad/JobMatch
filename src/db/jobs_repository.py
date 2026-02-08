# src/db/jobs_repository.py
import json
import logging
from enum import Enum
from typing import List, Optional

from db.postgres import get_pool

logger = logging.getLogger("Repository")

# --- כתיבה / עדכון (עבור Workers & Intake) ---


async def add_new_job(
    url: str, source: str = "web", manual_text: str = None, manual_meta: dict = None
) -> bool:
    pool = await get_pool()
    status = "WAITING_FOR_AI" if manual_text else "WAITING_FOR_SCRAPE"
    company = manual_meta.get("company", url) if manual_meta else url
    title = manual_meta.get("title", url) if manual_meta else url

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


async def get_job_by_url(url: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM jobs WHERE url = $1", url)
    return dict(row) if row else None


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
    is_archived = action != "none"

    # סנכרון עם ה-Logic החדש של application_status
    app_status = "pending"
    if action == "applied":
        app_status = "applied"
    elif action == "ignored":
        app_status = "not_relevant"

    # חשוב מאוד: הסדר של המשתנים בתוך ה-execute חייב להתאים ל-$1, $2, $3, $4
    await pool.execute(
        """
        UPDATE jobs 
        SET user_action = $1, 
            is_archived = $2,
            application_status = $3
        WHERE url = $4
        """,
        action,
        is_archived,
        app_status,
        url,
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
            scraped_at = NOW(),
            is_archived = FALSE,
            error_log = NULL
        WHERE url = $1
        """,
        url,
        company,
        title,
        description,
    )


class ApplicationStatus(str, Enum):
    PENDING = "pending"  # משרה חדשה שעוד לא טופלה
    NOT_RELEVANT = "not_relevant"  # הוחלט לא להגיש
    APPLIED = "applied"  # הוגשה מועמדות
    PHONE_SCREEN = "phone_screen"  # שיחת טלפון ראשונית
    INTERVIEW = "interview"  # תהליך ראיונות
    REJECTED = "rejected"  # התקבלה דחייה
    GHOSTED = "ghosted"  # לא ענו הרבה זמן


async def update_application_status(
    url: str, status: ApplicationStatus, is_archived: Optional[bool] = None
):
    pool = await get_pool()

    # לוגיקה אוטומטית: אם זה דחייה, לא רלוונטי או ללא מענה, נרצה לארכב
    if is_archived is None:
        is_archived = status in [
            ApplicationStatus.NOT_RELEVANT,
            ApplicationStatus.REJECTED,
            ApplicationStatus.GHOSTED,
        ]

    # סנכרון עם ה-Logic הישן של user_action
    user_action = "none"
    if status == ApplicationStatus.APPLIED:
        user_action = "applied"
    elif status in [ApplicationStatus.NOT_RELEVANT, ApplicationStatus.REJECTED]:
        user_action = "ignored"

    await pool.execute(
        """
        UPDATE jobs 
        SET application_status = $1,
            user_action = $2,
            is_archived = $3
        WHERE url = $4
        """,
        status.value,
        user_action,
        is_archived,
        url,
    )


async def auto_archive_old_applications():
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE jobs 
        SET application_status = 'ghosted' 
        WHERE application_status = 'applied' 
        AND created_at < NOW() - INTERVAL '30 days'
        """
    )


async def clear_archived_jobs():
    """מוחק את כל המשרות שסומנו כארכיון (כמו הפונקציה הישנה שלך)"""
    pool = await get_pool()
    await pool.execute("DELETE FROM jobs WHERE is_archived = TRUE")


async def retry_job(url: str):
    """מאתחל משרה חזרה לתחילת התור (סריקה) ומנקה שגיאות"""
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE jobs 
        SET status = 'WAITING_FOR_SCRAPE', 
            error_log = NULL,
            is_archived = FALSE
        WHERE url = $1
        """,
        url,
    )


async def reset_stuck_jobs():
    """מאפס משרות שנתקעו במצב 'בסריקה' או 'בניתוח' חזרה לתור (למקרה של קריסת שרת)"""
    pool = await get_pool()
    await pool.execute(
        "UPDATE jobs SET status = 'WAITING_FOR_SCRAPE' WHERE status = 'SCRAPING'"
    )
    await pool.execute(
        "UPDATE jobs SET status = 'WAITING_FOR_AI' WHERE status = 'ANALYZING'"
    )
