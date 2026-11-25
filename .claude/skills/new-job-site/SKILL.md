---
name: new-job-site
description: תמיכה באתר משרות או ATS חדש בסורק של JobMatch, או תיקון אתר שנסרק לא נכון (תיאור ריק, שלד SPA, משרה סגורה שלא זוהתה, דף התחברות). להשתמש כשמשרות מאתר מסוים נכשלות ב-FAILED_SCRAPE / NO_DATA או מקבלות תיאור שגוי.
---

# תמיכה באתר משרות חדש

הדפוס חזר ב-Workday, BambooHR, HireMeTech, MazeBolt (Comeet ב-WordPress) ו-Workday 403.
הבעלים של הקבצים: S-Pipeline (`docs/BOARD.md`).

## 0. לאבחן לפני שכותבים קוד
- מה הסורק קיבל: `error_log` של המשרה, או `scripts/test_scraper.py` על קישור אחד.
  **הסקריפט צורך Jina (ולפעמים HireMeTech): רק באישור המשתמש**, עם מספר הקישורים.
- סדר הניסיונות ב-`Scraper.scrape` (`src/scraper_service/scraper.py`): API של ה-ATS → Jina →
  HTML ישיר → Playwright. לבחור את השכבה הזולה שעובדת:
  1. **API ציבורי של ה-ATS** (הדף הוא SPA ריק, אבל הדפדפן טוען JSON): handler ב-`site_apis.py`.
  2. **Jina עם selector** (התיאור באלמנט ידוע): `SITE_SELECTORS` ב-`scraper.py` (כמו LinkedIn).
  3. **HTML ישיר** (הדף מרונדר בשרת ו-Jina חותך אותו): `html_extract.py` (`_CONTENT_SELECTORS`).
  4. Playwright: רק אם אין ברירה. כבוי ב-Render החינמי (`ENABLE_PLAYWRIGHT=false`).
- לא להמציא את מבנה ה-API או את המגבלות שלו: לבדוק מול תשובה אמיתית (באישור) או תיעוד.

## 1. API של ATS: `src/scraper_service/site_apis.py`
- פונקציה `_<site>(url, session) -> Optional[SiteApiResult]`: `None` = לא האתר הזה.
  מזהה את ה-URL ב-regex, קורא ל-endpoint עם `_HEADERS`/`TIMEOUT`, ובונה טקסט עם `_document(...)`
  (פורמט Jina: `Title: ...`), וגם `company` ו-`job_title` כשיש.
- משרה שהוסרה: `reason="job_unavailable"` (ראה `_workday_unposted`: 403 S22 = הוסרה, 404 S21 = לא קיימת).
- להוסיף ל-`_HANDLERS`. חריגה ב-handler הופכת ל-`api_error` וממשיכים ל-Jina, ולכן אין צורך ב-try.

## 2. זיהוי תוכן: `src/scraper_service/utils.py` (`validate_content`)
- סימנים חדשים לדף "משרה סגורה", התחברות או שגיאה: `_JOB_UNAVAILABLE`, `_LOGIN`, `_ERROR_PAGE`,
  `_NO_DESCRIPTION`, `_UNAVAILABLE_URL_MARKERS`. לבדוק שהסימן לא מופיע במשרות תקינות.
- הודעה למשתמש לסיבה חדשה: `FAILURE_MESSAGES`. תקלה זמנית: `_TRANSIENT_PREFIXES`.

## 3. בדיקות (בלי רשת)
- `tests/test_site_apis.py`: `_Session` ו-`_Resp` מזויפים עם תשובה **בצורה של ה-API האמיתי**.
  מקרים: זיהוי URL (כן ולא), משרה תקינה, משרה שהוסרה, JSON לא צפוי.
- `tests/test_content_validation.py`: הטקסט שהתקבל בפועל (מקוצר, בלי פרטים אישיים) מסווג נכון.
- `tests/test_html_extract.py` או `tests/test_scraper.py` לפי השכבה.
- להריץ: `C:\Users\yc\JobMatch\.venv\Scripts\python.exe -m pytest tests/test_site_apis.py tests/test_content_validation.py tests/test_scraper.py`.

## 4. סקריפט הבדיקה ותיעוד
- להוסיף את האתר ל-`SITES` ב-`scripts/test_scraper.py`, כדי שיופיע בטבלה לפי אתר.
- עובדה חדשה על האתר (endpoint, קוד שגיאה): docstring ב-handler, ו-handoff ל-S0.
- אם האתר משפיע על חילוץ הקישורים מההודעה (`src/services/link_extractor.py`): נקודת תיאום,
  להריץ גם `test_link_extractor.py`, `test_intake.py` ו-`test_message_to_score.py`.
