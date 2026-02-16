import asyncio
import logging
from datetime import datetime
from typing import Optional

# ניסיון ייבוא גמיש התומך בהרצה כמודול או כסקריפט ישיר
try:
    from scraper import Scraper

    from db.json_db import update_job_in_db
    from engine import JobAnalyzer
    from services.file_utils import CONTEXT_PATH, RESUME_PATH, read_text_file
except ImportError:
    from src.scraper import Scraper

    from src.db.json_db import update_job_in_db
    from src.engine import JobAnalyzer
    from src.services.file_utils import CONTEXT_PATH, RESUME_PATH, read_text_file

logger = logging.getLogger("JobMatchServer")

# הגבלת ריצה מקבילית לאחד כדי למנוע עומס על ה-LLM או חסימות סקריפינג
CONCURRENCY_LIMIT = asyncio.Semaphore(1)


async def process_job(
    url: str, manual_text: Optional[str] = None, manual_meta: Optional[dict] = None
):
    """
    מנהל את מחזור החיים המלא של עיבוד משרה:
    1. קליטת המשרה (Intake) ורישום ראשוני ב-DB.
    2. חילוץ תוכן (Scraping) - או שימוש בטקסט ידני אם סופק.
    3. ניתוח AI (Analysis) - השוואת קורות החיים לתיאור המשרה.
    4. עדכון סטטוסים לאורך כל הדרך (pending -> scraping -> analyzing -> completed).
    """
    async with CONCURRENCY_LIMIT:
        # --- שלב 0: וולידציה ---
        resume = read_text_file(RESUME_PATH)
        if not resume:
            logger.error(f"❌ תהליך הופסק: קובץ קורות החיים חסר בנתיב: {RESUME_PATH}")
            return

        # הכנת אובייקט המשרה הראשוני
        job_record = {
            "url": url,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "company": (manual_meta or {}).get("company", "Pending..."),
            "job_title": (manual_meta or {}).get("title", "Pending..."),
        }

        await update_job_in_db(job_record)

        try:
            # --- שלב 1: חילוץ נתונים (Scraping) ---
            if manual_text:
                logger.info(f"📝 משתמש בטקסט ידני עבור: {url}")
                job_record["full_description"] = manual_text
            else:
                logger.info(f"🌐 מתחיל סריקה עבור: {url}")
                await update_job_in_db({"url": url, "status": "scraping"})

                scraper = Scraper()
                # הרצה ב-thread נפרד כי הסקריפר עשוי להיות סינכרוני (Playwright/Requests)
                scraped_data = await asyncio.to_thread(scraper.scrape, url)

                if not scraped_data:
                    raise Exception("הסורק לא הצליח לחלץ תוכן מהכתובת שופקה")

                job_record.update(scraped_data)

            job_record["status"] = "scraped"
            await update_job_in_db(job_record)

            # --- שלב 2: ניתוח בינה מלאכותית (AI Analysis) ---
            logger.info(f"🧠 מתחיל ניתוח AI עבור: {url}")
            await update_job_in_db({"url": url, "status": "analyzing"})

            context = read_text_file(CONTEXT_PATH)
            analyzer = JobAnalyzer()

            # שליחה ל-LLM - פעולה חוסמת ולכן מורצת ב-thread נפרד
            analysis_result = await asyncio.to_thread(
                analyzer.analyze, resume, context, job_record
            )

            # --- שלב 3: סיום ושמירה ---
            final_data = {
                "url": url,
                **analysis_result,
                "analyzed_at": datetime.now().isoformat(),
                "status": "completed",
            }
            await update_job_in_db(final_data)
            logger.info(f"✅ עיבוד משרה הושלם בהצלחה: {url}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ שגיאה בעיבוד {url}: {error_msg}")
            await update_job_in_db(
                {"url": url, "status": "failed", "error_log": error_msg}
            )
