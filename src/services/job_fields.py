# src/services/job_fields.py
"""עזרים משותפים לשדות company / job_title."""
from typing import Optional

# ערכים שמשמעותם "עוד לא ידוע". נבדקים ב-lowercase אחרי strip.
PLACEHOLDER_VALUES = (
    "",
    "unknown",
    "identifying...",
    "pending...",
    "לא צוין",
    "לא זוהה",
    "משרה ידנית",
    "n/a",
    "none",
    "null",
)


def is_placeholder(value: Optional[str]) -> bool:
    """True אם הערך ריק, placeholder, או URL (add_new_job שם את ה-URL כ-company זמני)."""
    if value is None:
        return True
    v = str(value).strip().lower()
    return v in PLACEHOLDER_VALUES or v.startswith(("http://", "https://", "manual"))


def clean_field(value: Optional[str]) -> Optional[str]:
    """מחזיר את הערך אחרי strip, או None אם הוא placeholder."""
    return None if is_placeholder(value) else str(value).strip()
