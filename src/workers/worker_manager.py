"""
צינור העיבוד: 3 workers שמשתמשים ב-Postgres כתור (FOR UPDATE SKIP LOCKED) + תחזוקה יומית.

    PENDING_RESOLVE -> (resolver) -> WAITING_FOR_SCRAPE -> (scraper) -> WAITING_FOR_AI -> (ai) -> COMPLETED

כל צעד הוא פונקציה שמטפלת במשרה אחת (resolve_next / scrape_next / analyze_next) ומחזירה
האם הייתה עבודה. _run_loop מריץ אותה בלולאה:
- תור ריק -> IdleWaiter (מתעורר מיד ב-notify, אחרת בדיקה כל 1, 2, 4... עד 60 שניות)
- שגיאה של הלולאה עצמה (למשל ה-DB לא זמין רגעית) -> רישום והמתנה, וה-worker ממשיך לחיות.
  (קודם חריגה כזו הרגה את ה-worker בשקט, והצינור נעצר עד הפעלה מחדש)

ניסיונות חוזרים: תקלה זמנית (timeout / 5xx / רשת) -> fail_or_retry: חוזרת לתור עם backoff
עד MAX_JOB_ATTEMPTS (ברירת מחדל 3), ואז FAILED_*. 429 של Gemini -> המשרה חוזרת לתור בלי
להיספר כניסיון, וה-AI worker ממתין (rate_limiter).
"""
import asyncio
import logging
import os
import time
from typing import Callable, Dict

from db.jobs_repository import (
    auto_archive_old_applications,
    fail_or_retry,
    fetch_next_job,
    find_existing_job,
    finish_analysis,
    finish_scrape,
    get_api_usage,
    increment_api_usage,
    mark_failed,
    requeue_in_progress,
    requeue_job,
    reset_stuck_jobs,
    update_job_after_resolution,
)
from scraper_service.resolvers import (
    ResolveError,
    URLResolver,
    hiremetech_token_status,
    is_hiremetech,
)
from scraper_service.utils import failure_message
from services.file_utils import CONTEXT_PATH, RESUME_PATH, read_text_file
from services.link_extractor import normalize_job_url
from workers.queue_signal import IdleWaiter, notify
from workers.rate_limiter import AIRateLimiter, ModelPool

# טיפול גמיש בייבוא מנועים
try:
    from engine import JobAnalyzer, RateLimitError, configured_models
    from scraper_service.scraper import Scraper
except ImportError:
    from src.engine import JobAnalyzer, RateLimitError, configured_models
    from src.scraper_service.scraper import Scraper

logger = logging.getLogger("Workers")

RESOLVE_TIMEOUT_SECONDS = 60
# Jina (עד 25 שניות, לפעמים פעמיים) + Playwright (עד ~45) - 60 לא הספיק כש-Jina איטי
SCRAPE_TIMEOUT_SECONDS = 90
AI_TIMEOUT_SECONDS = 150  # עד 2 בקשות (retry על סכמה) של עד 60 שניות כל אחת
LOOP_ERROR_MAX_BACKOFF = 60


def max_attempts() -> int:
    try:
        return max(1, int(os.getenv("MAX_JOB_ATTEMPTS") or 3))
    except ValueError:
        return 3


# --- מצב ה-workers (ל-/health) ---

_state: Dict[str, dict] = {}
_tasks: Dict[str, asyncio.Task] = {}
ai_pool: ModelPool = None  # נוצר ב-ai_worker (צריך את שמות המודלים)


def _touch(name: str, **fields) -> None:
    entry = _state.setdefault(name, {"jobs": 0, "last_job_at": None, "last_error": None})
    entry.update(fields)


def workers_status() -> dict:
    """לכל worker: האם המשימה חיה, כמה משרות טופלו, מתי לאחרונה, שגיאה אחרונה."""
    out = {}
    for name in ("resolver_worker", "scrape_worker", "ai_worker", "maintenance_worker"):
        task = _tasks.get(name)
        out[name] = {
            "running": bool(task and not task.done()),
            **_state.get(name, {}),
        }
    if ai_pool:
        out["ai_worker"]["models"] = ai_pool.status()
    return out


