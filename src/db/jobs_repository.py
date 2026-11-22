import json
import logging
from enum import Enum
from typing import List, Optional

from db.postgres import get_pool
from services.job_fields import PLACEHOLDER_VALUES, clean_field

logger = logging.getLogger("Repository")

# שדות שה-DB הוא המקור הקובע עבורם; ה-JSON של הניתוח לא דורס אותם בתצוגה
_PROTECTED_FIELDS = {"id", "url", "status", "company", "job_title"}

# SQL: האם הערך הנוכחי בעמודה הוא placeholder (ואז מותר לדרוס אותו בערך שחולץ)
_IS_PLACEHOLDER_SQL = (
    "({col} IS NULL OR lower(btrim({col})) = ANY($5::text[]) "
    "OR {col} ~* '^(https?://|manual)')"
)

# הערת "ניסיון N/3, מנסה שוב" (fail_or_retry) נמחקת כשהשלב מצליח; הערות אחרות
# (למשל "HireMeTech: הטוקן פג - נותח לפי הדף הציבורי") נשארות
_RETRY_NOTE_SUFFIX = "מנסה שוב)"
_CLEAR_RETRY_NOTE_SQL = f"CASE WHEN error_log LIKE '%{_RETRY_NOTE_SUFFIX}' THEN NULL ELSE error_log END"

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


# applied_at: מתי הוגשה המועמדות. מתמלא במעבר לאחד משלבי ההגשה (ונשמר אם כבר קיים -
# מעבר מ-applied לראיון לא מאפס אותו), ומתאפס בחזרה ל-pending.
_APPLIED_STAGES = (
    ApplicationStatus.APPLIED.value,
    ApplicationStatus.PHONE_SCREEN.value,
    ApplicationStatus.INTERVIEW.value,
)


def _applied_at_sql(status_param: str, stages_param: str = "$5") -> str:
    """ביטוי SQL ל-applied_at. status_param = הפרמטר עם הסטטוס החדש, stages_param = _APPLIED_STAGES."""
    return (
        f"CASE WHEN {status_param} = ANY({stages_param}::text[]) THEN COALESCE(applied_at, NOW()) "
        f"WHEN {status_param} = 'pending' THEN NULL ELSE applied_at END"
    )


# --- פונקציות יצירה וניהול תור (Pipeline) ---


