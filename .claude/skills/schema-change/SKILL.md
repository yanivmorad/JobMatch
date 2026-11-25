---
name: schema-change
description: הוספה או שינוי של סטטוס משרה, עמודה או טבלה ב-JobMatch לאורך כל השכבות (סכמה, repository, route, דשבורד, בדיקות). להשתמש בכל שינוי ב-JOB_STATUSES, ב-init_db, או כשמוסיפים שדה שהדשבורד או ה-API צריכים.
---

# שינוי סכמה או סטטוס לאורך השכבות

הדפוס חזר ב-`FAILED_RESOLVE`, `retry_count`/`not_before`, `source_url`, `applied_at` ובטבלת `profile`.
זו נקודת תיאום (`AGENTS.md`): הכל באותו ענף, ו-handoff עם סעיף "שינויים משותפים".
הבעלים של הקבצים האלה הוא S-API (`docs/BOARD.md`).

## 1. סכמה: `src/db/postgres.py`
- **סטטוס:** להוסיף ערך ל-`JOB_STATUSES`. `init_db` מוסיף אותו ל-enum עם
  `ALTER TYPE job_status ADD VALUE IF NOT EXISTS` (לא לשנות את המנגנון).
- **עמודה:** להוסיף גם ל-`CREATE TABLE IF NOT EXISTS jobs` (DB חדש) וגם כ-
  `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ...` בסעיף ה-Migrations (DB קיים, כולל Neon).
  ערך ראשוני לשורות קיימות = `UPDATE ... WHERE <col> IS NULL` (idempotent, כמו `source_url`).
  migration מורכב = פונקציה נפרדת, כמו `_migrate_applied_at`.
- **טבלה:** `CREATE TABLE IF NOT EXISTS`, כמו `profile` ו-`api_usage`.
- הכל חייב להיות בטוח להרצה חוזרת: `init_db` רץ בכל הפעלה.

## 2. גישה: `src/db/jobs_repository.py`
- כל קריאה או כתיבה, וכל מעבר סטטוס, רק כאן. משרה נתפסת מהתור רק ב-`fetch_next_job`.
- עדכון לפי url/id: להחזיר אם שורה נמצאה (`RETURNING` או בדיקת `UPDATE 0`), כדי שה-route יחזיר 404.
- שדה חדש שהדשבורד צריך: לוודא שהוא נבחר ב-`get_all_jobs`/`_flatten` וב-`get_job_by_id`.

## 3. ה-workers (רק לסטטוס)
- איזה worker מעביר אליו וממנו: `src/workers/worker_manager.py`, ולעדכן את ה-docstring שבראשו.
- סטטוס כישלון: להחליט מה `retry_job` עושה איתו (ה-`CASE` שם).
- קבצים אלה בבעלות S-Pipeline. מחוץ לחריגה מוסכמת בלוח, מבקשים מ-S0.

## 4. API: `src/routes/`, `src/models/job_models.py`
- שדה קלט = מודל Pydantic (ערכים סגורים = `Literal`). שגיאה = `HTTPException`.

## 5. דשבורד
- **סטטוס:** תווית ב-`dashboard/src/constants/jobStatus.js` (וקבוצה/צבע לפי הקובץ).
  `tests/test_dashboard_statuses.py` נכשל אם חסר ערך.
- **שדה:** הקריאה ב-`dashboard/src/services/taskService.js`, והתצוגה ב-`dashboard/src/utils/jobView.js`
  או במסך הרלוונטי.

## 6. בדיקות
- `tests/test_db_init.py`: ה-migration עובד על DB ריק **ועל** DB בסכמה ישנה, ופעמיים ברצף.
- בדיקת repository ובדיקת HTTP (`tests/test_jobs_api.py`) לשדה או למעבר החדש.
- להריץ עם ה-skill `db-tests`, ואז `cd dashboard; npm run lint; npm run build` אם הדשבורד השתנה.

## 7. תיעוד
- סטטוס: תרשים הצינור בראש `README.md`. משתנה סביבה חדש: `AGENTS.md` כלל 7.
- handoff: "שינויים משותפים" → סכמה/סטטוס, כדי ש-S0 יודיע לשאר הסשנים לבצע rebase.
