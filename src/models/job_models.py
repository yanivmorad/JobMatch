# src/models/job_models.py
from typing import List, Optional

from pydantic import BaseModel, Field


class JobSubmission(BaseModel):
    urls: List[str]


class RawTextSubmission(BaseModel):
    """טקסט גולמי (הודעות וואטסאפ / פוסטים) - השרת מחלץ ממנו את קישורי המשרות."""

    text: str = Field(..., max_length=200_000)


class TextSubmission(BaseModel):
    text: str
    title: Optional[str] = "משרה ידנית"
    company: Optional[str] = "לא צוין"


class ActionRequest(BaseModel):
    url: str
    action: str  # 'applied', 'ignored', 'archive', 'none'


class ManualUpdate(BaseModel):
    url: str
    company: str
    title: str
    description: str


class ApplicationStatusUpdateRequest(BaseModel):
    url: str
    status: str
    is_archived: Optional[bool] = None