async def add_new_job(
    url: str, source: str = "web", manual_text: str = None, manual_meta: dict = None
) -> Optional[int]:
    """
    נקודת הכניסה הראשית למשרה במערכת.
    יכולת: מחליטה אם לשלוח את המשרה לפיענוח לינק (PENDING_RESOLVE)
    או ישירות לניתוח AI (WAITING_FOR_AI) אם הטקסט כבר קיים.
    מחזיר את ה-id של המשרה החדשה, או None אם כבר קיימת (כך שאפשר להמשיך להשתמש בו כ-bool).
    """
    pool = await get_pool()
    status = "WAITING_FOR_AI" if manual_text else "PENDING_RESOLVE"
    company = (manual_meta or {}).get("company", url)
    title = (manual_meta or {}).get("title", url)

    return await pool.fetchval(
        """
        INSERT INTO jobs (url, source_url, status, source, full_description, company, job_title)
        VALUES ($1, $1, $2, $3, $4, $5, $6)
        ON CONFLICT (url) DO NOTHING
        RETURNING id
        """,
        url,
        status,
        source,
        manual_text,
        company,
        title,
    )


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
                SET status = $1, updated_at = NOW(), not_before = NULL
                WHERE id = (
                    SELECT id FROM jobs
                    WHERE status = $2 AND (not_before IS NULL OR not_before <= NOW())
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


async def update_job_after_resolution(
    job_id: int, new_url: str, status: str, note: Optional[str] = None
):
    """
    מעדכן את הלינק הסופי (למשל אחרי מעבר דרך לינקים מקוצרים) ומעביר לשלב הסריקה.
    note: הערה למשתמש (נשמרת ב-error_log), למשל "הטוקן פג - נותח לפי הדף הציבורי".
    """
    pool = await get_pool()
    await pool.execute(
        "UPDATE jobs SET url = $1, status = $2, error_log = $4, updated_at = NOW() WHERE id = $3",
        new_url,
        status,
        job_id,
        note,
    )


async def finish_scrape(
    job_id: int,
    description: str,
    company: Optional[str] = None,
    title: Optional[str] = None,
):
    """
    שומר את המידע שחולץ מהאתר (Scraping) ומעביר את המשרה לתור ה-AI.
    company/title נשמרים רק אם הסורק באמת מצא אותם (אחרת ה-AI יחלץ אותם בשלב הבא).
    """
    pool = await get_pool()
    await pool.execute(
        f"""
        UPDATE jobs SET
            status = 'WAITING_FOR_AI',
            company = COALESCE($2, company),
            job_title = COALESCE($3, job_title),
            full_description = $4, scraped_at = NOW(), updated_at = NOW(),
            error_log = {_CLEAR_RETRY_NOTE_SQL}
        WHERE id = $1
        """,
        job_id,
        clean_field(company),
        clean_field(title),
        description,
    )


async def finish_analysis(job_id: int, result: dict):
    """
    שומר את תוצאות הניתוח הסופיות של ה-LLM ומסמן את התהליך כהושלם (COMPLETED).
    company / job_title שה-AI חילץ נכתבים לעמודות רק אם הערך הקיים הוא placeholder,
    כך שערך שהמשתמש הזין ידנית לא נדרס.
    """
    pool = await get_pool()
    if isinstance(result, dict):
        company = clean_field(result.get("company"))
        title = clean_field(result.get("job_title"))
        json_result = json.dumps(result)
    else:
        company = title = None
        json_result = result

    company_cond = _IS_PLACEHOLDER_SQL.format(col="company")
    title_cond = _IS_PLACEHOLDER_SQL.format(col="job_title")
    await pool.execute(
        f"""
        UPDATE jobs SET
            status = 'COMPLETED', analysis_result = $2, analyzed_at = NOW(),
            error_log = {_CLEAR_RETRY_NOTE_SQL},
            company = CASE WHEN $3::text IS NOT NULL AND {company_cond} THEN $3
                           WHEN {company_cond} THEN 'לא צוין' ELSE company END,
            job_title = CASE WHEN $4::text IS NOT NULL AND {title_cond} THEN $4
                             WHEN {title_cond} THEN 'לא צוין' ELSE job_title END
        WHERE id = $1
        """,
        job_id,
        json_result,
        company,
        title,
        list(PLACEHOLDER_VALUES),
    )


async def requeue_job(job_id: int, status: str, note: Optional[str] = None):
    """
    מחזיר משרה לתור בלי לספור ניסיון כושל (למשל 429: המכסה נגמרה - זו לא תקלה של המשרה).
    """
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE jobs SET status = $2, error_log = COALESCE($3, error_log),
            not_before = NULL, updated_at = NOW()
        WHERE id = $1
        """,
        job_id,
        status,
        note,
    )


async def requeue_in_progress() -> int:
    """כיבוי מסודר: משרות "בטיפול" חוזרות לתור בלי להיספר כניסיון. מחזיר כמה."""
    pool = await get_pool()
    total = 0
    for stuck, (retry_status, _failed) in _IN_PROGRESS.items():
        result = await pool.execute(
            "UPDATE jobs SET status = $2::job_status WHERE status = $1::job_status",
            stuck,
            retry_status,
        )
        total += int(result.split()[-1])
    return total


async def fail_or_retry(
    job_id: int,
    retry_status: str,
    failed_status: str,
    error_msg: str,
    max_attempts: int = 3,
    base_delay_seconds: int = 30,
):
    """
    תקלה זמנית (timeout / 5xx / רשת): retry_count++. כל עוד לא עברנו max_attempts המשרה
    חוזרת לתור עם backoff (30s, 60s, 120s...) דרך not_before; אחרת - failed_status.
    מחזיר (הסטטוס החדש, not_before) - not_before כדי לתזמן את ה-worker להתעורר בזמן.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        UPDATE jobs SET
            retry_count = retry_count + 1,
            status = (CASE WHEN retry_count + 1 < $5 THEN $2 ELSE $3 END)::job_status,
            not_before = CASE WHEN retry_count + 1 < $5
                              THEN NOW() + make_interval(secs => $6 * power(2, retry_count))
                              ELSE NULL END,
            error_log = CASE WHEN retry_count + 1 < $5
                             THEN $4 || ' (ניסיון ' || (retry_count + 1) || '/' || $5 || ', מנסה שוב)'
                             ELSE $4 END,
            updated_at = NOW()
        WHERE id = $1
        RETURNING status::text AS status, not_before
        """,
        job_id,
        retry_status,
        failed_status,
        error_msg,
        max_attempts,
        base_delay_seconds,
    )
    return (row["status"], row["not_before"]) if row else (None, None)


async def pending_retry_times() -> dict:
    """{סטטוס: מתי הניסיון החוזר הקרוב} - בהפעלה, כדי לתזמן את ה-workers להתעורר בזמן."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT status::text AS status, MIN(not_before) AS due FROM jobs "
        "WHERE not_before IS NOT NULL GROUP BY status"
    )
    return {r["status"]: r["due"] for r in rows}


