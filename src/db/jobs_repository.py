import json
import logging
from enum import Enum
from typing import List, Optional

from db.postgres import get_pool

logger = logging.getLogger("Repository")

# --- הגדרות וסטטוסים ---


class ApplicationStatus(str, Enum):
    """מייצג את מצב התקדמות הגשת המועמדות של המשתמש מול החברה"""

    PENDING = "pending"  # משרה חדשה במערכת
    NOT_RELEVANT = "not_relevant"  # החלטה לא להגיש
    APPLIED = "applied"  # הוגשה מועמדות בפועל
    PHONE_SCREEN = "phone_screen"  # שיחת טלפון ראשונית
    INTERVIEW = "interview"  # שלב ראיונות
    REJECTED = "rejected"  # התקבלה דחייה
    GHOSTED = "ghosted"  # ארכיון אוטומטי (ללא מענה מעל 30 יום)


# --- פונקציות יצירה וניהול תור (Pipeline) ---


async def add_new_job(
    url: str, source: str = "web", manual_text: str = None, manual_meta: dict = None
) -> bool:
    """
    נקודת הכניסה הראשית למשרה במערכת.
    יכולת: מחליטה אם לשלוח את המשרה לפיענוח לינק (PENDING_RESOLVE)
    או ישירות לניתוח AI (WAITING_FOR_AI) אם הטקסט כבר קיים.
    """
    pool = await get_pool()
    status = "WAITING_FOR_AI" if manual_text else "PENDING_RESOLVE"
    company = (manual_meta or {}).get("company", url)
    title = (manual_meta or {}).get("title", url)

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
        return " 1" in result


async def fetch_next_job(current_status: str, next_status: str) -> Optional[dict]:
    """
    יכולת קריטית: ניהול תור העבודה של ה-Workers.
    זרימה: מוצאת משרה בסטטוס המבוקש, נועלת אותה כדי שוורקר אחר לא יקח אותה (SKIP LOCKED),
    ומעדכנת אותה מיד לסטטוס הבא כדי לסמן שהיא בטיפול.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                UPDATE jobs 
                SET status = $1, updated_at = NOW()
                WHERE id = (
                    SELECT id FROM jobs 
                    WHERE status = $2 
                    ORDER BY created_at ASC 
                    LIMIT 1 
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING *
                """,
                next_status,
                current_status,
            )
            return dict(row) if row else None


async def update_job_after_resolution(job_id: int, new_url: str, status: str):
    """מעדכן את הלינק הסופי (למשל אחרי מעבר דרך לינקים מקוצרים) ומעביר לשלב הסריקה."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE jobs SET url = $1, status = $2, error_log = NULL, updated_at = NOW() WHERE id = $3",
        new_url,
        status,
        job_id,
    )


async def finish_scrape(job_id: int, company: str, title: str, description: str):
    """שומר את המידע שחולץ מהאתר (Scraping) ומעביר את המשרה לתור ה-AI."""
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE jobs SET 
            status = 'WAITING_FOR_AI', company = $2, job_title = $3, 
            full_description = $4, scraped_at = NOW(), updated_at = NOW()
        WHERE id = $1
        """,
        job_id,
        company,
        title,
        description,
    )


async def finish_analysis(job_id: int, result: dict):
    """שומר את תוצאות הניתוח הסופיות של ה-LLM ומסמן את התהליך כהושלם (COMPLETED)."""
    pool = await get_pool()
    json_result = json.dumps(result) if isinstance(result, dict) else result
    await pool.execute(
        "UPDATE jobs SET status = 'COMPLETED', analysis_result = $2, analyzed_at = NOW() WHERE id = $1",
        job_id,
        json_result,
    )


async def mark_failed(job_id: int, status: str, error_msg: str):
    """מתעד שגיאה שקרתה במהלך הצינור (סריקה/AI) כדי לאפשר דיבאגינג מה-UI."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE jobs SET status = $2, error_log = $3, updated_at = NOW() WHERE id = $1",
        job_id,
        status,
        error_msg,
    )


async def manual_update_job_content(job_id: int, manual_description: str):
    """
    לוקח משרה קיימת, מזריק לה תוכן ידני ומקפיץ אותה ישר לניתוח AI.
    מדלג על שלב ה-Resolve וה-Scrape.
    """
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE jobs 
        SET full_description = $1, 
            status = 'WAITING_FOR_AI', 
            error_log = NULL,
            updated_at = NOW()
        WHERE id = $2
        """,
        manual_description,
        job_id,
    )


