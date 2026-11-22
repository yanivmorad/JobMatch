# src/routes/jobs_routes.py
import logging
import uuid

from fastapi import APIRouter, Body, HTTPException

from db.jobs_repository import (
    ApplicationStatus,
    add_new_job,
    delete_job_by_url,
    find_existing_job,
    get_all_jobs,
    get_job_by_id,
    manual_update_job_content,
    queue_snapshot,
    update_application_status,
    update_manual_job,
)
from models.job_models import (
    ActionRequest,
    ApplicationStatusUpdateRequest,
    JobSubmission,
    ManualUpdate,
    RawTextSubmission,
    TextSubmission,
)
from services.intake import duplicate_info, ingest_text, ingest_urls
from services.link_extractor import extract_job_links, normalize_job_url
from workers.queue_signal import notify
from workers.worker_manager import ai_availability

logger = logging.getLogger("JobMatchServer")
router = APIRouter(tags=["jobs"])


@router.get("/results")
async def get_jobs():
    """שליפת כל המשרות מה-SQL"""
    return await get_all_jobs()


@router.get("/jobs/{job_id:int}")
async def get_job(job_id: int):
    """
    משרה אחת: סטטוס, ציון וניתוח. לערוצים כמו בוט: שולחים הודעה ל-/jobs/raw, מקבלים
    added_jobs עם id, ושואלים כאן עד ש-status הוא COMPLETED (או סטטוס כישלון).
    """
    job = await get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/queue")
async def get_queue_snapshot():
    """
    מצב התור בבקשה קטנה: ספירה לפי סטטוס + version. הדשבורד בודק את זה בזמן עיבוד
    ומושך את /results (כל המשרות, כולל תיאורים מלאים) רק כש-version השתנה.
    ai.paused_until: כל מודלי ה-AI בהפסקה (למשל המכסה היומית נוצלה) - עד מתי.
    """
    snapshot = await queue_snapshot()
    snapshot["ai"] = ai_availability()
    return snapshot


@router.post("/jobs/url")
async def add_url_jobs(submission: JobSubmission):
    """Intake: רשימת קישורים מוכנה. רק מכניס ל-DB, הוורקרים יעשו את השאר."""
    # בדיקת כפילות ללינק בודד - מחזירה 409 (הדשבורד מציג "נסרק בעבר")
    if len(submission.urls) == 1:
        url = normalize_job_url(submission.urls[0])
        existing = await find_existing_job(url)
        if existing:
            info = duplicate_info(url, existing)
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"קישור זה נסרק בעבר בתאריך {info['date']}",
                    "url": url,
                    "date": info["date"],
                },
            )

    return await ingest_urls(submission.urls, source="extension")


@router.post("/jobs/raw")
async def add_raw_text(submission: RawTextSubmission):
    """
    Intake מטקסט גולמי (הודעות וואטסאפ וכו'): השרת מחלץ את קישורי המשרות,
    מסנן קישורים שאינם משרות (מוחזרים ב-ignored עם סיבה) ומכניס את השאר לתור.
    """
    return await ingest_text(submission.text, source="web")


@router.post("/jobs/extract-links")
async def preview_links(submission: RawTextSubmission):
    """תצוגה מקדימה: אילו קישורים יוכנסו ואילו יסוננו - בלי לשמור כלום."""
    links = extract_job_links(submission.text)
    return {"jobs": links.jobs, "ignored": links.ignored, "titles": links.titles}


@router.post("/jobs/text")
async def add_text_job(submission: TextSubmission):
    """
    Intake ידני: מדלג ישר ל-AI.
    לכל משרה ידנית מזהה ייחודי: קודם ה-URL נבנה מהשם בלבד, ומשרות עם אותו שם
    (למשל כל המשרות בלי כותרת) נבלעו בשקט ב-ON CONFLICT DO NOTHING.
    """
    job_url = f"manual://{uuid.uuid4().hex}"
    manual_meta = {"title": submission.title, "company": submission.company}

    added = await add_new_job(
        url=job_url,
        source="manual",
        manual_text=submission.text,
        manual_meta=manual_meta,
    )
    if not added:
        raise HTTPException(status_code=500, detail="Failed to add manual job")
    notify("WAITING_FOR_AI")
    return {"message": "Manual job added to AI queue", "url": job_url}


@router.delete("/jobs")
async def delete_job(url: str):
    await delete_job_by_url(url)
    return {"message": "Job deleted"}


# בתוך src/routes/jobs_routes.py


@router.post("/jobs/action")
async def update_action(req: ActionRequest):
    """המשתמש סימן: הוגש / התעלם / ארכב / שחזר"""
    from db.jobs_repository import update_user_action  # וודא ייבוא

    logger.info(f"🔄 Updating action for: {req.url} to {req.action}")
    await update_user_action(req.url, req.action)

    return {"message": "Status updated successfully"}


@router.delete("/history")
async def clear_history():
    """מחיקת כל המשרות שבארכיון"""
    from db.jobs_repository import clear_archived_jobs

    await clear_archived_jobs()
    return {"message": "History cleared from SQL"}


@router.post("/jobs/manual-update")
async def manual_update(req: ManualUpdate):
    """עדכון ידני של משרה שכשלה בסריקה"""
    logger.info(f"✍️ Manual update for: {req.url}")
    await update_manual_job(req.url, req.company, req.title, req.description)
    notify("WAITING_FOR_AI")
    return {"message": "Job updated and re-queued for AI"}


@router.post("/jobs/retry")
async def retry_endpoint(url: str):
    """ניסיון סריקה מחדש"""
    from db.jobs_repository import retry_job

    status = await retry_job(url)
    if status:
        notify(status)
    return {"message": "Job queued for retry", "status": status}


@router.post("/jobs/application-status")
async def update_job_status(req: ApplicationStatusUpdateRequest):
    """עדכון סטטוס אפליקציה (pending, applied, וכו')"""
    logger.info(
        f"📋 Updating application status for: {req.url} to {req.status} (archived: {req.is_archived})"
    )
    try:
        status_enum = ApplicationStatus(req.status)
    except ValueError:
        # קודם הוחזר tuple, ש-FastAPI הפך לתשובת 200 עם רשימה
        raise HTTPException(status_code=400, detail="Invalid status value")
    await update_application_status(req.url, status_enum, req.is_archived)
    return {"message": "Application status updated"}


@router.post("/jobs/{job_id}/manual-content")
async def update_job_manually(job_id: int, content: str = Body(..., embed=True)):
    try:
        await manual_update_job_content(job_id, content)
        notify("WAITING_FOR_AI")
        return {"status": "success", "message": "Job moved to AI analysis"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
