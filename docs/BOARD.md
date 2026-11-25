# לוח המשימות

> נערך רק על ידי S0 (המתאם), ונכנס ל-`main`. סשן אחר קורא אותו עם
> `git show origin/main:docs/BOARD.md` ומדווח ל-S0 בהודעה או בקובץ handoff (`docs/handoff/T<n>.md`,
> לפי `docs/handoff/TEMPLATE.md`). פרומפט הפתיחה של כל סשן: `docs/sessions/`.
> סטטוסים: פתוח · בעבודה · ב-PR · מוזג · חסום

## סשנים
| סשן | ענפים | DB בדיקות (127.0.0.1:5434) | בבעלותו |
|---|---|---|---|
| S0 מתאם | `redesign`, `chore/<נושא>` | `jobmatch_test` | `docs/BOARD.md`, מיזוגים, ענפים |
| S-API | `api/<T>` | `jobmatch_test_api` | `src/db/`, `src/routes/`, `src/models/`, `src/server.py`, `src/services/{intake,auth,profile_service,job_fields}.py`, `dashboard/src/services/taskService.js`, `dashboard/src/components/screens/{Intake,Profile}Screen.jsx` (ל-T5 ול-T10) |
| S-Pipeline | `pipeline/<T>` | `jobmatch_test_pipeline` | `src/workers/`, `src/scraper_service/`, `src/engine.py`, `src/services/{description,link_extractor}.py`, `scripts/` |
| S-Infra | `infra/<T>` | `jobmatch_test_infra` | `.github/`, `Dockerfile`, `docker-compose.yml`, `render.yaml`, `requirements*.txt`, `README.md`, `.env.example`, `dashboard/README.md` |

**חריגות מוסכמות:** S-API מוסיף שורת קריאה ב-`src/workers/worker_manager.py` (`maintenance_worker`)
עבור T17. כל סשן שמוסיף משתנה סביבה מוסיף שורה ב-`.env.example`, ב-`render.yaml` ובטבלה ב-README.
את המבנה של שלושת הקבצים קובע S-Infra.

## משימות
| מזהה | P | משימה | בעלים | סטטוס | תלוי ב | ענף / PR |
|---|---|---|---|---|---|---|
| T1 | P0 | בדיקות DB (59) + תיקונים | S0 | הושלם 2026-11-25: 353 עברו, 0 דולגו, אין תיקונים | — | `redesign` |
| T3 | P1 | מיזוג `redesign` ל-`main` + מחיקת ענפים שמוזגו | S0 | מוזג 2026-11-25 (fast-forward). מחיקת ענפים: ממתין לאישור | T1 | `redesign` |
| T0 | P1 | הגדרות: AGENTS/CLAUDE/.claude/BOARD | S0 | מוזג 2026-11-25 (ישירות ל-`main`, באישור) | T3 | `main` |
| T2 | P0 | API לא חשוף ברשת (`HOST`, 127.0.0.1) | S-API | פתוח | T0 | |
| T4 | P1 | 404 + `Literal` ל-action + בדיקות HTTP | S-API | פתוח | T2 | |
| T5 | P1 | חוזה משרה ידנית (`url`) | S-API | פתוח | T4 | |
| T17 | P2 | מחיקה אוטומטית מהארכיון (`ARCHIVE_RETENTION_DAYS`=90) | S-API | פתוח | T4 | |
| T12a | P2 | לוגי console בדשבורד רק ב-DEV | S-API | פתוח | T0 | |
| T12b | P2 | צמצום `/health` · docstring 60/3600 | S-API · S-Pipeline | פתוח | T0 | |
| T10 | P2 | `updated_at` לפרופיל | S-API | פתוח | T4 | |
| T13 | P2 | `/results` קל יותר | S-API | פתוח | T5 | |
| T14 | P2 | thread שממשיך אחרי timeout | S-Pipeline | פתוח | T0 | |
| T11 | P2 | `test_analysis.py` מה-DB | S-Pipeline | פתוח | T0 | |
| T6 | P1 | CI | S-Infra | פתוח | T0 | |
| T15 | P2 | Python 3.12 ב-venv | S-Infra | פתוח | T0 | |
| T7 | P1 | התאמת תיעוד | S-Infra | פתוח | T2, T4, T5 | |
| T8 | P0 | פריסה Render + Neon | S0 | עלה 2026-11-25: `https://jobmatch-oqbq.onrender.com` (Free, Docker, Frankfurt). `/ping`, `/health` (DB 8ms, 4 workers), הדשבורד ו-401 בלי טוקן נבדקו | T3 | `main` (`a9ae914`) |
| T18 | P0 | בדיקת קצה לקצה: הודעת וואטסאפ אמיתית ← ציון בדשבורד. מקומית לפני הפריסה, ושוב על הענן | S0 | הושלם 2026-11-26 על הענן (בלי סיבוב מקומי): 4 משרות (HireMeTech עם טוקן, Comeet, Lever, Greenhouse) ← ציון תוך ~2 דקות, 2 קישורים שאינם משרות סוננו, 5 קריאות Gemini. 2 באגים בכותרת תוקנו (`a9b0a45`, `a8b7da1`) | T8 | `main` |
| T16 | P1 | בוט וואטסאפ (WhatsApp Cloud API): webhook, חתימה, רשימת מספרים מורשים, כפילויות, ציון חוזר לשולח | S0 | ב-PR: הקוד והבדיקות מוכנים, כבוי עד שמגדירים את Meta (`docs/whatsapp-setup.md`). טלגרם: אותו `notifier`, ערוץ נוסף | T8, T18 | `feat/whatsapp-bot` |

