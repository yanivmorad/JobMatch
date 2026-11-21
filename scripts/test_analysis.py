"""
בדיקת איכות הניתוח (שלב 4): מריץ את ה-engine על משרות מוכרות, כל משרה כמה פעמים,
ובודק שהתשובה תקינה (כל השדות, כולל company / job_title) ושהציון עקבי.

    python scripts/test_analysis.py                       # 10 משרות מדוח הסורק האחרון, פעמיים כל אחת
    python scripts/test_analysis.py --limit 8 --runs 2
    python scripts/test_analysis.py --report logs/scraper_report_X.json --url https://... --url https://...
    python scripts/test_analysis.py --from-db             # משרות שכבר נותחו במערכת (DATABASE_URL / PG_*)

המשרות נלקחות מהדוח של scripts/test_scraper.py (הטקסט המלא נשמר שם), כך שאין סריקה מחדש.
הקצב נשמר לפי GEMINI_RPM (ברירת מחדל 10), ו-429 ממתין ומנסה שוב.
הדוח: logs/analysis_report_<timestamp>.md + .json
טבלה: משרה | חברה | ציון | המלצה | חוסמים, ועמודת פער בין הריצות.
"""
import argparse
import asyncio
import glob
import json
import os
import statistics
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))

from engine import JobAnalyzer, RateLimitError  # noqa: E402
from services.file_utils import CONTEXT_PATH, RESUME_PATH, read_text_file  # noqa: E402
from workers.rate_limiter import AIRateLimiter  # noqa: E402

# ציונים של אותה משרה שרחוקים יותר מזה = לא עקבי
CONSISTENCY_TOLERANCE = 10


def latest_report() -> str:
    reports = sorted(glob.glob(os.path.join(ROOT, "logs", "scraper_report_*.json")))
    if not reports:
        sys.exit("no logs/scraper_report_*.json - run scripts/test_scraper.py first")
    return reports[-1]


def jobs_from_report(path: str, urls: list, limit: int) -> list:
    with open(path, encoding="utf-8") as f:
        rows = [r for r in json.load(f)["results"] if r.get("ok") and r.get("text")]
    if urls:
        rows = [r for r in rows if r["url"] in urls or r.get("resolved_url") in urls]
    else:
        # פיזור: משרה אחת מכל אתר לפני שחוזרים לאותו אתר
        by_site, picked = {}, []
        for r in rows:
            by_site.setdefault(r["site"], []).append(r)
        while len(picked) < limit and any(by_site.values()):
            for site in list(by_site):
                if by_site[site] and len(picked) < limit:
                    picked.append(by_site[site].pop(0))
        rows = picked
    return [{"url": r.get("resolved_url") or r["url"], "site": r["site"], "full_description": r["text"]} for r in rows[:limit]]


async def jobs_from_db(limit: int) -> list:
    from db.postgres import get_pool

    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT url, full_description, company, job_title FROM jobs WHERE full_description IS NOT NULL "
        "AND status = 'COMPLETED' ORDER BY analyzed_at DESC LIMIT $1",
        limit,
    )
    return [{**dict(r), "site": "db"} for r in rows]


async def analyze_all(jobs: list, runs: int) -> list:
    analyzer = JobAnalyzer()
    limiter = AIRateLimiter(analyzer.model_name)
    resume, context = read_text_file(RESUME_PATH), read_text_file(CONTEXT_PATH)
    if not resume:
        sys.exit("resume is empty - data/resume.txt")

    results = []
    for i, job in enumerate(jobs, 1):
        entry = {"url": job["url"], "site": job["site"], "runs": [], "errors": []}
        for run in range(runs):
            while True:
                await limiter.wait_until_allowed()
                await limiter.record_request()
                t0 = time.time()
                try:
                    res = await asyncio.to_thread(analyzer.analyze, resume, context, job)
                    limiter.on_success()
                    res["seconds"] = round(time.time() - t0, 1)
                    entry["runs"].append(res)
                    break
                except RateLimitError as e:
                    until = limiter.on_rate_limited(e)
                    print(f"    429 ({e.quota_ids} = {e.quota_values}) - waiting until {until:%H:%M:%S} UTC")
                    if e.per_day:
                        entry["errors"].append("daily quota exhausted")
                        return results + [entry]
                except Exception as e:
                    entry["errors"].append(f"{type(e).__name__}: {e}")
                    break
        scores = [r["suitability_score"] for r in entry["runs"]]
        entry["spread"] = (max(scores) - min(scores)) if len(scores) > 1 else 0
        first = entry["runs"][0] if entry["runs"] else {}
        print(
            f"[{i}/{len(jobs)}] {first.get('job_title', '?')[:40]} @ {first.get('company', '?')[:25]} "
            f"| scores {scores} | {first.get('recommendation', '-')}"
            + (f" | ERR {entry['errors']}" if entry["errors"] else "")
        )
        results.append(entry)
    return results


def _cell(text) -> str:
    return str(text).replace("|", "/").replace("\n", " ").strip()


def write_report(results: list, runs: int, model: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(ROOT, "logs", f"analysis_report_{stamp}")
    os.makedirs(os.path.dirname(base), exist_ok=True)
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump({"model": model, "runs": runs, "results": results}, f, ensure_ascii=False, indent=2)

    ok = [r for r in results if r["runs"]]
    spreads = [r["spread"] for r in ok if len(r["runs"]) > 1]
    lines = [
        f"# Analysis report {stamp}",
        "",
        f"model: {model}, runs per job: {runs}, jobs: {len(results)}, valid answers: "
        f"{sum(len(r['runs']) for r in results)}/{len(results) * runs}",
    ]
    if spreads:
        lines.append(
            f"score spread between runs: max {max(spreads)}, mean {statistics.mean(spreads):.1f} "
            f"({sum(s > CONSISTENCY_TOLERANCE for s in spreads)} jobs above {CONSISTENCY_TOLERANCE})"
        )
    lines += ["", "| משרה | חברה | ציון | המלצה | חוסמים | פער |", "|---|---|---|---|---|---|"]
    for r in sorted(ok, key=lambda r: -r["runs"][0]["suitability_score"]):
        first = r["runs"][0]
        scores = "/".join(str(x["suitability_score"]) for x in r["runs"])
        blockers = "; ".join(first.get("showstoppers") or []) or "-"
        lines.append(
            f"| {_cell(first['job_title'])} | {_cell(first['company'])} | {scores} | "
            f"{first['recommendation']} | {_cell(blockers)} | {r['spread']} |"
        )
    failed = [r for r in results if r["errors"]]
    if failed:
        lines += ["", "## Errors", ""] + [f"- {r['url']}: {r['errors']}" for r in failed]
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return base


async def main():
    parser = argparse.ArgumentParser(description="Run the AI analysis on known jobs and check consistency.")
    parser.add_argument("--report", help="scraper report JSON (default: the latest)")
    parser.add_argument("--url", action="append", default=[], help="only these jobs (repeatable)")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--runs", type=int, default=2, help="analyses per job (consistency)")
    parser.add_argument("--from-db", action="store_true", help="use analyzed jobs from the database")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    jobs = await jobs_from_db(args.limit) if args.from_db else jobs_from_report(args.report or latest_report(), args.url, args.limit)
    if not jobs:
        sys.exit("no jobs to analyze")
    print(f"Analyzing {len(jobs)} jobs x {args.runs} runs\n")
    results = await analyze_all(jobs, args.runs)
    base = write_report(results, args.runs, JobAnalyzer().model_name)
    print(f"\nReport: {base}.md\n        {base}.json")


if __name__ == "__main__":
    asyncio.run(main())
