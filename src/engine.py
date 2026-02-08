# jobMatch/src/engine.py
import json
import os
import time
from typing import Any, Dict

import requests
from dotenv import load_dotenv

load_dotenv()


class JobAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("❌ GEMINI_API_KEY missing in .env file")

        # המודל שבחרת - יציב ומהיר ל-2026
        self.model_name = "gemini-2.5-flash-lite"
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        self.headers = {"Content-Type": "application/json"}

    def analyze(
        self, resume: str, context: str, job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        מנתח את המשרה ומוודא שהמזהה המקורי (URL או None) חוזר בסוף התהליך
        כדי למנוע איבוד נתונים בעדכון ה-DB.
        """

        # 1. שמירת ה-URL המקורי (או None) - זה העוגן שלנו
        original_url = job_data.get("url")
        raw_company = job_data.get("company", "לא זוהה")
        raw_title = job_data.get("job_title", "לא זוהה")
        description = job_data.get("full_description", "אין תיאור משרה")

        prompt = f"""
נתח התאמה למשרה על בסיס עובדות בלבד. 

### נתונים:
1. קורות חיים:
{resume}

2. הקשר נוסף:
{context}

3. תיאור המשרה:
{description}

### החזר JSON במבנה הבא:
{{
  "company": "{raw_company}",
  "job_title": "{raw_title}",
  "suitability_score": 0-100,
  "acceptance_probability": 0-100,
  "job_summary_hebrew": "סיכום המשרה בעברית",
  "showstoppers": ["רשימת חוסמים"],
  "gap_analysis": ["רשימת פערים"],
  "recommendation": "להגיש / לא להגיש",
  "formatted_message": "פנייה ישירה ליניב"
}}
"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }

        # לוגיקת ה-Retry
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

                # 2. הזרקה מחדש של ה-URL המקורי לתוצאה (גם אם הוא None)
                result["url"] = original_url
                return result

            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(2)

        # 3. במקרה של כישלון סופי - מחזירים אובייקט בטוח שכולל את ה-URL המקורי
        return {
            "url": original_url,
            "company": raw_company,
            "job_title": raw_title,
            "suitability_score": 0,
            "formatted_message": "שגיאה בניתוח המשרה לאחר מספר ניסיונות.",
            "error": True,
        }


# --- בלוק בדיקה להרצה ישירה ---
if __name__ == "__main__":
    print("🧪 Testing JobAnalyzer with preservation logic...")

    test_resume = (
        "Yaniv, Software Engineer with 5 years experience in Python and FastAPI."
    )
    test_context = "Looking for remote roles."

    # בדיקה עם URL קיים (סריקה רגילה)
    test_job_with_url = {
        "url": "https://linkedin.com/jobs/123",
        "company": "Tech Corp",
        "job_title": "Python Dev",
        "full_description": "We need a Python developer for a remote role.",
    }

    # בדיקה ללא URL (פוסט פייסבוק / הדבקה ידנית)
    test_job_no_url = {
        "url": None,
        "company": "Facebook Group Post",
        "job_title": "Freelance Project",
        "full_description": "Looking for someone to help with a FastAPI project.",
    }

    analyzer = JobAnalyzer()

    print("\n1. Testing with valid URL:")
    res1 = analyzer.analyze(test_resume, test_context, test_job_with_url)
    print(f"Result URL: {res1.get('url')}")

    print("\n2. Testing with NO URL (None):")
    res2 = analyzer.analyze(test_resume, test_context, test_job_no_url)
    print(f"Result URL: {res2.get('url')}")