# --- שלב 1: פענוח קישור ---


async def resolve_next(resolver: URLResolver) -> bool:
    job = await fetch_next_job("PENDING_RESOLVE", "RESOLVING")
    if not job:
        return False
    job_id, original_url = job["id"], job["url"]
    logger.info(f"🔍 [ID {job_id}] Resolver: starting resolution for {original_url}")
    try:
        resolved_url = await asyncio.wait_for(
            asyncio.to_thread(resolver.resolve, original_url, job_id=job_id),
            timeout=RESOLVE_TIMEOUT_SECONDS,
        )
        # הקישור מאתר החברה מגיע לרוב עם utm (למשל ?utm_source=hiremetech)
        resolved_url = normalize_job_url(resolved_url) if resolved_url else original_url
        if resolved_url != original_url:
            logger.info(f"🔗 [ID {job_id}] Resolver: resolved to {resolved_url}")
            existing = await find_existing_job(resolved_url, exclude_id=job_id)
            if existing:
                logger.warning(f"🚫 [ID {job_id}] Resolver: duplicate of ID {existing['id']}")
                await mark_failed(job_id, "DUPLICATE", f"Exists as ID: {existing['id']}")
                return True
        await update_job_after_resolution(job_id, resolved_url, "WAITING_FOR_SCRAPE")
        notify("WAITING_FOR_SCRAPE")

    except asyncio.TimeoutError:
        logger.error(f"⏲️ [ID {job_id}] Resolver timeout ({RESOLVE_TIMEOUT_SECONDS}s) for {original_url}")
        if is_hiremetech(original_url):
            await update_job_after_resolution(
                job_id, original_url, "WAITING_FOR_SCRAPE",
                note="HireMeTech: הפענוח לקח יותר מדי זמן (נותח לפי הדף הציבורי, בלי שם החברה)",
            )
            notify("WAITING_FOR_SCRAPE")
        else:
            await fail_or_retry(job_id, "PENDING_RESOLVE", "FAILED_RESOLVE",
                                f"Timeout ({RESOLVE_TIMEOUT_SECONDS}s) בפענוח הקישור", max_attempts())
    except ResolveError as e:
        if e.public_fallback:
            # HireMeTech: התיאור ציבורי - ממשיכים לסריקת הדף עצמו (בלי שם החברה),
            # וההערה נשמרת ב-error_log כדי שהמשתמש יידע לעדכן את הטוקן
            logger.warning(f"↪️ [ID {job_id}] Resolver: {e} - scraping the public page instead")
            await update_job_after_resolution(
                job_id, original_url, "WAITING_FOR_SCRAPE",
                note=f"{e} (נותח לפי הדף הציבורי, בלי שם החברה)",
            )
            notify("WAITING_FOR_SCRAPE")
        else:
            logger.error(f"❌ [ID {job_id}] Resolver error for {original_url}: {e}")
            await mark_failed(job_id, "FAILED_RESOLVE", str(e))
    except Exception as e:
        logger.error(f"❌ [ID {job_id}] Resolver error for {original_url}: {e}")
        await fail_or_retry(job_id, "PENDING_RESOLVE", "FAILED_RESOLVE", str(e), max_attempts())
    return True


# --- שלב 2: סריקה ---


