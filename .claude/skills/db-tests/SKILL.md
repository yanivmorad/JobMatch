---
name: db-tests
description: הרצת בדיקות pytest שדורשות Postgres ב-JobMatch (Windows) על DB בדיקות זמני ב-Docker, בלי לגעת ב-DB האמיתי. להשתמש כשצריך להריץ את בדיקות ה-DB (צינור, retry, תפיסה כפולה, API, פרופיל, ארכוב), כש-pytest מדלג עם "TEST_DATABASE_URL not set", או לפני PR.
---

# בדיקות DB ב-JobMatch

`tests/conftest.py` מוחק את כל הסכמה (`DROP SCHEMA public CASCADE`) בכל בדיקה, ולכן:

- **אסור:** ה-DB האמיתי (פורט 1212, `.env`), ה-compose project ברירת המחדל (`jobmatch`, שה-volume שלו
  `jobmatch_pgdata` מכיל נתונים), והשירות `app` של compose (מריץ workers עם המפתחות = צורך מכסה).
- **תמיד:** `-p jobmatch_test`, רק השירות `db`, ו-DB ששמו מכיל `test`.
- **לכל סשן DB משלו** באותו קונטיינר, כדי ששני סשנים לא ימחקו זה לזה את הסכמה:
  S0 `jobmatch_test` · S-API `jobmatch_test_api` · S-Pipeline `jobmatch_test_pipeline` · S-Infra `jobmatch_test_infra`.
  לא בטוח באיזה סשן אתה? בדוק ב-`docs/BOARD.md`, או שאל.

הפעלת Docker וה-compose מאושרת לבדיקות האלה בלבד (החלטה מ-2026-11-25 ב-`docs/BOARD.md`).

## צעדים (PowerShell, מתיקיית השורש של ה-checkout או ה-worktree)

1. **Docker פועל?** `docker info` מצליח? אם לא:
   `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"`, ואז לבדוק שוב את `docker info`
   כל כמה שניות, עד כ-2 דקות.
2. **פורט 5434 פנוי?** `docker ps --filter "publish=5434" --format "{{.Names}}"`.
   אם רץ שם קונטיינר של project אחר (למשל `jobmatch_e2e2-db-1`), **לא לעצור אותו בלי לשאול**.
3. **להפעיל את ה-DB:** `docker compose -p jobmatch_test up -d db`
   (אם הפורט נשאר ריק אחרי כשל: `docker compose -p jobmatch_test up -d --force-recreate db`).
4. **לחכות שיהיה מוכן:** `docker compose -p jobmatch_test exec db pg_isready -U jobmatch -d jobmatch`.
5. **ליצור את ה-DB של הסשן, אם עוד לא קיים** (`<db>` = השם מהרשימה למעלה):
   `docker compose -p jobmatch_test exec db psql -U jobmatch -d jobmatch -tAc "SELECT 1 FROM pg_database WHERE datname='<db>'"`
   ואם אין פלט: `docker compose -p jobmatch_test exec db createdb -U jobmatch <db>`.
6. **להריץ** (ב-`127.0.0.1`, לא `localhost`: ב-Windows הניסיון ב-IPv6 מאט כל בדיקה):
   ```powershell
   $env:TEST_DATABASE_URL = "postgresql://jobmatch:jobmatch@127.0.0.1:5434/<db>"
   C:\Users\yc\JobMatch\.venv\Scripts\python.exe -m pytest
   ```
   ב-worktree אין `.venv` ואין `.env`: משתמשים ב-Python של ה-checkout הראשי לפי נתיב מלא, ולא מעתיקים את `.env`.
   אפשר להריץ קובץ אחד: `... -m pytest tests/test_jobs_api.py -q`.
7. **לבדוק את הדיווח:** אסור שיישארו דילוגים עם `TEST_DATABASE_URL not set`
   (`-rs` מציג את סיבות הדילוג). דילוג `Node.js not installed` הוא בסדר.
8. **בסוף:** להשאיר את הקונטיינר רץ אם סשן אחר עובד, או `docker compose -p jobmatch_test stop`.
   `down -v` מותר רק עם `-p jobmatch_test`, ורק אם המשתמש ביקש.

## דיווח
מספרי passed/skipped/failed, וכל כישלון עם שם הבדיקה והשגיאה. כישלון שאינו קשור לשינוי שלך מדווחים
ל-S0 ולא מתקנים אותו בקבצים שאינם בבעלותך.
