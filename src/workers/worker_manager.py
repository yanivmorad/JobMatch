import asyncio
import logging

from db.jobs_repository import (
    auto_archive_old_applications,
    fetch_next_job,
    finish_analysis,
    finish_scrape,
    get_job_by_url,
    mark_failed,
    reset_stuck_jobs,
    update_job_after_resolution,
)
from scraper_service.resolvers import URLResolver  # ייבוא ישיר
from scraper_service.utils import failure_message
from services.file_utils import CONTEXT_PATH, RESUME_PATH, read_text_file

# טיפול גמיש בייבוא מנועים
try:
    from engine import JobAnalyzer
    from scraper_service.scraper import Scraper
except ImportError:
    from src.engine import JobAnalyzer
    from src.scraper_service.scraper import Scraper

logger = logging.getLogger("Workers")


async def resolver_worker():
    logger.info("🔍 Resolver Worker started")
    # מאתחלים רק את ה-Resolver, בלי כל ה-Scraper הכבד
    resolver = URLResolver()

    while True:
        job = await fetch_next_job("PENDING_RESOLVE", "RESOLVING")
        if job:
            job_id = job["id"]
            original_url = job["url"]
            try:
                logger.info(
                    f"🔍 [ID {job_id}] Resolver: starting resolution for {original_url}"
                )
                # ה-Resolver מחליט אם הלינק דורש טיפול או לא
                resolved_url = await asyncio.wait_for(
                    asyncio.to_thread(resolver.resolve, original_url, job_id=job_id),
                    timeout=60,
                )

                # לוגיקת כפילויות (נשארת אותו דבר, אבל עכשיו היא נקייה יותר)
                if resolved_url and resolved_url != original_url:
                    logger.info(
                        f"🔗 [ID {job_id}] Resolver: resolved to new URL: {resolved_url}"
                    )
                    existing = await get_job_by_url(resolved_url)
                    if existing:
                        logger.warning(
                            f"🚫 [ID {job_id}] Resolver: resolved URL already exists in DB (Duplicate)"
                        )
                        await mark_failed(
                            job_id, "DUPLICATE", f"Exists as ID: {existing['id']}"
                        )
                        continue

                    await update_job_after_resolution(
                        job_id, resolved_url, "WAITING_FOR_SCRAPE"
                    )
                else:
                    # הלינק כבר היה "נקי" או שלא נמצא פיענוח
                    logger.info(
                        f"✅ [ID {job_id}] Resolver: no changes needed for {original_url}"
                    )
                    await update_job_after_resolution(
                        job_id, original_url, "WAITING_FOR_SCRAPE"
                    )

            except asyncio.TimeoutError:
                logger.error(f"⏲️ [ID {job_id}] Resolver timeout (60s) for {original_url}")
                await mark_failed(job_id, "FAILED_RESOLVE", "Timeout (60s) בפענוח הקישור")
            except Exception as e:
                # ResolveError מכיל הודעה ברורה למשתמש (טוקן חסר / כפתור לא נמצא...)
                logger.error(f"❌ [ID {job_id}] Resolver error for {original_url}: {e}")
                await mark_failed(job_id, "FAILED_RESOLVE", str(e))
        else:
            await asyncio.sleep(5)


