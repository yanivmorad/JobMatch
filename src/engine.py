import json
import os
import time
from typing import Any, Dict

import requests
from dotenv import load_dotenv

# טעינת משתני סביבה (API Key)
load_dotenv()


class JobAnalyzer:
    def __init__(self):
        """
        אתחול המנתח - הגדרת מודל ה-AI ופרטי הגישה.
        """
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("❌ GEMINI_API_KEY missing in .env file")

        # שימוש במודל Flash-Lite: איזון מושלם בין מהירות לעלות ב-2026
        self.model_name = "gemini-2.5-flash-lite"
        # המפתח נשלח ב-header ולא ב-URL, כדי שלא יודפס ללוג בהודעות שגיאה
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
        """
        # 1. שמירת ה"עוגן": ה-URL הוא המזהה הייחודי שלנו בבסיס הנתונים
        original_url = job_data.get("url")
        raw_company = self._known_or_empty(job_data.get("company"), original_url)
        raw_title = self._known_or_empty(job_data.get("job_title"), original_url)
        description = job_data.get("full_description") or "אין תיאור משרה"

        known_meta = ""
        if raw_company or raw_title:
            known_meta = f"""
4. פרטים ידועים (השתמש בהם אם הם תואמים לתיאור):
   חברה: {raw_company or "לא ידוע"}
   תפקיד: {raw_title or "לא ידוע"}
"""

        # 2. בניית הפרומפט - הגדרת הציפיות מה-AI
        prompt = f"""
נתח התאמה למשרה על בסיס עובדות בלבד. 

### נתונים:
1. קורות חיים של המועמד:
{resume}

2. הקשר/העדפות נוספות:
{context}

3. תיאור המשרה המלא:
{description}
{known_meta}
### הוראות פורמט:
החזר אך ורק אובייקט JSON תקין (ללא טקסט חופשי לפני או אחרי). 
את שם החברה ושם התפקיד חלץ מתוך תיאור המשרה. אם לא ניתן לזהות - החזר מחרוזת ריקה.
המבנה חייב להיות:
{{
  "company": "שם החברה המגייסת",
  "job_title": "שם התפקיד",
  "suitability_score": 0-100,
  "acceptance_probability": 0-100,
  "job_summary_hebrew": "סיכום תמציתי של המשרה",
  "showstoppers": ["חוסמים פוטנציאליים (למשל: דרישת שפות שאין למועמד)"],
  "gap_analysis": ["פערים מקצועיים שניתן לגשר עליהם"],
  "recommendation": "להגיש / לא להגיש",
  "formatted_message": "הודעה אישית למועמד שמסכמת למה כדאי/לא כדאי להגיש"
}}
"""

        # הגדרות ה-Payload עם דגש על טמפרטורה נמוכה (עקביות) ופורמט JSON
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,  # אנחנו רוצים תשובות עובדתיות, לא יצירתיות
            },
        }

        # 3. מנגנון הרצה עם ניסיונות חוזרים (Retry)
        for attempt in range(3):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()  # יזרוק שגיאה אם ה-Status Code הוא לא 200

                data = response.json()

                # חילוץ הטקסט מהמבנה של Google Gemini
                text_output = data["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(text_output)
                # לפעמים המודל עוטף את האובייקט ברשימה
                if isinstance(result, list) and result and isinstance(result[0], dict):
                    result = result[0]
                if not isinstance(result, dict):
                    raise ValueError("AI response is not a JSON object")

                # 4. הזרקה מחדש של ה-URL המקורי
                # זה קריטי כי ה-Worker צריך את ה-URL כדי לדעת איזה שורה לעדכן ב-DB
                result["url"] = original_url
                return result

            except Exception as e:
                print(f"⚠️ ניסיון {attempt + 1} נכשל: {e}")
                if attempt < 2:
                    time.sleep(2)  # המתנה קלה לפני ניסיון נוסף

        # אם הגענו לכאן, הניתוח נכשל סופית
        raise RuntimeError("Analysis failed after 3 attempts")

    @staticmethod
    def _known_or_empty(value, url) -> str:
        """מחזיר את הערך רק אם הוא שם אמיתי (לא URL, לא placeholder)."""
        if not isinstance(value, str):
            return ""
        value = value.strip()
        placeholders = {"unknown", "לא זוהה", "לא צוין", "identifying...", "pending..."}
        if not value or value == url or value.lower() in placeholders:
            return ""
        if value.startswith(("http://", "https://")):
            return ""
        return value


# --- בלוק בדיקה להרצה ישירה ---
if __name__ == "__main__":
    print("🧪 מריץ בדיקת מעבדה ל-JobAnalyzer...")

    # נתוני דוגמה
    test_resume = "מהנדס תוכנה עם 5 שנות ניסיון ב-Python ו-FastAPI."
    test_context = "מחפש משרות מרחוק (Remote) בלבד."

    test_job = {
        "url": "https://example.com/job/123",
        "company": "TechGlobal",
        "job_title": "Backend Developer",
        "full_description": "מחפשים מפתח פייתון מנוסה לעבודה מהבית.",
    }

    analyzer = JobAnalyzer()

    try:
        final_result = analyzer.analyze(test_resume, test_context, test_job)
        print("\n✅ ניתוח בוצע בהצלחה:")
        print(json.dumps(final_result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ בדיקה נכשלה: {e}")
