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
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        self.headers = {"Content-Type": "application/json"}

    def analyze(
        self, resume: str, context: str, job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        שולח את נתוני המשרה ל-AI ומחזיר ניתוח התאמה מפורט.
        """
        # 1. שמירת ה"עוגן": ה-URL הוא המזהה הייחודי שלנו בבסיס הנתונים
        original_url = job_data.get("url")
        raw_company = job_data.get("company", "לא זוהה")
        raw_title = job_data.get("job_title", "לא זוהה")
        description = job_data.get("full_description", "אין תיאור משרה")

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

### הוראות פורמט:
החזר אך ורק אובייקט JSON תקין (ללא טקסט חופשי לפני או אחרי). 
המבנה חייב להיות:
{{
  "company": "{raw_company}",
  "job_title": "{raw_title}",
  "suitability_score": 0-100,
  "acceptance_probability": 0-100,
  "job_summary_hebrew": "סיכום תמציתי של המשרה",
  "showstoppers": ["חוסמים פוטנציאליים (למשל: דרישת שפות שאין למועמד)"],
  "gap_analysis": ["פערים מקצועיים שניתן לגשר עליהם"],
  "recommendation": "להגיש / לא להגיש",
  "formatted_message": "הודעה מותאמת אישית ליניב שתסכם למה כדאי/לא כדאי"
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


# --- בלוק בדיקה להרצה ישירה ---
if __name__ == "__main__":
    print("🧪 מריץ בדיקת מעבדה ל-JobAnalyzer...")

    # נתוני דוגמה
    test_resume = "יניב, מהנדס תוכנה עם 5 שנות ניסיון ב-Python ו-FastAPI."
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
