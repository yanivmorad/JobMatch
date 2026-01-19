# src/routes/jobs_routes.py
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from db.json_db import (
    clear_history_db,
    delete_job_by_url,
    get_job_by_url,
    load_db,
    update_job_in_db,
)
from models.job_models import ActionRequest, JobSubmission, TextSubmission
from services.job_service import process_job

logger = logging.getLogger("JobMatchServer")

router = APIRouter(tags=["jobs"])


@router.get("/results")
async def get_jobs():
    """החזרת כל המשרות לטבלה ב-Frontend"""
    jobs = await load_db()
    jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jobs


@router.post("/jobs/url")
async def add_url_jobs(submission: JobSubmission, background_tasks: BackgroundTasks):
    """הוספת רשימת URLים לעיבוד ברקע"""
    count = 0
    skipped = 0
    for url in submission.urls:
        clean_url = url.strip()
        if clean_url:
            existing = await get_job_by_url(clean_url)
            if existing:
                status = existing.get("status", "unknown")
                logger.info(
                    f"⏭️ דילוג על משרה קיימת: {clean_url[:50]}... (סטטוס: {status})"
                )
                skipped += 1
                continue

            background_tasks.add_task(process_job, clean_url)
            count += 1

    message = f"Started processing {count} new jobs"
    if skipped > 0:
        message += f" (skipped {skipped} existing)"

    return {"message": message, "added": count, "skipped": skipped}


@router.post("/jobs/text")
async def add_text_job(submission: TextSubmission, background_tasks: BackgroundTasks):
    """הוספת משרה ע"י הדבקת טקסט ידני"""
    fake_url = f"manual-{datetime.now().timestamp()}"
    manual_meta = {"title": submission.title, "company": submission.company}
    background_tasks.add_task(process_job, fake_url, submission.text, manual_meta)
    return {"message": "Manual job analysis started"}


@router.post("/jobs/action")
async def update_action(req: ActionRequest):
    """המשתמש סימן: הוגש / התעלם / ארכב / שחזר"""
    logger.info(f" cercando job per URL: {req.url}")
    job = await get_job_by_url(req.url)

    if not job:
        logger.error(f"❌ Job not found for URL: {req.url}")
        raise HTTPException(status_code=404, detail="Job not found")

    old_action = job.get("user_action", "none")
    old_archived = job.get("is_archived", False)

    job["user_action"] = req.action
    job["is_archived"] = req.action != "none"

    logger.info(
        f"🔄 Action Update: '{old_action}' -> '{req.action}' | Archived: {old_archived} -> {job['is_archived']}"
    )

    await update_job_in_db(job)
    return {
        "message": "Status updated",
        "new_status": job["user_action"],
        "is_archived": job["is_archived"],
    }


@router.post("/jobs/retry")
async def retry_job(req: ActionRequest, background_tasks: BackgroundTasks):
    """ניסיון חוזר למשרה שנכשלה"""
    job = await get_job_by_url(req.url)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    background_tasks.add_task(process_job, req.url)
    return {"message": "Retrying job..."}


@router.delete("/jobs")
async def delete_job(url: str):
    """מחיקת משרה בודדת (דרך Query Param)"""
    deleted = await delete_job_by_url(url)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job deleted"}


@router.delete("/history")
async def clear_history():
    """מחיקת כל המשרות שבארכיון (ignored)"""
    await clear_history_db()
    return {"message": "History cleared"}
