"""
באג (ריצה אמיתית, 22.11): בזמן שמונה קישורים עברו את הצינור, הדשבורד לא הראה איפה כל אחד עומד.
1. הרענון האוטומטי רץ רק אם ברשימה שנטענה כבר הייתה משרה בעיבוד - משרות שנוספו מחוץ לדשבורד
   (תוסף / API / טאב או טלפון אחר) לא הופיעו עד רענון ידני.
2. הניטור החי הציג רק 4 משרות בעיבוד, בלי שם (company היה ה-URL הזמני), ומשרה שסיימה נעלמה
   בלי לומר אם הצליחה או נכשלה.

הלוגיקה עברה ל-dashboard/src/utils/queueView.js ונבדקת ב-Node (tests/js/queue_view.test.mjs).
כאן: הרצת הבדיקות האלה, התאמה לשרת (placeholders, סטטוסים), ובדיקות מבניות על הקומפוננטות.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from db.postgres import JOB_STATUSES
from services import job_fields

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_SRC = ROOT / "dashboard" / "src"
JS_TESTS = Path(__file__).resolve().parent / "js" / "queue_view.test.mjs"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")


def _node_json(code: str):
    """מריץ ESM קטן ב-Node ומחזיר את ה-JSON שהוא הדפיס."""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@needs_node
def test_queue_view_logic_in_node():
    proc = subprocess.run(
        ["node", "--test", str(JS_TESTS)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert re.search(r"# fail 0", proc.stdout), proc.stdout
    passed = int(re.search(r"# pass (\d+)", proc.stdout).group(1))
    assert passed >= 20, proc.stdout


@needs_node
def test_placeholders_match_the_server():
    """שם בניטור: אותה הגדרה של 'עוד לא ידוע' כמו ב-src/services/job_fields.py."""
    js = _node_json(
        "import * as q from './dashboard/src/utils/queueView.js';"
        "console.log(JSON.stringify({values: q.PLACEHOLDER_VALUES, markers: q.MASKED_MARKERS}));"
    )
    assert js["values"] == list(job_fields.PLACEHOLDER_VALUES)
    assert js["markers"] == list(job_fields._MASKED_MARKERS)


@needs_node
def test_is_placeholder_agrees_with_the_server_on_samples():
    samples = [
        None, "", "  Unknown ", "Identifying...", "pending...", "לא צוין", "משרה ידנית", "N/A",
        "https://www.comeet.com/jobs/a/1", "http://x.com", "manual://abc", "Company | HireMe",
        "HireMeTech", "(שם החברה מוסתר בדף הציבורי של HireMeTech)",
        "Supercom", "Junior QA Automation Engineer", "Company Builder Ltd", "מפתח/ת Full Stack",
    ]
    js = _node_json(
        "import { isPlaceholder } from './dashboard/src/utils/queueView.js';"
        f"const s = {json.dumps(samples, ensure_ascii=False)};"
        "console.log(JSON.stringify(s.map(isPlaceholder)));"
    )
    assert js == [job_fields.is_placeholder(v) for v in samples]


@needs_node
def test_every_server_status_has_a_pipeline_stage():
    stages = _node_json(
        "import { STATUS_STAGE } from './dashboard/src/constants/jobStatus.js';"
        "console.log(JSON.stringify(STATUS_STAGE));"
    )
    assert set(stages) == set(JOB_STATUSES)
    assert set(stages.values()) <= {"resolve", "scrape", "ai", "done", "failed"}
    assert stages["COMPLETED"] == "done"
    assert all(stages[s] == "failed" for s in ("FAILED_RESOLVE", "FAILED_SCRAPE", "FAILED_ANALYSIS", "NO_DATA"))


# --- בדיקות מבניות: שהקומפוננטות באמת משתמשות בלוגיקה (הבאגים היו בחיווט, לא רק בחישוב) ---


def _read(rel: str) -> str:
    return (DASHBOARD_SRC / rel).read_text(encoding="utf-8")


def test_polling_is_not_gated_on_already_loaded_processing_jobs():
    src = _read("components/JobDashboard.jsx")
    # הבאג: `if (!jobs.some(j => isProcessing(j.status))) return;` בתחילת ה-effect של ה-polling
    assert not re.search(r"if\s*\(\s*!\s*jobs\.some\([^)]*isProcessing[^)]*\)\s*\)\s*\)?\s*return", src)
    assert "shouldRefetch(" in src and "pollDelay(" in src
    assert "visibilitychange" in src  # לא מושכים כשהטאב מוסתר, ובודקים מיד כשחוזרים


def test_overview_monitor_shows_the_whole_run():
    # אחרי העיצוב מחדש: הניטור החי נמצא במסך הקליטה (IntakeScreen), והסקירה וסרגל הצד מסכמים את כל הריצה
    src = _read("components/screens/IntakeScreen.jsx")
    assert ".slice(0, 4)" not in src  # קודם: רק 4 משרות בעיבוד
    assert re.search(r"runList\.map\(\(job\)\s*=>\s*<RunRow", src)  # כל קישור בריצה מקבל שורה
    assert "runSummary(runJobs)" in src
    overview = _read("components/screens/OverviewScreen.jsx")
    assert "runSummary(runJobs)" in overview and ".slice(0, 4)" not in overview
    dashboard = _read("components/JobDashboard.jsx")
    assert "currentRun(" in dashboard and "runJobs={runJobs}" in dashboard


def test_queue_item_uses_the_shared_display_name():
    src = _read("components/run/RunRow.jsx")
    assert "jobDisplayName(job)" in src
    assert 'job.company !== "Unknown"' not in src  # הלוגיקה הישנה שהציגה את ה-URL הזמני
