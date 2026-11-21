import json
import logging
import os
import re
from typing import Any, Dict, List, Literal, Optional

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator

try:
    from services.description import DEFAULT_MAX_CHARS, condense_description
    from services.job_fields import clean_field
except ImportError:
    from src.services.description import DEFAULT_MAX_CHARS, condense_description
    from src.services.job_fields import clean_field

# טעינת משתני סביבה (API Key)
load_dotenv()

logger = logging.getLogger("Engine")

DEFAULT_MODEL = "gemini-2.5-flash-lite"
REQUEST_TIMEOUT = 60
# ניסיונות נוספים כשהתשובה לא עומדת בסכמה (JSON שבור / שדה חסר / ציון מחוץ לטווח)
VALIDATION_ATTEMPTS = 2

RECOMMENDATIONS = ("להגיש", "לא להגיש")


# --- שגיאות: ה-worker מחליט לפיהן מה לעשות עם המשרה ---


class AIError(RuntimeError):
    """שגיאה קבועה (מפתח לא תקין, בקשה שנחסמה...) - המשרה נכשלת אחרי מספר ניסיונות."""


class TransientAIError(AIError):
    """תקלה זמנית (5xx, רשת, timeout) - המשרה חוזרת לתור (עד MAX_JOB_ATTEMPTS)."""


class InvalidAIResponse(AIError):
    """התשובה לא עמדה בסכמה גם אחרי VALIDATION_ATTEMPTS ניסיונות."""


class RateLimitError(AIError):
    """
    429 / RESOURCE_EXHAUSTED: המכסה נגמרה. המשרה *לא* נכשלת - היא חוזרת לתור,
    וה-worker ממתין retry_after שניות (או עד איפוס המכסה היומית אם per_day).
    """

    def __init__(self, message: str, retry_after: Optional[float] = None, quota_ids=(), quota_values=()):
        super().__init__(message)
        self.retry_after = retry_after
        self.quota_ids = list(quota_ids)
        self.quota_values = list(quota_values)

    @property
    def per_day(self) -> bool:
        return any("perday" in q.lower() for q in self.quota_ids)


# --- סכמת התשובה ---


class AnalysisResult(BaseModel):
    company: str = Field(min_length=1)
    job_title: str = Field(min_length=1)
    suitability_score: int = Field(ge=0, le=100)
    acceptance_probability: int = Field(ge=0, le=100)
    job_summary_hebrew: str = Field(min_length=1)
    showstoppers: List[str]
    gap_analysis: List[str]
    recommendation: Literal["להגיש", "לא להגיש"]
    formatted_message: str = Field(min_length=1)

    @field_validator("recommendation", mode="before")
    @classmethod
    def _normalize_recommendation(cls, v):
        v = (v or "").strip()
        # "לא כדאי להגיש" / "לא להגיש." -> "לא להגיש"
        if v.startswith("לא"):
            return "לא להגיש"
        if "להגיש" in v:
            return "להגיש"
        return v


# responseSchema של Gemini (structured output): מחייב את המודל למבנה הזה
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "company": {"type": "STRING"},
        "job_title": {"type": "STRING"},
        "suitability_score": {"type": "INTEGER"},
        "acceptance_probability": {"type": "INTEGER"},
        "job_summary_hebrew": {"type": "STRING"},
        "showstoppers": {"type": "ARRAY", "items": {"type": "STRING"}},
        "gap_analysis": {"type": "ARRAY", "items": {"type": "STRING"}},
        "recommendation": {"type": "STRING", "enum": list(RECOMMENDATIONS)},
        "formatted_message": {"type": "STRING"},
    },
    "required": list(AnalysisResult.model_fields),
    "propertyOrdering": list(AnalysisResult.model_fields),
}


def _max_description_chars() -> int:
    try:
        return int(os.getenv("MAX_DESCRIPTION_CHARS") or DEFAULT_MAX_CHARS)
    except ValueError:
        return DEFAULT_MAX_CHARS


