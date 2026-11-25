# JobMatch: הנחיות לסוכנים ולסשנים

המשתמש מדביק הודעות משרות גולמיות (וואטסאפ) או קישורים. השרת מחלץ קישורים, ושלושה workers
מפענחים, סורקים ומנתחים מול קורות החיים עם Gemini. תיאור מלא, הרצה, פריסה ומגבלות השירותים: `README.md`.

## מפה
| איפה | מה |
|---|---|
| `src/server.py` | FastAPI: `/api/*` (טוקן), `/health`, `/ping`, הגשת `dashboard/dist` |
| `src/routes/`, `src/models/job_models.py` | נתיבי API ומודלי הבקשות (חוזה מול הדשבורד) |
| `src/db/postgres.py` | סכמה, `JOB_STATUSES`, migrations idempotent ב-`init_db` |
| `src/db/jobs_repository.py` | כל השאילתות וכל מעברי הסטטוס |
| `src/workers/` | resolver, scraper, AI, תחזוקה, rate limiter, `queue_signal` (התעוררות) |
| `src/scraper_service/` | HireMeTech, ATS APIs (`site_apis.py`), Jina/HTML/Playwright, `validate_content` |
| `src/engine.py` | פרומפט, קריאה ל-Gemini, סכמת התשובה |
| `src/services/` | `link_extractor` (intake + resolver + תצוגה מקדימה), intake, auth, profile, `whatsapp` + `notifier` (בוט, `docs/whatsapp-setup.md`) |
| `src/routes/whatsapp_routes.py` | `/webhooks/whatsapp`: מחוץ ל-`/api`, בלי טוקן, אימות בחתימה. כבוי (404) בלי משתני `WHATSAPP_*` |
| `dashboard/` | React/Vite/Tailwind. `src/services/taskService.js` = כל קריאות ה-API, `src/constants/jobStatus.js`, `src/styles/tokens.css` |
| `tests/` | pytest. בדיקות DB דורשות `TEST_DATABASE_URL`. `tests/js/` רץ ב-Node מתוך pytest |
| `scripts/` | בדיקה על נתונים אמיתיים (**צורכים מכסה**) |
| `docs/design/` | העיצוב, החלטות ונקודות פתוחות |
| `docs/BOARD.md` | לוח המשימות והבעלות בין הסשנים |

## פקודות
- שרת: `run_server.bat`, או `cd src; python server.py`.
- דשבורד: `cd dashboard; npm run dev | npm run lint | npm run build`.
- בדיקות: `pytest`. בדיקות DB: ה-skill `db-tests`.
- `scripts/test_scraper.py`, `scripts/test_analysis.py`: רק באישור (ראה כללים).

## צינור הסטטוסים
הזרימה וה-retry מתועדים בראש `src/workers/worker_manager.py`. הרשימה הקובעת היא `JOB_STATUSES`
ב-`src/db/postgres.py`. ב-`dashboard/src/constants/jobStatus.js` חייבת להופיע תווית לכל ערך,
ו-`tests/test_dashboard_statuses.py` אוכף את זה.

## כללים שאסור לשבור
1. **ה-DB האמיתי (פורט 1212, `.env`) וה-volume `jobmatch_pgdata` אסורים לנגיעה.** בדיקות רצות רק
   על DB ששמו מכיל `test`, ב-`127.0.0.1:5434` וב-compose project נפרד.
2. **בלי אישור, לא מריצים שום דבר שצורך Gemini, Jina או HireMeTech:** ה-workers, השרת מול DB
   אמיתי, `scripts/test_*.py`. מבקשים אישור עם הערכה של מספר הקריאות.
3. בלי אישור: `pip install`, `npm install`/`npm ci`, `playwright install`, `docker compose up`,
   commit, push, מיזוג או מחיקה.
4. כל מעבר סטטוס עובר דרך `jobs_repository`. משרה נתפסת מהתור רק ב-`fetch_next_job`
   (`SKIP LOCKED`). אין `sleep` קבוע בלולאות התור: משתמשים ב-`notify`/`IdleWaiter`.
5. שגיאת API נזרקת כ-`HTTPException`, לעולם לא כ-`return {...}, 400`.
6. כל באג שמתוקן מקבל בדיקה שנכשלת לפני התיקון.
7. משתנה סביבה חדש מתועד ב-`.env.example`, ב-`render.yaml` ובטבלה ב-`README.md`.
8. אין סודות ואין פרטים אישיים בקבצים שבמעקב (`data/` ו-`logs/` ב-gitignore). לא מוסיפים צילום
   של מסך הפרופיל לריפו.
9. Playwright נסגר ב-`finally`.
10. הדשבורד בעברית ו-RTL: מאפיינים לוגיים (`ms-`/`me-`/`ps-`/`pe-`/`start`/`end`), בלי
    `ml-`/`pl-`/`left`/`right`. צבעים ומרווחים רק מ-`tokens.css`.
11. לא ממציאים מגבלות של שירותים חיצוניים. בודקים בתיעוד ומעדכנים את "Limits" ב-README.
12. תיעוד והערות בעברית. commit קטן לכל צעד, וענף נפרד לכל סשן.

## נקודות תיאום: מי שנוגע כאן מעדכן את כל הצדדים באותו commit
1. סטטוס או עמודה: `postgres.py` ← `jobs_repository.py` ← `jobStatus.js` ← בדיקה. ה-skill `schema-change`.
2. חוזה API: `job_models.py` ו-`routes/*` מול `taskService.js`, וטבלת ה-API ב-README.
3. `src/services/link_extractor.py`: משמש את ה-intake, את ה-resolver ואת התצוגה המקדימה. מריצים
   את `test_link_extractor.py`, `test_intake.py` ו-`test_message_to_score.py`.
4. משתנה סביבה: כלל 7.
הבעלות על כל קובץ משותף כתובה ב-`docs/BOARD.md`.

## איך מוסיפים
- **סטטוס או עמודה:** ה-skill `schema-change`.
- **אתר משרות:** ה-skill `new-job-site`.
- **נתיב API:** route ב-`src/routes/`, מודל ב-`job_models.py`, שאילתה ב-`jobs_repository.py`
  (404 כשלא נמצאה שורה), בדיקת HTTP ב-`tests/test_jobs_api.py`, פונקציה ב-`taskService.js`,
  ושורה בטבלת ה-API ב-README.
