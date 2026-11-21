"""
בדיקת הסורק על רשימת קישורים: resolve + scrape, בלי AI ובלי DB.

    python scripts/test_scraper.py data/links.txt
    python scripts/test_scraper.py --url https://... --url https://...

בתוך Docker (אותה סביבה כמו בייצור):
    docker compose run --rm --no-deps -v ./scripts:/app/scripts app \
        python scripts/test_scraper.py data/links.txt

קובץ הקישורים: קישור אחד בכל שורה. שורות ריקות ושורות שמתחילות ב-# מדולגות.
הדוח נשמר ל-logs/scraper_report_<timestamp>.md + .json
"""
import argparse
import json
import logging
import os
import re
import sys
import time
from collections import OrderedDict
from datetime import datetime
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from scraper_service.resolvers import ResolveError, URLResolver  # noqa: E402
from scraper_service.scraper import Scraper  # noqa: E402
from scraper_service.utils import failure_message  # noqa: E402

SITES = [
    ("LinkedIn", ("linkedin.com",)),
    ("HireMeTech", ("hiremetech.com",)),
    ("Comeet", ("comeet.com", "comeet.co")),
    ("Greenhouse", ("greenhouse.io",)),
    ("Lever", ("lever.co",)),
    ("AllJobs", ("alljobs.co.il",)),
    ("Drushim", ("drushim.co.il",)),
    ("Workday", ("myworkdayjobs.com", "workday.com")),
    ("SmartRecruiters", ("smartrecruiters.com",)),
    ("JobMaster", ("jobmaster.co.il",)),
    ("Indeed", ("indeed.com",)),
    ("Glassdoor", ("glassdoor.com", "glassdoor.co.il")),
    ("Ashby", ("ashbyhq.com",)),
    ("BambooHR", ("bamboohr.com",)),
]

_JINA_HEADER = re.compile(r"^(Title|URL Source|Final URL|Published Time|Markdown Content|Warning):.*$", re.MULTILINE)


def site_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for name, domains in SITES:
        if any(host == d or host.endswith("." + d) for d in domains):
            return name
    return f"Career page ({host.removeprefix('www.')})" if host else "Invalid URL"


def read_links(path: str) -> list:
    links = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split(" #", 1)[0].strip()
            if line and not line.startswith("#"):
                links.append(line)
    return links


def run_one(url: str, resolver: URLResolver, scraper: Scraper, skip_resolve: bool) -> dict:
    row = {
        "site": site_of(url),
        "url": url,
        "resolved_url": None,
        "resolved_site": None,
        "ok": False,
        "method": None,
        "length": 0,
        "seconds": 0.0,
        "resolve_seconds": 0.0,
        "error": None,
        "attempts": [],
        "preview": "",
    }
    t0 = time.time()

    target = url
    if not skip_resolve:
        try:
            target = resolver.resolve(url)
        except ResolveError as e:
            if e.public_fallback:
                # כמו ה-worker: HireMeTech -> סריקת הדף הציבורי (בלי שם החברה)
                row["resolve_note"] = f"{e} -> public page"
            else:
                row["error"] = f"resolve: {e}"
        except Exception as e:  # כמו ה-worker: כל שגיאה = FAILED_RESOLVE
            row["error"] = f"resolve: {type(e).__name__}: {e}"
        row["resolve_seconds"] = round(time.time() - t0, 1)
        if target != url:
            row["resolved_url"] = target
            row["resolved_site"] = site_of(target)

    if row["error"] is None:
        trace = []
        try:
            result = scraper.scrape(target, trace=trace)
        except Exception as e:
            result = None
            row["error"] = f"scrape crashed: {type(e).__name__}: {e}"
        row["attempts"] = trace
        if result:
            text = result["full_description"]
            winner = next((a["method"] for a in reversed(trace) if a.get("valid")), result.get("source"))
            row.update(
                ok=True,
                method=winner,  # jina / jina_full_page / playwright
                length=len(text),
                preview=" ".join(_JINA_HEADER.sub("", text).split())[:200],
                text=text,  # הטקסט המלא - נשמר רק ב-JSON (לבדיקת איכות ולשלב הניתוח)
            )
        elif row["error"] is None:
            row["error"] = failure_message([a.get("reason") for a in trace])

    row["seconds"] = round(time.time() - t0, 1)
    return row


def fmt_attempts(attempts: list) -> str:
    parts = []
    for a in attempts:
        status = f" {a['status']}" if a.get("status") else ""
        parts.append(f"{a['method']}{status} {a.get('reason')} ({a.get('seconds', '?')}s, {a.get('length', 0)} chars)")
    return " -> ".join(parts) or "-"