## ממצאים פתוחים (נאספו ב-2026-11-25, לאמת לפני תיקון)
| # | ממצא | איפה | משימה |
|---|---|---|---|
| F1 | השרת מאזין על `0.0.0.0` ובלי `API_TOKEN` מקומית: קורות החיים חשופים ברשת. כבר יש אזהרה ב-startup | `run_server.bat`, `src/server.py` (`__main__`), `src/services/auth.py` | T2 |
| F2 | retry, action, application-status, manual-update, manual-content ו-delete מחזירים 200 על משרה שלא קיימת | `src/routes/jobs_routes.py`, `src/db/jobs_repository.py` | T4 |
| F3 | `ActionRequest.action` מחרוזת חופשית: כל ערך שאינו `none` מעביר לארכיון | `src/models/job_models.py`, `update_user_action` | T4 |
| F4 | הדשבורד שולח `url` ב-`POST /jobs/text`, ו-`TextSubmission` זורק אותו בשקט | `taskService.js` (`addManualJob`), `useJobActions.js`, `job_models.py` | T5 |
| F7 | שבעה נתיבים חסרים בטבלת ה-API ב-README. `dashboard/README.md` הוא תבנית Vite | `README.md` | T7 |
| F8 | `DB_POOL_MAX`, `DASHBOARD_DIR` חסרים ב-`.env.example` | `src/db/postgres.py`, `src/server.py` | T7 |
| F9 | בלי בדיקת HTTP: `DELETE /jobs`, `/jobs/action`, `DELETE /history`, `/jobs/manual-update`, `/jobs/{id}/manual-content`, `/jobs/retry`. בלי בדיקה: `update_manual_job`, `manual_update_job_content`, `clear_archived_jobs`, `requeue_job`, `get_job_by_id` | `tests/` | T4 |
| F13 | `asyncio.wait_for` סביב `to_thread` לא עוצר את ה-thread אחרי timeout (הוסק) | `src/workers/worker_manager.py` | T14 |
| F14 | `/results` מחזיר תיאורים מלאים. מוקל חלקית: הדשבורד מושך רק כש-`version` משתנה | `get_all_jobs` | T13 |
| F15 | `scripts/test_analysis.py` קורא את הפרופיל מ-`data/` ולא מה-DB | `scripts/test_analysis.py` | T11 |
| F16 | interceptors ב-`taskService.js` כותבים ל-console כל בקשה ותשובה (כולל קורות חיים), גם ב-build ייצור | `dashboard/src/services/taskService.js` | T12a |
| F17 | `/health` פתוח ומחזיר פירוט שגיאות DB ותוקף טוקן HireMeTech. ה-docstring של `worker_manager` אומר 60 שניות, ברירת המחדל 3600 (`queue_signal.py`) | `src/server.py`, `src/workers/worker_manager.py` | T12b |
| F19 | ה-venv המקומי Python 3.10, ה-image 3.12 | `requirements*.txt`, `Dockerfile` | T15 |