async def scrape_next(scraper: Scraper) -> bool:
    job = await fetch_next_job("WAITING_FOR_SCRAPE", "SCRAPING")
    if not job:
        return False
    job_id, url = job["id"], job["url"]
    logger.info(f"🕷️ [ID {job_id}] Scraper: starting to scrape {url}")
    try:
        trace = []
        result = await asyncio.wait_for(
            asyncio.to_thread(scraper.scrape, url, job_id=job_id, trace=trace),
            timeout=SCRAPE_TIMEOUT_SECONDS,
        )
        if result and result.get("full_description"):
            await finish_scrape(
                job_id, result["full_description"],
                company=result.get("company"), title=result.get("job_title"),
            )
            logger.info(f"✅ [ID {job_id}] Scraper: done ({result.get('source')})")
            notify("WAITING_FOR_AI")
        else:
            # תשובה סופית (משרה סגורה / התחברות / CAPTCHA) - אין טעם לנסות שוב אוטומטית
            reasons = [a.get("reason") for a in trace]
            logger.warning(f"⚠️ [ID {job_id}] Scraper: no valid content ({reasons})")
            await mark_failed(job_id, "NO_DATA", failure_message(reasons))
    except asyncio.TimeoutError:
        logger.error(f"⏲️ [ID {job_id}] Scraper timeout ({SCRAPE_TIMEOUT_SECONDS}s) for {url}")
        await fail_or_retry(job_id, "WAITING_FOR_SCRAPE", "FAILED_SCRAPE",
                            f"Timeout ({SCRAPE_TIMEOUT_SECONDS}s) during scraping", max_attempts())
    except Exception as e:
        logger.error(f"❌ [ID {job_id}] Scraper error for {url}: {e}")
        await fail_or_retry(job_id, "WAITING_FOR_SCRAPE", "FAILED_SCRAPE", str(e), max_attempts())
    return True


# --- שלב 3: ניתוח AI ---


async def analyze_next(pool: ModelPool) -> bool:
    # ממתינים לתור של המכסה *לפני* שלוקחים משרה, כדי שלא תישאר ב-ANALYZING בזמן ההמתנה
    analyzer, limiter = await pool.acquire()
    job = await fetch_next_job("WAITING_FOR_AI", "ANALYZING")
    if not job:
        return False
    job_id, url = job["id"], job.get("url", "No URL")
    logger.info(f"🧠 [ID {job_id}] AI ({analyzer.model_name}): starting analysis for {url}")

    resume = read_text_file(RESUME_PATH)
    context = read_text_file(CONTEXT_PATH)
    await limiter.record_request()
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(analyzer.analyze, resume, context, job),
            timeout=AI_TIMEOUT_SECONDS,
        )
    except RateLimitError as e:
        until = limiter.on_rate_limited(e)
        logger.warning(f"⏸️ [ID {job_id}] AI: Gemini quota hit - job back in queue, paused until {until.isoformat()}")
        await requeue_job(job_id, "WAITING_FOR_AI")
        return True
    except asyncio.TimeoutError:
        logger.error(f"⏲️ [ID {job_id}] AI timeout ({AI_TIMEOUT_SECONDS}s)")
        await fail_or_retry(job_id, "WAITING_FOR_AI", "FAILED_ANALYSIS",
                            f"AI Timeout ({AI_TIMEOUT_SECONDS}s)", max_attempts())
        return True
    except Exception as e:  # TransientAIError / InvalidAIResponse / AIError
        logger.error(f"❌ [ID {job_id}] AI error: {e}")
        await fail_or_retry(job_id, "WAITING_FOR_AI", "FAILED_ANALYSIS", str(e), max_attempts())
        return True

    limiter.on_success()
    await finish_analysis(job_id, result)
    logger.info(f"✨ [ID {job_id}] AI: {result.get('suitability_score')} - {result.get('job_title')} @ {result.get('company')}")
    return True


# --- לולאת worker משותפת ---


async def _run_loop(name: str, status: str, step: Callable) -> None:
    idle = IdleWaiter(status)
    error_backoff = 1.0
    while True:
        try:
            worked = await step()
            error_backoff = 1.0
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # למשל ה-DB נפל / Neon התנתק: לא מפילים את ה-worker
            logger.exception(f"❌ {name}: loop error, retrying in {error_backoff:.0f}s: {e}")
            _touch(name, last_error=f"{type(e).__name__}: {e}"[:300])
            await asyncio.sleep(error_backoff)
            error_backoff = min(error_backoff * 2, LOOP_ERROR_MAX_BACKOFF)
            continue
        if worked:
            _touch(name, jobs=_state.get(name, {}).get("jobs", 0) + 1, last_job_at=time.time())
            idle.reset()
        else:
            await idle.wait()


async def resolver_worker():
    logger.info("🔍 Resolver Worker started")
    resolver = URLResolver()  # בלי ה-Scraper הכבד
    token = hiremetech_token_status(resolver.hireme_token)
    if not token["configured"] or token["expired"]:
        logger.warning(
            f"⚠️ HireMeTech token {'missing' if not token['configured'] else 'expired at ' + token['expires_at']}"
            " - HireMeTech jobs will be analyzed from the public page, without the company name"
        )
    await _run_loop("resolver_worker", "PENDING_RESOLVE", lambda: resolve_next(resolver))