def build_prompt(resume: str, context: str, job_data: Dict[str, Any]) -> str:
    """בונה את הפרומפט. פרטים אישיים (כמו שם המועמד) מגיעים רק מקורות החיים / קובץ ההקשר."""
    description = condense_description(job_data.get("full_description") or "", _max_description_chars())
    description = description or "אין תיאור משרה"

    # פרטים שהמשתמש הזין ידנית - נותנים ל-AI כרמז, לא כתבנית להעתקה
    known = []
    company = clean_field(job_data.get("company"))
    title = clean_field(job_data.get("job_title"))
    if company:
        known.append(f"חברה: {company}")
    if title:
        known.append(f"תפקיד: {title}")
    known_block = (
        "\n4. פרטים ידועים על המשרה (הוזנו ידנית):\n" + "\n".join(known) + "\n"
        if known
        else ""
    )

    return f"""
נתח התאמה למשרה על בסיס עובדות בלבד.

### נתונים:
1. קורות חיים של המועמד:
{resume}

2. הקשר/העדפות נוספות:
{context}

3. תיאור המשרה המלא:
{description}
{known_block}
### הוראות פורמט:
החזר אך ורק אובייקט JSON תקין (ללא טקסט חופשי לפני או אחרי).
המבנה חייב להיות:
{{
  "company": "שם החברה המעסיקה, כפי שמופיע בתיאור המשרה",
  "job_title": "שם התפקיד, כפי שמופיע בתיאור המשרה",
  "suitability_score": 0-100,
  "acceptance_probability": 0-100,
  "job_summary_hebrew": "סיכום תמציתי של המשרה",
  "showstoppers": ["חוסמים פוטנציאליים (למשל: דרישת שפות שאין למועמד)"],
  "gap_analysis": ["פערים מקצועיים שניתן לגשר עליהם"],
  "recommendation": "להגיש / לא להגיש",
  "formatted_message": "הודעה אישית קצרה למועמד שמסכמת למה כדאי/לא כדאי להגיש. אם שם המועמד מופיע בקורות החיים או בהקשר - פנה אליו בשמו"
}}
אם שם החברה או שם התפקיד לא מופיעים בתיאור המשרה ולא בפרטים הידועים - החזר עבורם "לא צוין". אל תמציא.
"""


# --- פענוח שגיאת 429 של Google (google.rpc.Status) ---

_DURATION = re.compile(r"^\s*([\d.]+)s\s*$")


def _parse_rate_limit(response) -> RateLimitError:
    retry_after = None
    header = (getattr(response, "headers", None) or {}).get("Retry-After")
    if header:
        try:
            retry_after = float(header)
        except ValueError:
            pass
    quota_ids, quota_values, message = [], [], "429 RESOURCE_EXHAUSTED"
    try:
        error = (response.json() or {}).get("error") or {}
        message = f"429 {error.get('status', 'RESOURCE_EXHAUSTED')}"
        for detail in error.get("details") or []:
            kind = detail.get("@type", "")
            if kind.endswith("RetryInfo") and retry_after is None:
                m = _DURATION.match(str(detail.get("retryDelay", "")))
                if m:
                    retry_after = float(m.group(1))
            elif kind.endswith("QuotaFailure"):
                for v in detail.get("violations") or []:
                    quota_ids.append(v.get("quotaId") or v.get("quotaMetric") or "")
                    quota_values.append(str(v.get("quotaValue") or ""))
    except Exception:
        pass
    return RateLimitError(message, retry_after, quota_ids, quota_values)


def configured_models() -> List[str]:
    """
    GEMINI_MODELS="a,b,c" (שרשרת: עוברים לבא כשהמכסה היומית של הקודם נגמרת),
    אחרת GEMINI_MODEL, אחרת DEFAULT_MODEL.
    """
    chain = [m.strip() for m in (os.getenv("GEMINI_MODELS") or "").split(",") if m.strip()]
    if chain:
        return list(dict.fromkeys(chain))
    # "or" ולא ברירת מחדל של getenv: שורה ריקה ב-.env (GEMINI_MODEL=) מגיעה כ-""
    return [(os.getenv("GEMINI_MODEL") or "").strip() or DEFAULT_MODEL]


