import json
import os
import time

from tabulate import tabulate

from engine import JobAnalyzer  # וודא שהקלאס בקובץ engine.py נקרא JobAnalyzer
from scraper import Scraper  # וודא שהקלאס בקובץ scraper.py נקרא Scraper

# הגדרת נתיבים
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESUME_PATH = os.path.join(DATA_DIR, "resume.txt")
CONTEXT_PATH = os.path.join(DATA_DIR, "Personal Context.txt")
JOBS_LIST_PATH = os.path.join(DATA_DIR, "jobs.txt")
RESULTS_PATH = os.path.join(BASE_DIR, "results.json")


def load_file(path):
    if not os.path.exists(path):
        print(f"⚠️ Warning: {path} not found.")
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_jobs_list(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def main():
    print("\n🚀 --- JobMatch System Starting ---")

    # טעינת נתונים
    resume = load_file(RESUME_PATH)
    context = load_file(CONTEXT_PATH)
    entries = load_jobs_list(JOBS_LIST_PATH)

    if not resume:
        print("❌ Error: Please fill in data/resume.txt")
        return

    if not entries:
        print(f"❌ Error: No entries found in {JOBS_LIST_PATH}.")
        return

    print(f"✅ Loaded resume and context. Found {len(entries)} jobs to process.")

    # אתחול רכיבים
    scraper = Scraper()
    analyzer = JobAnalyzer()
    results = []

    for entry in entries:
        job_data = None
        display_url = entry[:50] + "..." if len(entry) > 50 else entry

        # 1. שלב הסריקה (Scraping)
        if entry.startswith(("http://", "https://")):
            print(f"\n🌐 Scrapping: {display_url}")
            job_data = scraper.scrape(entry)
        else:
            print("\n📝 Manual Text Input detected...")
            job_data = {
                "url": "Manual Entry",
                "company": "Pending Analysis",
                "job_title": "Pending Analysis",
                "full_description": entry,
            }

        # 2. אימות נתונים
        if not job_data or not job_data.get("full_description"):
            print(f"⚠️ Skipping: Could not get content for {display_url}")
            continue

        # 3. ניתוח עם Gemini (כולל תיקון כותרות וסיכום בעברית)
        print("🤖 Analyzing & Cleaning Data with Gemini...")
        analysis = analyzer.analyze(resume, context, job_data)

        # מיזוג נתונים: ה-AI דורס את הנתונים הגולמיים מהסקרייפר במידה ומצא דיוק טוב יותר
        final_entry = {
            "url": job_data.get("url"),
            "scraped_at": job_data.get("scraped_at"),
            **analysis,  # מכיל company, job_title, job_summary_hebrew, suitability_score וכו'
        }

        results.append(final_entry)

        # 4. המתנה למניעת חסימות (Rate Limiting)
        print(
            f"📊 Done: {final_entry['job_title']} @ {final_entry['company']} (Score: {final_entry['suitability_score']})"
        )
        print("⏳ Waiting before next job...")
        time.sleep(4)

    # שמירת תוצאות
    if results:
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {RESULTS_PATH}")

        # הדפסת טבלה מסכמת
        table_data = []
        for r in results:
            table_data.append(
                [
                    str(r.get("company"))[:15],
                    str(r.get("job_title"))[:25],
                    f"{r.get('suitability_score')}/100",
                    f"{r.get('acceptance_probability')}%",
                    str(r.get("recommendation"))[:50] + "...",
                ]
            )

        print("\n" + "=" * 90)
        print("🎯 FINAL JOB MATCH SUMMARY")
        print("=" * 90)
        print(
            tabulate(
                table_data,
                headers=["Company", "Title", "Match", "Prob %", "Bottom Line"],
                tablefmt="fancy_grid",
            )
        )
    else:
        print("\n❌ No jobs were successfully analyzed.")


if __name__ == "__main__":
    main()