def print_row(i: int, total: int, row: dict):
    mark = "OK  " if row["ok"] else "FAIL"
    head = f"[{i}/{total}] {mark} {row['site']}"
    if row["ok"]:
        head += f" | {row['method']} | {row['length']:,} chars"
    head += f" | {row['seconds']}s"
    print(head)
    print(f"    url:      {row['url']}")
    if row["resolved_url"]:
        print(f"    resolved: {row['resolved_url']} ({row['resolved_site']}, {row['resolve_seconds']}s)")
    if row.get("resolve_note"):
        print(f"    resolve:  {row['resolve_note']}")
    print(f"    attempts: {fmt_attempts(row['attempts'])}")
    if row["ok"]:
        print(f"    preview:  {row['preview']}")
    else:
        print(f"    error:    {row['error']}")
    print()


def summarize(rows: list) -> list:
    by_site = OrderedDict()
    for r in rows:
        s = by_site.setdefault(
            r["site"], {"site": r["site"], "links": 0, "ok": 0, "jina": 0, "playwright": 0, "failed": 0, "seconds": [], "errors": []}
        )
        s["links"] += 1
        s["seconds"].append(r["seconds"])
        if r["ok"]:
            s["ok"] += 1
            s["playwright" if r["method"] == "playwright" else "jina"] += 1
        else:
            s["failed"] += 1
            s["errors"].append(r["error"])
    out = []
    for s in by_site.values():
        out.append(
            {
                "site": s["site"],
                "links": s["links"],
                "ok": s["ok"],
                "jina": s["jina"],
                "playwright": s["playwright"],
                "failed": s["failed"],
                "success_rate": f"{100 * s['ok'] // s['links']}%",
                "avg_seconds": round(sum(s["seconds"]) / len(s["seconds"]), 1),
                "errors": sorted(set(s["errors"])),
            }
        )
    return out


def table(rows: list, cols: list) -> str:
    widths = [max(len(c), *(len(str(r[c])) for r in rows)) for c in cols]
    line = lambda vals: "| " + " | ".join(str(v).ljust(w) for v, w in zip(vals, widths)) + " |"
    return "\n".join([line(cols), "|" + "|".join("-" * (w + 2) for w in widths) + "|"] + [line([r[c] for c in cols]) for r in rows])


def main():
    parser = argparse.ArgumentParser(description="Resolve + scrape a list of job links (no AI, no DB).")
    parser.add_argument("links_file", nargs="?", help="file with one URL per line")
    parser.add_argument("--url", action="append", default=[], help="a URL to test (repeatable)")
    parser.add_argument("--skip-resolve", action="store_true", help="scrape the URLs as-is")
    parser.add_argument("--out-dir", default=os.path.join(ROOT, "logs"))
    parser.add_argument("-v", "--verbose", action="store_true", help="show scraper/resolver logs")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="    %(levelname)s %(name)s: %(message)s")

    links = (read_links(args.links_file) if args.links_file else []) + args.url
    if not links:
        parser.error("no links: pass a links file and/or --url")

    resolver, scraper = URLResolver(), Scraper()
    print(f"Testing {len(links)} links (Jina key: {'yes' if scraper.api_key else 'NO'}, "
          f"HireMeTech token: {'yes' if resolver.hireme_token else 'NO'})\n")

    rows = []
    for i, url in enumerate(links, 1):
        row = run_one(url, resolver, scraper, args.skip_resolve)
        rows.append(row)
        print_row(i, len(links), row)

    summary = summarize(rows)
    ok = sum(r["ok"] for r in rows)
    summary_cols = ["site", "links", "ok", "jina", "playwright", "failed", "success_rate", "avg_seconds"]
    print(f"=== Summary: {ok}/{len(rows)} succeeded ===\n")
    print(table(summary, summary_cols))
    failures = [s for s in summary if s["errors"]]
    if failures:
        print("\nFailure reasons:")
        for s in failures:
            for e in s["errors"]:
                print(f"  {s['site']}: {e}")

    os.makedirs(args.out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(args.out_dir, f"scraper_report_{stamp}")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": rows}, f, ensure_ascii=False, indent=2)
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(f"# Scraper report {stamp}\n\n{ok}/{len(rows)} succeeded\n\n")
        f.write(table(summary, summary_cols) + "\n\n## Per link\n\n")
        for r in rows:
            f.write(f"- **{r['site']}** {'OK' if r['ok'] else 'FAIL'} ({r['method'] or '-'}, {r['length']} chars, {r['seconds']}s): {r['url']}\n")
            if r["resolved_url"]:
                f.write(f"  - resolved: {r['resolved_url']}\n")
            if r.get("resolve_note"):
                f.write(f"  - resolve: {r['resolve_note']}\n")
            f.write(f"  - attempts: {fmt_attempts(r['attempts'])}\n")
            f.write(f"  - {'preview: ' + r['preview'] if r['ok'] else 'error: ' + str(r['error'])}\n")
    print(f"\nReport: {base}.md\n        {base}.json")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
