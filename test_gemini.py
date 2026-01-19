import os, json, requests, time
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
model_name = "gemini-3-flash-preview"  # או "gemini-2.5-flash" כבדיקה

url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
headers = {"Content-Type": "application/json"}

prompt = "שלום — בדיקת חיבור קצרה. כתוב OK אם עובד."

payload = {
    "contents": [
        {
            "parts": [
                {"text": prompt}
            ]
        }
    ]
}

try:
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    # בדוק מבנה תגובה תקין לפני json.loads על טקסט פנימי
    print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
except requests.exceptions.HTTPError as e:
    print("HTTP error:", e, r.status_code, r.text[:1000])
except Exception as e:
    print("Other error:", e)
