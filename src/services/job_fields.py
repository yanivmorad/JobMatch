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
    # הדף הציבורי של HireMeTech מסתיר את החברה: "<תפקיד> at Company | HireMe"
    "company",
    "company | hireme",
    "hireme",
    # באג (E2E): ה-AI כתב את שם הפלטפורמה כשם החברה
    "hiremetech",
    "hiremetech.com",
    "hire me tech",
)
# ה-AI העתיק את ההערה "(שם החברה מוסתר בדף הציבורי של HireMeTech)" כשם החברה
_MASKED_MARKERS = ("מוסתר", "hidden by hiremetech")


def is_placeholder(value: Optional[str]) -> bool:
    """True אם הערך ריק, placeholder, או URL (add_new_job שם את ה-URL כ-company זמני)."""
    if value is None:
        return True
    v = str(value).strip().lower()
    return (
        v in PLACEHOLDER_VALUES
        or v.startswith(("http://", "https://", "manual"))
        or any(m in v for m in _MASKED_MARKERS)
    )


def clean_field(value: Optional[str]) -> Optional[str]:
    """מחזיר את הערך אחרי strip, או None אם הוא placeholder."""
    return None if is_placeholder(value) else str(value).strip()
