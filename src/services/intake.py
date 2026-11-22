"""
קליטת משרות למערכת - נקודת כניסה אחת לכל ערוץ (דשבורד, תוסף, ובהמשך בוט טלגרם / וואטסאפ).

    ingest_text(text)  - טקסט גולמי: מחלץ את קישורי המשרות ומכניס אותם לתור
    ingest_urls(urls)  - רשימת קישורים מוכנה

כל קישור מנורמל (בלי utm וכו') ונבדק מול משרות קיימות - גם מול הקישור המקורי שנשלח
(source_url), כך שמשרת HireMeTech שכבר פוענחה לאתר החברה מזוהה ככפולה.
הוורקרים ממשיכים משם (resolve -> scrape -> AI).
"""
from typing import Iterable

from db.jobs_repository import add_new_job, find_existing_job
from services.link_extractor import extract_job_links, normalize_job_url
from workers.queue_signal import notify


def _scan_date(job: dict) -> str:
    when = job.get("analyzed_at") or job.get("created_at")
    return when.strftime("%d/%m/%Y") if when else "לא ידוע"


def duplicate_info(url: str, existing: dict) -> dict:
    return {
        "id": existing.get("id"),
        "url": url,
        "date": _scan_date(existing),
        "company": existing.get("company") or "Unknown",
        "status": existing.get("status"),
    }


async def ingest_urls(urls: Iterable[str], source: str = "web") -> dict:
    """
    added_jobs: [{id, url}] - ערוץ כמו בוט שומר את ה-id-ים ושואל GET /api/jobs/{id} עד שיש ציון.
    skipped_urls כוללים את ה-id של המשרה הקיימת (אפשר להחזיר מיד את הציון שכבר קיים).
    """
    added_jobs, skipped_urls, seen = [], [], set()
    for raw in urls:
        url = normalize_job_url(raw)
        if not url.startswith(("http://", "https://")) or url in seen:
            continue
        seen.add(url)

        existing = await find_existing_job(url)
        job_id = await add_new_job(url, source=source) if existing is None else None
        if job_id:
            added_jobs.append({"id": job_id, "url": url})
            continue
        # קיים כבר (או נוסף במקביל ממקור אחר בין הבדיקה להכנסה)
        existing = existing or await find_existing_job(url)
        skipped_urls.append(duplicate_info(url, existing or {}))

    if added_jobs:
        notify("PENDING_RESOLVE")  # ה-resolver מתעורר מיד, בלי לחכות לבדיקה התקופתית
    return {
        "message": f"Processed {len(added_jobs) + len(skipped_urls)} jobs",
        "added": len(added_jobs),
        "added_urls": [j["url"] for j in added_jobs],
        "added_jobs": added_jobs,
        "skipped": len(skipped_urls),
        "skipped_urls": skipped_urls,
    }


async def ingest_text(text: str, source: str = "web") -> dict:
    links = extract_job_links(text)
    result = await ingest_urls(links.jobs, source=source)
    result["ignored"] = links.ignored
    return result