async def scrape_worker():
    """
    שלב 2: חילוץ התוכן (Text/Markdown) מאתר המשרה.
    סטטוס: WAITING_FOR_SCRAPE -> WAITING_FOR_AI
    יכולת: הופכת HTML למבנה נתונים נקי (חברה, תיאור, טייטל).
    """
    logger.info("🕷️ Scraper Worker התחיל לעבוד")
    scraper = Scraper()

    while True:
        job = await fetch_next_job("WAITING_FOR_SCRAPE", "SCRAPING")
        if job:
            job_id = job["id"]
            url = job["url"]
            try:
                logger.info(f"🕷️ [ID {job_id}] Scraper: starting to scrape {url}")

                # הרצת ה-Scraper (מנסה Jina ואז Playwright)
                trace = []
                result = await asyncio.wait_for(
                    asyncio.to_thread(scraper.scrape, url, job_id=job_id, trace=trace),
                    timeout=60,
                )

                if result and result.get("full_description"):
                    await finish_scrape(
                        job_id,
                        result["full_description"],
                        company=result.get("company"),
                        title=result.get("job_title"),
                    )
                    logger.info(
                        f"✅ [ID {job_id}] Scraper: completed successfully for {url}"
                    )
                else:
                    reasons = [a.get("reason") for a in trace]
                    logger.warning(
                        f"⚠️ [ID {job_id}] Scraper: no valid content for {url} ({reasons})"
                    )
                    # הודעה ברורה למשתמש לפי סיבת הכישלון (התחברות / משרה סגורה / חסימה...)
                    await mark_failed(job_id, "NO_DATA", failure_message(reasons))

            except asyncio.TimeoutError:
                logger.error(f"⏲️ [ID {job_id}] Scraper timeout (60s) for {url}")
                await mark_failed(
                    job_id, "FAILED_SCRAPE", "Timeout (60s) during scraping"
                )
            except Exception as e:
                logger.error(f"❌ [ID {job_id}] Scraper error for {url}: {e}")
                await mark_failed(job_id, "FAILED_SCRAPE", str(e))
        else:
            await asyncio.sleep(5)


async def ai_worker():
    """
    שלב 3: ניתוח המשרה מול קורות החיים באמצעות LLM.
    סטטוס: WAITING_FOR_AI -> COMPLETED
    יכולת: הפקת ציון התאמה, סיכום בעברית ורשימת יתרונות/חסרונות.
    """
    logger.info("🤖 AI Worker התחיל לעבוד")
    analyzer = JobAnalyzer()

    while True:
        job = await fetch_next_job("WAITING_FOR_AI", "ANALYZING")
        if job:
            job_id = job["id"]
            url = job.get("url", "No URL")
            try:
                logger.info(f"🧠 [ID {job_id}] AI: starting analysis for {url}")

                # טעינת קבצי עזר (קורות חיים והקשר נוסף)
                resume = read_text_file(RESUME_PATH)
                context = read_text_file(CONTEXT_PATH)

                # שליחה לניתוח (לוקח הכי הרבה זמן)
                result = await asyncio.wait_for(
                    asyncio.to_thread(analyzer.analyze, resume, context, job),
                    timeout=90,  # זמן ארוך יותר ל-AI
                )

                await finish_analysis(job_id, result)
                logger.info(f"✨ [ID {job_id}] AI: analysis completed for {url}")

            except asyncio.TimeoutError:
                logger.error(f"⏲️ [ID {job_id}] AI timeout for {url}")
                await mark_failed(job_id, "FAILED_ANALYSIS", "AI Timeout")
            except Exception as e:
                logger.error(f"❌ [ID {job_id}] AI error for {url}: {e}")
                await mark_failed(job_id, "FAILED_ANALYSIS", str(e))
        else:
            await asyncio.sleep(5)


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
        except Exception as e:
            # שגיאה (למשל DB לא זמין רגעית) לא עוצרת את הלולאה - ננסה שוב בסבב הבא
            logger.error(f"❌ Maintenance error: {e}")
        await asyncio.sleep(interval_seconds)


# הפניות למשימות הרקע: asyncio שומר רק weak reference למשימה, ומשימה בלי הפניה
# חזקה עלולה להיאסף ע"י ה-GC באמצע ריצה (ראו התיעוד של asyncio.create_task)
_background_tasks: set = set()


async def start_background_workers():
    """
    פונקציית הניהול הראשית:
    1. מאפסת משרות שנתקעו בגלל קריסה קודמת.
    2. מפעילה את כל ה-Workers כמשימות רקע אסינכרוניות.
    """
    logger.info("🧹 מנקה משרות תקועות ומפעיל את הצינור...")
    await reset_stuck_jobs()

    # הפעלה במקביל של כל יחידות העבודה
    for worker in (resolver_worker, scrape_worker, ai_worker, maintenance_worker):
        task = asyncio.create_task(worker(), name=worker.__name__)
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    logger.info("🚀 כל ה-Workers באוויר (Resolver, Scraper, AI, Maintenance)")
