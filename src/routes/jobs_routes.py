# src/routes/jobs_routes.py
import logging

from fastapi import APIRouter, Body, HTTPException

from db.jobs_repository import (
    ApplicationStatus,
    add_new_job,
    delete_job_by_url,
    get_all_jobs,
    get_job_by_url,
    manual_update_job_content,
    update_application_status,
    update_manual_job,
)

# IMPORT REPOSITORY INSTEAD OF JSON_DB
from models.job_models import (
    ActionRequest,
    ApplicationStatusUpdateRequest,
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
    skipped_urls = []  # רשימת לינקים שדולגו

    # בדיקת כפילות ללינקים בודדים - דרישת משתמש
    if len(submission.urls) == 1:
        url = submission.urls[0].strip()
        existing = await get_job_by_url(url)
        if existing:
            original_date = existing.get("analyzed_at") or existing.get("created_at")
            date_str = (
                original_date.strftime("%d/%m/%Y") if original_date else "לא ידוע"
            )
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"קישור זה נסרק בעבר בתאריך {date_str}",
                    "url": url,
                    "date": date_str,
                },
            )

    for url in submission.urls:
        clean_url = url.strip()
        if clean_url:
            was_added = await add_new_job(clean_url, source="extension")
            if was_added:
                added += 1
            else:
                skipped += 1
                # נבדוק מתי הלינק נסרק
                existing = await get_job_by_url(clean_url)
                if existing:
                    original_date = existing.get("analyzed_at") or existing.get(
                        "created_at"
                    )
                    date_str = (
                        original_date.strftime("%d/%m/%Y")
                        if original_date
                        else "לא ידוע"
                    )
                    skipped_urls.append(
                        {
                            "url": clean_url,
                            "date": date_str,
                            "company": existing.get("company", "Unknown"),
                        }
                    )

    return {
        "message": f"Processed {added + skipped} jobs",
        "added": added,
        "skipped": skipped,
        "skipped_urls": skipped_urls,  # מידע על לינקים שדולגו
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


@router.post("/jobs/retry")
async def retry_endpoint(url: str):
    """ניסיון סריקה מחדש"""
    from db.jobs_repository import retry_job

    await retry_job(url)
    return {"message": "Job queued for retry"}


@router.post("/jobs/application-status")
async def update_job_status(req: ApplicationStatusUpdateRequest):
    """עדכון סטטוס אפליקציה (pending, applied, וכו')"""
    logger.info(
        f"📋 Updating application status for: {req.url} to {req.status} (archived: {req.is_archived})"
    )
    try:
        status_enum = ApplicationStatus(req.status)
        await update_application_status(req.url, status_enum, req.is_archived)
        return {"message": "Application status updated"}
    except ValueError:
        return {"error": "Invalid status value"}, 400


@router.post("/jobs/{job_id}/manual-content")
async def update_job_manually(job_id: int, content: str = Body(..., embed=True)):
    try:
        await manual_update_job_content(job_id, content)
        return {"status": "success", "message": "Job moved to AI analysis"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