class JobAnalyzer:
    def __init__(self, model_name: Optional[str] = None):
        """
        אתחול המנתח - הגדרת מודל ה-AI ופרטי הגישה.
        model_name: ברירת מחדל - המודל הראשון ב-configured_models().
        """
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("❌ GEMINI_API_KEY missing in .env file")

        self.model_name = model_name or configured_models()[0]
        # המפתח נשלח ב-header ולא ב-URL: הודעות שגיאה של requests כוללות את ה-URL,
        # ומפתח ב-query string היה דולף ללוגים.
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        self.headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def _call(self, payload: dict) -> str:
        """בקשה אחת ל-Gemini. מחזיר את הטקסט, או זורק שגיאה מסווגת (בלי URL / מפתח בהודעה)."""
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            raise TransientAIError(f"Gemini network error: {type(e).__name__}") from None

        status = response.status_code
        if status == 429:
            err = _parse_rate_limit(response)
            logger.warning(
                f"⚠️ Gemini 429 (quota: {err.quota_ids or '?'} = {err.quota_values or '?'}, retry after {err.retry_after}s)"
            )
            raise err
        if status >= 500:
            logger.warning(f"⚠️ Gemini HTTP {status}")
            raise TransientAIError(f"Gemini HTTP {status}")
        if status >= 400:
            try:
                detail = ((response.json() or {}).get("error") or {}).get("message", "")
            except Exception:
                detail = ""
            logger.error(f"❌ Gemini HTTP {status}: {detail[:200]}")
            raise AIError(f"Gemini HTTP {status}: {detail[:200]}")

        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            block = (data.get("promptFeedback") or {}).get("blockReason")
            raise AIError(f"Gemini returned no answer (blockReason={block})")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        if not text:
            raise InvalidAIResponse(f"empty answer (finishReason={candidates[0].get('finishReason')})")
        return text

    def analyze(
        self, resume: str, context: str, job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        שולח את נתוני המשרה ל-AI ומחזיר ניתוח התאמה מאומת (AnalysisResult + url).
        השדות company / job_title בתוצאה הם מה ש-Gemini חילץ מהתיאור.
        """
        payload = {
            "contents": [{"parts": [{"text": build_prompt(resume, context, job_data)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
                "temperature": 0.1,
            },
        }

        last_error = None
        for attempt in range(1, VALIDATION_ATTEMPTS + 1):
            text = self._call(payload)  # 429 / 5xx / 4xx עולים ישר ל-worker
            try:
                result = AnalysisResult.model_validate(json.loads(text)).model_dump()
                result["url"] = job_data.get("url")
                result["model"] = self.model_name  # ציונים של מודלים שונים לא בהכרח ברי-השוואה
                return result
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                logger.warning(f"⚠️ Gemini answer failed validation (attempt {attempt}): {str(e)[:300]}")

        raise InvalidAIResponse(f"Gemini answer did not match the schema: {str(last_error)[:300]}")


# --- בלוק בדיקה להרצה ישירה ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("🧪 מריץ בדיקת מעבדה ל-JobAnalyzer...")

    test_resume = "מהנדס תוכנה עם 5 שנות ניסיון ב-Python ו-FastAPI."
    test_context = "מחפש משרות מרחוק (Remote) בלבד."
    test_job = {
        "url": "https://example.com/job/123",
        "full_description": "TechGlobal מחפשת Backend Developer - מפתח פייתון מנוסה לעבודה מהבית.",
    }

    try:
        final_result = JobAnalyzer().analyze(test_resume, test_context, test_job)
        print("\n✅ ניתוח בוצע בהצלחה:")
        print(json.dumps(final_result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ בדיקה נכשלה: {e}")
