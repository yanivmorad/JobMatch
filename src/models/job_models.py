# src/models/job_models.py
from typing import Dict, List, Optional

from pydantic import BaseModel


class JobSubmission(BaseModel):
    urls: List[str]
    # אופציונלי: url -> כותרת המשרה כפי שזוהתה בטקסט שהודבק (למשל בהודעת וואטסאפ)
    titles: Optional[Dict[str, str]] = None


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
