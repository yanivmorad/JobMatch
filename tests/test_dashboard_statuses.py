"""
באג (סעיף 7): משרות בסטטוס FAILED_RESOLVE נעלמו מהממשק - הסטטוס לא הופיע באף אחת
מרשימות הסינון שהיו מועתקות בכמה קומפוננטות (JobDashboard, AddJobsTab, OverviewTab...).

עכשיו יש מקור אחד: dashboard/src/constants/jobStatus.js. הבדיקות כאן:
1. כל סטטוס ב-JOB_STATUSES של השרת נמצא בדיוק בקבוצה אחת בדשבורד (ולהפך).
2. אף קומפוננטה לא מחזיקה שוב רשימת סטטוסים משלה.
"""
import re
from pathlib import Path

from db.postgres import JOB_STATUSES

DASHBOARD_SRC = Path(__file__).resolve().parent.parent / "dashboard" / "src"
STATUS_FILE = DASHBOARD_SRC / "constants" / "jobStatus.js"

_GROUP_RE = re.compile(r"export const (\w+_STATUSES)\s*=\s*\[([^\]]*)\]")
_STR_RE = re.compile(r"['\"]([A-Z_]+)['\"]")


def _groups() -> dict:
    text = STATUS_FILE.read_text(encoding="utf-8")
    return {name: _STR_RE.findall(body) for name, body in _GROUP_RE.findall(text)}


def test_every_server_status_is_in_exactly_one_dashboard_group():
    groups = _groups()
    partition = {k: groups[k] for k in ("PROCESSING_STATUSES", "FAILED_STATUSES", "DONE_STATUSES")}

    for status in JOB_STATUSES:
        owners = [name for name, values in partition.items() if status in values]
        assert len(owners) == 1, f"{status} is in {owners or 'no group'} in jobStatus.js"

    dashboard_only = {s for values in partition.values() for s in values} - set(JOB_STATUSES)
    assert not dashboard_only, f"statuses unknown to the server: {dashboard_only}"


def test_failed_resolve_is_visible_as_failed():
    groups = _groups()
    assert "FAILED_RESOLVE" in groups["FAILED_STATUSES"]
    assert "FAILED_RESOLVE" in groups["NEEDS_MANUAL_CONTENT_STATUSES"]


def test_every_failed_status_has_a_label():
    text = STATUS_FILE.read_text(encoding="utf-8")
    labels = re.search(r"FAILED_STATUS_LABELS\s*=\s*\{([^}]*)\}", text).group(1)
    labeled = set(re.findall(r"(\w+)\s*:", labels))
    assert set(_groups()["FAILED_STATUSES"]) <= labeled


def test_no_component_keeps_its_own_status_list():
    """מערך literal עם 2+ סטטוסים של הצינור מחוץ ל-jobStatus.js = רשימה שתתפצל שוב."""
    statuses = "|".join(JOB_STATUSES)
    array_re = re.compile(rf"\[\s*['\"]({statuses})['\"]\s*,\s*['\"]({statuses})['\"]")
    offenders = []
    for path in DASHBOARD_SRC.rglob("*.js*"):
        if path == STATUS_FILE:
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if array_re.search(line):
                offenders.append(f"{path.relative_to(DASHBOARD_SRC).as_posix()}:{i}")
    assert not offenders, f"use constants/jobStatus.js instead: {offenders}"