# --- פונקציות קריאה (API & UI) ---


async def get_all_jobs() -> List[dict]:
    """
    יכולת: שליפת כל המשרות לממשק המשתמש.
    לוגיקה: הופכת את ה-JSON של הניתוח לשדות שטוחים (כמו score, summary) כדי להקל על ה-Frontend.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM jobs ORDER BY created_at DESC")
        results = []
        for row in rows:
            job = dict(row)
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


async def get_job_by_url(url: str) -> Optional[dict]:
    """שליפת מידע מלא על משרה בודדת לפי כתובת ה-URL שלה."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM jobs WHERE url = $1", url)
    return dict(row) if row else None


# --- עדכוני סטטוס ופעולות משתמש ---


async def update_user_action(url: str, action: str):
    """עדכון מהיר של פעולת משתמש (הגשתי/התעלמתי) וסנכרון הארכיון."""
    pool = await get_pool()
    is_archived = action != "none"
    app_status = "pending"
    if action == "applied":
        app_status = "applied"
    elif action == "ignored":
        app_status = "not_relevant"

    await pool.execute(
        """
        UPDATE jobs 
        SET user_action = $1, is_archived = $2, application_status = $3
        WHERE url = $4
        """,
        action,
        is_archived,
        app_status,
        url,
    )


async def update_application_status(
    url: str, status: ApplicationStatus, is_archived: Optional[bool] = None
):
    """עדכון סטטוס מפורט (ראיון, דחייה וכו') וניהול אוטומטי של העברה לארכיון."""
    pool = await get_pool()
    if is_archived is None:
        is_archived = status in [
            ApplicationStatus.NOT_RELEVANT,
            ApplicationStatus.REJECTED,
            ApplicationStatus.GHOSTED,
        ]

    user_action = "none"
    if status == ApplicationStatus.APPLIED:
        user_action = "applied"
    elif status in [ApplicationStatus.NOT_RELEVANT, ApplicationStatus.REJECTED]:
        user_action = "ignored"

    await pool.execute(
        """
        UPDATE jobs 
        SET application_status = $1, user_action = $2, is_archived = $3
        WHERE url = $4
        """,
        status.value,
        user_action,
        is_archived,
        url,
    )


async def update_manual_job(url: str, company: str, title: str, description: str):
    """מאפשר למשתמש לערוך פרטי משרה ב-UI ולשלוח אותה לניתוח AI מחדש."""
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE jobs SET 
            status = 'WAITING_FOR_AI', company = $2, job_title = $3, 
            full_description = $4, scraped_at = NOW(), is_archived = FALSE, error_log = NULL
        WHERE url = $1
        """,
        url,
        company,
        title,
        description,
    )


# --- תחזוקה, מחיקה ושיקום ---


async def retry_job(url: str):
    """מחזיר משרה שנכשלה לשלב הסריקה לניסיון נוסף."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE jobs SET status = 'WAITING_FOR_SCRAPE', error_log = NULL, is_archived = FALSE WHERE url = $1",
        url,
    )


async def reset_stuck_jobs():
    """מנגנון בטיחות: משחרר משרות שנתקעו בסטטוס 'בטיפול' אם השרת קרס באמצע עבודה."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE jobs SET status = 'PENDING_RESOLVE' WHERE status = 'RESOLVING'"
    )

    await pool.execute(
        "UPDATE jobs SET status = 'WAITING_FOR_SCRAPE' WHERE status = 'SCRAPING'"
    )
    await pool.execute(
        "UPDATE jobs SET status = 'WAITING_FOR_AI' WHERE status = 'ANALYZING'"
    )


async def auto_archive_old_applications():
    """יכולת: ניקוי אוטומטי של תהליכים ישנים שבהם המעסיק לא הגיב מעל 30 יום."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE jobs SET application_status = 'ghosted' WHERE application_status = 'applied' AND created_at < NOW() - INTERVAL '30 days'"
    )


async def clear_archived_jobs():
    """מחיקה פיזית של כל המשרות שסומנו כארכיון."""
    pool = await get_pool()
    await pool.execute("DELETE FROM jobs WHERE is_archived = TRUE")


async def delete_job_by_url(url: str):
    """מחיקת משרה לפי כתובת URL."""
    pool = await get_pool()
    await pool.execute("DELETE FROM jobs WHERE url = $1", url)


async def delete_job_by_id(job_id: int):
    """מחיקת משרה לפי מזהה פנימי (ID)."""
    pool = await get_pool()
    await pool.execute("DELETE FROM jobs WHERE id = $1", job_id)
