# src/workers/worker_manager.py
import asyncio
import logging

from db.jobs_repository import (
    fetch_next_job,
    finish_analysis,
    finish_scrape,
    mark_failed,
    reset_stuck_jobs,
)
from services.file_utils import CONTEXT_PATH, RESUME_PATH, read_text_file

# נסה לייבא את המנועים
try:
    from engine import JobAnalyzer
    from scraper import Scraper
except ImportError:
    from src.engine import JobAnalyzer
    from src.scraper import Scraper

logger = logging.getLogger("Workers")


async def scrape_worker():
    logger.info("🕷️ Scraper Worker started")
    scraper = Scraper()

    while True:
        job = await fetch_next_job("WAITING_FOR_SCRAPE", "SCRAPING")
        if job:
            try:
                original_url = job["url"]
                logger.info(f"🕷️ Processing: {original_url}")

                # --- STEP 1: PRE-SCRAPE URL RESOLUTION CHECK ---
                # Check if this is a special URL (e.g., HireMeTech) that needs resolution
                resolved_url = original_url

                if "hiremetech" in original_url:
                    logger.info("🔍 Detected HireMeTech URL, resolving...")
                    # Use the resolver to get the actual company URL
                    resolved_url = await asyncio.to_thread(
                        scraper.resolver.resolve, original_url
                    )

                    # --- STEP 2: UPDATE URL IN DATABASE IF RESOLVED ---
                    if resolved_url != original_url:
                        logger.info(f"✅ Resolved: {original_url} → {resolved_url}")

                        # Import here to avoid circular dependency
                        from db.jobs_repository import (
                            delete_job_by_id,
                            get_job_by_url,
                            update_job_url,
                        )

                        # Check if the resolved URL already exists in our database
                        existing_job = await get_job_by_url(resolved_url)

                        if existing_job:
                            logger.warning(
                                f"⏭️ DUPLICATE DETECTED: Resolved URL '{resolved_url}' "
                                f"already exists in DB (Job ID: {existing_job['id']}). "
                                f"Deleting duplicate job ID {job['id']}."
                            )
                            # Delete the duplicate job
                            await delete_job_by_id(job["id"])
                            # Skip to next job without scraping
                            continue
                        else:
                            # Update the job URL in the database
                            logger.info(
                                f"📝 Updating job URL in database: {original_url} → {resolved_url}"
                            )
                            await update_job_url(job["id"], resolved_url)
                            # Let the next iteration pick up the updated URL
                            logger.info(
                                "✓ URL updated. Continuing to next job - worker will pick this up again with new URL."
                            )
                            continue

                # --- STEP 3: SCRAPE THE URL ---
                # Only reach here if URL doesn't need resolution or is already resolved
                logger.info(f"🕷️ Scraping: {original_url}")
                data = await asyncio.to_thread(scraper.scrape, original_url)

                if data:
                    # Use the resolved URL for database storage
                    final_url = data.get("resolved_url", original_url)

                    await finish_scrape(
                        job["id"],
                        data.get("company", "Unknown"),
                        data.get("job_title", "Unknown"),
                        data.get("full_description", ""),
                    )
                    logger.info(f"✅ Scrape complete for: {final_url}")
                else:
                    await mark_failed(
                        job["id"], "NO_DATA", "Scraper returned empty data"
                    )
            except Exception as e:
                logger.error(f"❌ Scrape error for {job['url']}: {e}")
                await mark_failed(job["id"], "FAILED_SCRAPE", str(e))
        else:
            await asyncio.sleep(2)


async def ai_worker():
    logger.info("🤖 AI Worker started")
    analyzer = JobAnalyzer()

    while True:
        job = await fetch_next_job("WAITING_FOR_AI", "ANALYZING")
        if job:
            try:
                logger.info(f"🤖 Analyzing Job ID: {job['id']}")
                resume = read_text_file(RESUME_PATH)
                context = read_text_file(CONTEXT_PATH)

                # הרצת הניתוח
                result = await asyncio.to_thread(analyzer.analyze, resume, context, job)
                await finish_analysis(job["id"], result)
                logger.info(f"✅ Analysis complete for Job ID: {job['id']}")
            except Exception as e:
                logger.error(f"❌ AI error for Job ID {job['id']}: {e}")
                await mark_failed(job["id"], "FAILED_ANALYSIS", str(e))
        else:
            await asyncio.sleep(2)


async def start_background_workers():
    """פונקציה שתופעל כשהשרת עולה"""
    logger.info("🧹 Cleaning up stuck jobs from previous run...")
    await reset_stuck_jobs()
    asyncio.create_task(scrape_worker())
    asyncio.create_task(ai_worker())
