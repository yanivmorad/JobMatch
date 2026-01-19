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

        # שימוש במודל יציב ומהיר
        self.model_name = "gemini-2.5-flash"
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        self.headers = {"Content-Type": "application/json"}

    def analyze(
        self, resume: str, context: str, job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """מנתח את המשרה ומבצע תיקון אוטומטי לנתוני המקור"""

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

        for attempt in range(3):
            try:
                # שים לב לשימוש ב-self.api_url ללא מרכאות מיותרות
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()

                text_output = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text_output)

            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(2)

        return {
            "company": raw_company,
            "job_title": raw_title,
            "suitability_score": 0,
            "formatted_message": "שגיאה בניתוח המשרה.",
        }


# --- בלוק בדיקה להרצה ישירה ---
if __name__ == "__main__":
    print("🧪 Testing JobAnalyzer...")

    # 1. נתוני דמו (במציאות זה יגיע מהקבצים שלך)
    test_resume = "Yaniv, Software Engineer with 5 years experience in Python and FastAPI. Expert in AWS and SQL."
    test_context = "I am looking for remote-first positions with a salary of 30k+."

    test_job = {
        "company": "Tech Corp",
        "job_title": "Senior Backend Developer",
        "full_description": "We are looking for a Python expert with 7 years of experience. Must know AWS and Kubernetes. Salary: 35k. Hybrid position in Tel Aviv.",
    }

    # 2. הרצה
    analyzer = JobAnalyzer()
    result = analyzer.analyze(test_resume, test_context, test_job)

    # 3. הדפסת תוצאות
    print("\n--- Analysis Result ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))
