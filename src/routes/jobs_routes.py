# src/routes/jobs_routes.py
import logging

from fastapi import APIRouter

# IMPORT REPOSITORY INSTEAD OF JSON_DB
from db.jobs_repository import (
    add_new_job,
    delete_job_by_url,
    get_all_jobs,
    update_manual_job,
)
from models.job_models import (
    ActionRequest,
    JobSubmission,
    ManualUpdate,
    TextSubmission,
)

logger = logging.getLogger("JobMatchServer")
router = APIRouter(tags=["jobs"])


@router.get("/results")
async def get_jobs():
    """שליפת כל המשרות מה-SQL"""
    return await get_all_jobs()


@router.post("/jobs/url")
async def add_url_jobs(submission: JobSubmission):
    """Intake: רק מכניס ל-DB, הוורקרים יעשו את השאר"""
    added = 0
    skipped = 0
    for url in submission.urls:
        clean_url = url.strip()
        if clean_url:
            was_added = await add_new_job(clean_url, source="extension")
            if was_added:
                added += 1
            else:
                skipped += 1

    return {
        "message": f"Processed {added + skipped} jobs",
        "added": added,
        "skipped": skipped,
    }


@router.post("/jobs/text")
async def add_text_job(submission: TextSubmission):
    """Intake ידני: מדלג ישר ל-AI"""
    fake_url = f"manual-{submission.company}-{submission.title}".replace(" ", "-")
    manual_meta = {"title": submission.title, "company": submission.company}

    await add_new_job(
        url=fake_url,
        source="manual",
        manual_text=submission.text,
        manual_meta=manual_meta,
    )
    return {"message": "Manual job added to AI queue"}


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
    return {"message": "Job updated and re-queued for AI"}
