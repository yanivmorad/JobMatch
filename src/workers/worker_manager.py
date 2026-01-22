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
                logger.info(f"🕷️ Scraping: {job['url']}")
                data = await asyncio.to_thread(scraper.scrape, job["url"])

                if data:
                    await finish_scrape(
                        job["id"],
                        data.get("company", "Unknown"),
                        data.get("job_title", "Unknown"),
                        data.get("full_description", ""),
                    )
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
