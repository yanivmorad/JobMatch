# src/models/job_models.py
from typing import List, Optional

from pydantic import BaseModel


class JobEntry(BaseModel):
    url: str
    status: str = "pending"  # pending, scraping, scraped, analyzing, completed, failed
    created_at: str
    scraped_at: Optional[str] = None
    analyzed_at: Optional[str] = None

    # נתונים גולמיים
    company: str = "Pending..."
    job_title: str = "Pending..."
    full_description: Optional[str] = None

    # תוצאות AI
    suitability_score: int = 0
    acceptance_probability: int = 0
    job_summary_hebrew: Optional[str] = None
    showstoppers: Optional[List[str]] = []
    gap_analysis: Optional[List[str]] = []
    recommendation: Optional[str] = None
    formatted_message: Optional[str] = None

    # ניהול
    error_log: Optional[str] = None
    user_action: str = "none"  # none, applied, ignored
    is_archived: bool = False


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
