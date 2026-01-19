# src/services/job_service.py
import asyncio
import logging
from datetime import datetime
from typing import Optional

from db.json_db import update_job_in_db
from services.file_utils import CONTEXT_PATH, RESUME_PATH, read_text_file

# יבוא המנועים
try:
    from engine import JobAnalyzer
    from scraper import Scraper
except ImportError:
    from src.engine import JobAnalyzer
    from src.scraper import Scraper

logger = logging.getLogger("JobMatchServer")

CONCURRENCY_LIMIT = asyncio.Semaphore(1)


async def process_job(
    url: str, manual_text: Optional[str] = None, manual_meta: Optional[dict] = None
):
    async with CONCURRENCY_LIMIT:
        # בדיקה ראשונית של קבצים הכרחיים לפני שמתחילים
        resume = read_text_file(RESUME_PATH)
        if not resume:
            logger.error("❌ Cannot process job: Resume file is missing or empty.")
            return

        job_record = {
            "url": url,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "company": manual_meta.get("company", "Pending...")
            if manual_meta
            else "Pending...",
            "job_title": manual_meta.get("title", "Pending...")
            if manual_meta
            else "Pending...",
        }

        await update_job_in_db(job_record)

        try:
            # --- שלב הסריקה ---
            if manual_text:
                job_record["full_description"] = manual_text
                job_record["status"] = "scraped"
            else:
                await update_job_in_db({"url": url, "status": "scraping"})
                scraper = Scraper()
                scraped_data = await asyncio.to_thread(scraper.scrape, url)

                if not scraped_data:
                    raise Exception("Scraper returned no data")

                job_record.update(scraped_data)
                job_record["status"] = "scraped"

            await update_job_in_db(job_record)

            # --- שלב הניתוח ---
            await update_job_in_db({"url": url, "status": "analyzing"})

            context = read_text_file(CONTEXT_PATH)
            analyzer = JobAnalyzer()

            # הרצת ה-AI (לוקח זמן)
            analysis_result = await asyncio.to_thread(
                analyzer.analyze, resume, context, job_record
            )

            # עדכון סופי
            final_data = {
                "url": url,
                **analysis_result,
                "analyzed_at": datetime.now().isoformat(),
                "status": "completed",
            }
            await update_job_in_db(final_data)

        except Exception as e:
            logger.error(f"❌ Error processing {url}: {e}")
            await update_job_in_db(
                {"url": url, "status": "failed", "error_log": str(e)}
            )
