# src/models/job_models.py
from typing import List, Optional

from pydantic import BaseModel


class JobSubmission(BaseModel):
    urls: List[str]


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
