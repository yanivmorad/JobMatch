import logging

from fastapi import APIRouter, HTTPException

from models.profile_models import ProfileContent
from services.profile_service import (
    get_context_content,
    get_resume_content,
    update_context_content,
    update_resume_content,
)

logger = logging.getLogger("JobMatchServer")

router = APIRouter(tags=["profile"])


@router.get("/resume")
async def get_resume():
    """קריאת קורות החיים (מה-DB)"""
    return {"content": await get_resume_content()}


@router.post("/resume")
async def update_resume(data: ProfileContent):
    """עדכון קורות החיים (נשמר ב-DB - שורד דיפלוי)"""
    try:
        await update_resume_content(data.content)
        return {"message": "Resume updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context")
async def get_context():
    """קריאת ההקשר האישי (מה-DB)"""
    return {"content": await get_context_content()}


@router.post("/context")
async def update_context(data: ProfileContent):
    """עדכון ההקשר האישי (נשמר ב-DB - שורד דיפלוי)"""
    try:
        await update_context_content(data.content)
        return {"message": "Context updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
