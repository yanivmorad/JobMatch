"""
אימות בסיסי ל-API: טוקן משותף ב-header.

    API_TOKEN=<סוד ארוך>   -> כל /api/* דורש  Authorization: Bearer <token>  (או X-API-Key: <token>)
    API_TOKEN לא מוגדר     -> פתוח (פיתוח מקומי בלבד; בהפעלה נרשמת אזהרה)

/health נשאר פתוח (ל-health check של הפלטפורמה ול-ping חיצוני). הדשבורד מבקש את
הטוקן פעם אחת ושומר אותו בדפדפן - הוא *לא* נבנה לתוך ה-JS (אחרת כל מי שפותח את
הדף היה רואה אותו).
"""
import logging
import os
import secrets
from typing import Optional

from fastapi import Header, HTTPException

logger = logging.getLogger("JobMatchServer")


def configured_token() -> Optional[str]:
    return (os.getenv("API_TOKEN") or "").strip() or None


async def require_api_token(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> None:
    expected = configured_token()
    if expected is None:
        return
    provided = x_api_key
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    if not provided or not secrets.compare_digest(provided.encode(), expected.encode()):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