async def increment_api_usage(day, model: str) -> int:
    """סופר בקשה ל-API של ה-AI ביום הנתון. מחזיר את המספר המעודכן."""
    pool = await get_pool()
    return await pool.fetchval(
        """
        INSERT INTO api_usage (day, model, requests) VALUES ($1, $2, 1)
        ON CONFLICT (day, model) DO UPDATE SET requests = api_usage.requests + 1
        RETURNING requests
        """,
        day,
        model,
    )


async def get_api_usage(day, model: str) -> int:
    pool = await get_pool()
    return await pool.fetchval(
        "SELECT COALESCE((SELECT requests FROM api_usage WHERE day = $1 AND model = $2), 0)",
        day,
        model,
    )


async def queue_snapshot() -> dict:
    """
    מצב התור בבקשה קטנה אחת: ספירה לפי סטטוס + "גרסה" (העדכון האחרון).
    הדשבורד בודק את זה בזמן עיבוד, ומושך את כל הרשימה רק כשהגרסה השתנתה.
    """
    pool = await get_pool()
    rows = await pool.fetch("SELECT status::text AS status, COUNT(*) AS n FROM jobs GROUP BY status")
    version = await pool.fetchval(
        "SELECT COALESCE(EXTRACT(EPOCH FROM MAX(updated_at)), 0)::text || ':' || COUNT(*) FROM jobs"
    )
    return {"counts": {r["status"]: r["n"] for r in rows}, "version": version}


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
    rows = await pool.fetch("SELECT * FROM jobs ORDER BY created_at DESC")
    return [_flatten(row) for row in rows]


def _flatten(row) -> dict:
    """שורת jobs -> dict, כשהשדות של analysis_result שטוחים (score, summary...) - כמו ב-get_all_jobs."""
    job = dict(row)
    analysis = job.get("analysis_result")
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except ValueError:
            analysis = None
    if isinstance(analysis, dict):
        job.update({k: v for k, v in analysis.items() if k not in _PROTECTED_FIELDS})
    return job


async def get_job_by_id(job_id: int) -> Optional[dict]:
    """משרה אחת עם תוצאת הניתוח (לבוט: מעקב אחרי משרה שנשלחה עד שיש ציון)."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
    return _flatten(row) if row else None


async def get_job_by_url(url: str) -> Optional[dict]:
    """שליפת מידע מלא על משרה בודדת לפי כתובת ה-URL שלה."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM jobs WHERE url = $1", url)
    return dict(row) if row else None


async def find_existing_job(url: str, exclude_id: Optional[int] = None) -> Optional[dict]:
    """
    משרה קיימת עם אותו קישור: הנוכחי (url) או המקורי שהמשתמש שלח (source_url).
    exclude_id: לא להחזיר את המשרה עצמה (בבדיקת כפילות אחרי פענוח).
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT * FROM jobs
        WHERE (url = $1 OR source_url = $1) AND ($2::int IS NULL OR id <> $2)
        ORDER BY id LIMIT 1
        """,
        url,
        exclude_id,
    )
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
        f"""
        UPDATE jobs
        SET user_action = $1, is_archived = $2, application_status = $3,
            applied_at = {_applied_at_sql("$3")}
        WHERE url = $4
        """,
        action,
        is_archived,
        app_status,
        url,
        list(_APPLIED_STAGES),
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
        f"""
        UPDATE jobs
        SET application_status = $1, user_action = $2, is_archived = $3,
            applied_at = {_applied_at_sql("$1")}
        WHERE url = $4
        """,
        status.value,
        user_action,
        is_archived,
        url,
        list(_APPLIED_STAGES),
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


