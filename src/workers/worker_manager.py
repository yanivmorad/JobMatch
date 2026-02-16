import asyncio
import logging

from db.jobs_repository import (
    fetch_next_job,
    finish_analysis,
    finish_scrape,
    get_job_by_url,
    mark_failed,
    reset_stuck_jobs,
    update_job_after_resolution,
)
from scraper_service.resolvers import URLResolver  # ייבוא ישיר
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
                # ה-Resolver מחליט אם הלינק דורש טיפול או לא
                resolved_url = await asyncio.wait_for(
                    asyncio.to_thread(resolver.resolve, original_url),
                    timeout=60,
                )

                # לוגיקת כפילויות (נשארת אותו דבר, אבל עכשיו היא נקייה יותר)
                if resolved_url and resolved_url != original_url:
                    existing = await get_job_by_url(resolved_url)
                    if existing:
                        await mark_failed(
                            job_id, "DUPLICATE", f"Exists as ID: {existing['id']}"
                        )
                        continue

                    await update_job_after_resolution(
                        job_id, resolved_url, "WAITING_FOR_SCRAPE"
                    )
                else:
                    # הלינק כבר היה "נקי" או שלא נמצא פיענוח
                    await update_job_after_resolution(
                        job_id, original_url, "WAITING_FOR_SCRAPE"
                    )

            except Exception as e:
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
                logger.info(f"🌐 סורק משרה {job_id}: {url}")

                # הרצת ה-Scraper (מנסה Jina ואז Playwright)
                result = await asyncio.wait_for(
                    asyncio.to_thread(scraper.scrape, url), timeout=60
                )

                if result and result.get("full_description"):
                    await finish_scrape(
                        job_id,
                        result.get("company", "Unknown"),
                        result.get("job_title", "Unknown"),
                        result.get("full_description", ""),
                    )
                    logger.info(f"✅ סריקה הושלמה עבור משרה {job_id}. עובר לניתוח AI.")
                else:
                    await mark_failed(
                        job_id, "NO_DATA", "הסורק לא הצליח לחלץ תיאור משרה"
                    )

            except asyncio.TimeoutError:
                await mark_failed(
                    job_id, "FAILED_SCRAPE", "Timeout (60s) during scraping"
                )
            except Exception as e:
                logger.error(f"❌ שגיאה בסריקת משרה {job_id}: {e}")
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
            try:
                logger.info(f"🧠 מנתח משרה {job_id} באמצעות AI...")

                # טעינת קבצי עזר (קורות חיים והקשר נוסף)
                resume = read_text_file(RESUME_PATH)
                context = read_text_file(CONTEXT_PATH)

                # שליחה לניתוח (לוקח הכי הרבה זמן)
                result = await asyncio.wait_for(
                    asyncio.to_thread(analyzer.analyze, resume, context, job),
                    timeout=90,  # זמן ארוך יותר ל-AI
                )

                await finish_analysis(job_id, result)
                logger.info(f"✨ ניתוח AI הושלם עבור משרה {job_id}!")

            except asyncio.TimeoutError:
                await mark_failed(job_id, "FAILED_ANALYSIS", "AI Timeout")
            except Exception as e:
                logger.error(f"❌ שגיאה בניתוח AI של משרה {job_id}: {e}")
                await mark_failed(job_id, "FAILED_ANALYSIS", str(e))
        else:
            await asyncio.sleep(5)


async def start_background_workers():
    """
    פונקציית הניהול הראשית:
    1. מאפסת משרות שנתקעו בגלל קריסה קודמת.
    2. מפעילה את כל ה-Workers כמשימות רקע אסינכרוניות.
    """
    logger.info("🧹 מנקה משרות תקועות ומפעיל את הצינור...")
    await reset_stuck_jobs()

    # הפעלה במקביל של כל יחידות העבודה
    asyncio.create_task(resolver_worker())
    asyncio.create_task(scrape_worker())
    asyncio.create_task(ai_worker())

    logger.info("🚀 כל ה-Workers באוויר (Resolver, Scraper, AI)")
