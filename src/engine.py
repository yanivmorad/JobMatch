import json
import logging
import os
import time
from typing import Any, Dict

import requests
from dotenv import load_dotenv

try:
    from services.job_fields import clean_field
except ImportError:
    from src.services.job_fields import clean_field

# טעינת משתני סביבה (API Key)
load_dotenv()

logger = logging.getLogger("Engine")

DEFAULT_MODEL = "gemini-2.5-flash-lite"


def build_prompt(resume: str, context: str, job_data: Dict[str, Any]) -> str:
    """בונה את הפרומפט. פרטים אישיים (כמו שם המועמד) מגיעים רק מקורות החיים / קובץ ההקשר."""
    description = job_data.get("full_description") or "אין תיאור משרה"

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


class JobAnalyzer:
    def __init__(self):
        """
        אתחול המנתח - הגדרת מודל ה-AI ופרטי הגישה.
        """
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("❌ GEMINI_API_KEY missing in .env file")

        self.model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        # המפתח נשלח ב-header ולא ב-URL: הודעות שגיאה של requests כוללות את ה-URL,
        # ומפתח ב-query string היה דולף ללוגים.
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        self.headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def analyze(
        self, resume: str, context: str, job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        שולח את נתוני המשרה ל-AI ומחזיר ניתוח התאמה מפורט.
        השדות company / job_title בתוצאה הם מה ש-Gemini חילץ מהתיאור.
        """
        original_url = job_data.get("url")
        prompt = build_prompt(resume, context, job_data)

        # טמפרטורה נמוכה (עקביות) ופורמט JSON
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }

        for attempt in range(3):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()

                data = response.json()
                text_output = data["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(text_output)

                result["url"] = original_url
                return result

            except Exception as e:
                logger.warning(f"⚠️ Gemini attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(2)

        raise RuntimeError("Analysis failed after 3 attempts")


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