async def scrape_worker():
    logger.info("🕷️ Scraper Worker started")
    scraper = Scraper()
    await _run_loop("scrape_worker", "WAITING_FOR_SCRAPE", lambda: scrape_next(scraper))


def build_model_pool() -> ModelPool:
    members = []
    for model in configured_models():
        limiter = AIRateLimiter(model, get_usage=get_api_usage, add_usage=increment_api_usage)
        members.append((JobAnalyzer(model), limiter))
    return ModelPool(members)


async def ai_worker():
    global ai_pool
    logger.info("🤖 AI Worker started")
    ai_pool = build_model_pool()
    first = ai_pool.members[0][1]
    logger.info(
        f"🤖 AI: models={[a.model_name for a, _ in ai_pool.members]}, GEMINI_RPM={first.rpm}, "
        f"GEMINI_RPD={first.rpd or 'no local cap'}"
    )
    await _run_loop("ai_worker", "WAITING_FOR_AI", lambda: analyze_next(ai_pool))


MAINTENANCE_INTERVAL_SECONDS = 24 * 60 * 60


async def maintenance_worker(interval_seconds: float = MAINTENANCE_INTERVAL_SECONDS):
    """
    תחזוקה יומית: הגשות בלי מענה מעל 30 יום -> ghosted (לפי applied_at).
    רץ מיד בהפעלה ואז פעם ב-interval. בשירות שנרדם (Render חינמי) הריצה בהפעלה
    היא זו שמבטיחה שזה קורה גם כשהשרת לא היה ער 24 שעות ברצף.
    """
    logger.info("🧹 Maintenance Worker started")
    while True:
        try:
            count = await auto_archive_old_applications()
            if count:
                logger.info(f"👻 Maintenance: {count} applications marked as ghosted")
            _touch("maintenance_worker", last_job_at=time.time())
        except Exception as e:
            # שגיאה (למשל DB לא זמין רגעית) לא עוצרת את הלולאה - ננסה שוב בסבב הבא
            logger.error(f"❌ Maintenance error: {e}")
            _touch("maintenance_worker", last_error=str(e)[:300])
        await asyncio.sleep(interval_seconds)


# הפניות למשימות הרקע: asyncio שומר רק weak reference למשימה, ומשימה בלי הפניה
# חזקה עלולה להיאסף ע"י ה-GC באמצע ריצה (ראו התיעוד של asyncio.create_task)
_background_tasks: set = set()


async def start_background_workers():
    """
    1. משרות שנשארו "בטיפול" מהריצה הקודמת חוזרות לתור (וכל קריסה נספרת כניסיון).
    2. מפעילה את כל ה-workers כמשימות רקע.
    """
    stuck = await reset_stuck_jobs(max_attempts())
    if stuck:
        logger.warning(f"🧹 Jobs left in progress by the previous run: {stuck}")

    for worker in (resolver_worker, scrape_worker, ai_worker, maintenance_worker):
        task = asyncio.create_task(worker(), name=worker.__name__)
        _tasks[worker.__name__] = task
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        task.add_done_callback(_log_worker_exit)

    logger.info("🚀 כל ה-Workers באוויר (Resolver, Scraper, AI, Maintenance)")


def _log_worker_exit(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    if task.exception():
        logger.error(f"💀 {task.get_name()} stopped: {task.exception()!r}")


async def stop_background_workers():
    """
    כיבוי מסודר (SIGTERM - דיפלוי / שינה של Render): עוצרים את הלולאות ומחזירים לתור
    משרות שהיו באמצע, *בלי* לספור את זה כניסיון כושל.
    """
    for task in list(_background_tasks):
        task.cancel()
    if _background_tasks:
        await asyncio.gather(*_background_tasks, return_exceptions=True)
    released = await requeue_in_progress()
    if released:
        logger.info(f"↩️ Returned {released} in-progress jobs to the queue")