## החלטות
- 2026-11-25 `DELETE /api/history` ממשיך למחוק את כל הארכיון (F6 נסגר). 135 הכותרות "Unknown" לא מתוקנות.
- 2026-11-25 מחיקה אוטומטית מהארכיון אחרי 90 יום (T17).
- 2026-11-25 תקציב לבדיקות אמיתיות: עד 10 קריאות Gemini להרצה, תמיד באישור. בדיקות אוטומטיות = mock בלבד.
- 2026-11-25 `redesign` ממוזג אחרי ש-T1 עובר.
- 2026-11-25 המטרה: הכל עובד מקצה לקצה עם הדשבורד הקיים, פרוס על הענן (T8 + T18), בלי תקלות קצה.
  אחר כך בוט טלגרם להזנת קישורים ביומיום (T16). וואטסאפ ירד מהתוכנית.
- 2026-11-26 וואטסאפ חוזר לתוכנית (בקשת המשתמש): בוט רשמי דרך WhatsApp Cloud API, לא whatsapp-web
  (לא רץ על Render החינמי ומפר את תנאי השימוש). טלגרם, אם יבוא, נכנס לאותו `notifier`.
- 2026-11-26 כותרת שנוחשה מההודעה היא רמז ל-AI: אחרי הניתוח מוצג שם המשרה שה-AI קרא בדף. ערך
  שהמשתמש הקליד (משרה ידנית או עריכה) לא נדרס.
- 2026-11-25 תיאום: קבצים ו-git הם מקור האמת. הודעות בין סשנים רק כהתראה. agent teams לא בשימוש
  (ניסיוני, בלי worktree ובלי resume ל-teammates).

## חסמים ושאלות פתוחות
- T8: Neon נוצר 2026-11-25: פרויקט `jobmatch` (`curly-thunder-42165976`), branch `production`, Frankfurt, Free.
  Render: ל-GitHub App של Render נוספה גישה ל-`JobMatch` (ול-`myWhatsAppBot` בלבד). Blueprint `jobmatch`,
  שירות `srv-dc3knr49v7es73cen8hg`. Docker רץ ב-Free. `HIRE_ME_TECH_TOKEN`, `RESUME_TEXT` ו-`PERSONAL_CONTEXT_TEXT`
  לא הוגדרו: הפרופיל נכנס דרך מסך הפרופיל. `API_TOKEN` נחשף בצילום מסך בשיחה: להחליף (לא אומת שהוחלף).
  `render.yaml`: נוסף `region: frankfurt`, ליד Neon (ברירת המחדל הייתה Oregon).
  ה-workspace ב-Render מכיל גם את `home-visit-*` ואת RidePals: 750 השעות החינמיות משותפות להם.
- מגבלות Gemini המדויקות מופיעות רק ב-AI Studio, אחרי התחברות (המשתמש).

## יומן מיזוגים
| תאריך | ענף | PR | הערות |
|---|---|---|---|
| 2026-11-25 | `redesign` | — (fast-forward, באישור המשתמש) | `main` = `ca3c3fa`. כולל את התיקונים Workday 403 וניקוי הכותרת |
| 2026-11-26 | `fix/e2e-titles` | — (fast-forward, באישור המשתמש לתקן באגים ולהעלות) | `main` = `a8b7da1`, נפרס ב-Render |