async def retry_job(url: str) -> Optional[str]:
    """
    מחזיר משרה לתור, לשלב שבו היא נכשלה:
    - משרה ידנית, או כישלון AI כשיש כבר תיאור -> WAITING_FOR_AI
    - כישלון בפענוח הלינק -> PENDING_RESOLVE
    - כל השאר -> WAITING_FOR_SCRAPE
    (קודם הכל הלך לסריקה: משרה ידנית ניסתה לסרוק URL מזויף, וכישלון resolve דילג על הפענוח)
    """
    pool = await get_pool()
    return await pool.fetchval(
        """
        UPDATE jobs SET
            status = (CASE
                WHEN source = 'manual' THEN 'WAITING_FOR_AI'
                WHEN status = 'FAILED_ANALYSIS'
                     AND COALESCE(full_description, '') <> '' THEN 'WAITING_FOR_AI'
                WHEN status IN ('FAILED_RESOLVE', 'DUPLICATE') THEN 'PENDING_RESOLVE'
                ELSE 'WAITING_FOR_SCRAPE'
            END)::job_status,
            error_log = NULL, is_archived = FALSE,
            retry_count = 0, not_before = NULL  -- ניסיון ידני מתחיל ספירה מחדש
        WHERE url = $1
        RETURNING status::text
        """,
        url,
    )


# סטטוס "בטיפול" -> (חזרה לתור, כישלון סופי)
_IN_PROGRESS = {
    "RESOLVING": ("PENDING_RESOLVE", "FAILED_RESOLVE"),
    "SCRAPING": ("WAITING_FOR_SCRAPE", "FAILED_SCRAPE"),
    "ANALYZING": ("WAITING_FOR_AI", "FAILED_ANALYSIS"),
}


async def reset_stuck_jobs(max_attempts: int = 3) -> dict:
    """
    מנגנון בטיחות בהפעלה: משרות שנשארו "בטיפול" (השרת קרס / הופעל מחדש באמצע) חוזרות לתור.
    כל קריסה נספרת כניסיון: משרה שמפילה את השרת שוב ושוב (למשל Playwright שחורג
    מהזיכרון בשרת של 512MB) נכשלת אחרי max_attempts, במקום לולאה אינסופית של קריסות.
    מחזיר {סטטוס: כמה משרות טופלו}.
    """
    pool = await get_pool()
    counts = {}
    for stuck, (retry_status, failed_status) in _IN_PROGRESS.items():
        rows = await pool.fetch(
            """
            UPDATE jobs SET
                retry_count = retry_count + 1,
                status = (CASE WHEN retry_count + 1 < $4 THEN $2 ELSE $3 END)::job_status,
                error_log = CASE WHEN retry_count + 1 < $4 THEN error_log
                                 ELSE 'העיבוד נקטע ' || (retry_count + 1) || ' פעמים (השרת הופעל מחדש באמצע) - נעצר'
                            END,
                not_before = NULL
            WHERE status = $1
            RETURNING status::text
            """,
            stuck,
            retry_status,
            failed_status,
            max_attempts,
        )
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
    return counts


async def auto_archive_old_applications(days: int = 30) -> int:
    """
    הגשות שלא קיבלו מענה מעל `days` יום -> ghosted + ארכיון (כמו בעדכון ידני ל-ghosted).
    נספר מ-applied_at (מתי הוגשה המועמדות). קודם נספר מ-created_at, כך שמשרה שנוספה
    לפני חודש והוגשה אתמול סומנה מיד "ללא מענה".
    מחזיר את מספר המשרות שעודכנו.
    """
    pool = await get_pool()
    result = await pool.execute(
        """
        UPDATE jobs SET application_status = 'ghosted', is_archived = TRUE
        WHERE application_status = 'applied'
          AND applied_at < NOW() - make_interval(days => $1)
        """,
        days,
    )
    return int(result.split()[-1])


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
