"""
סעיף 15: הדשבורד עבר `npm run lint` עם 7 שגיאות (משתנים שלא בשימוש, setState סינכרוני
בתוך useEffect). הבדיקה מריצה את ESLint ונכשלת על כל שגיאה.
מדולגת אם אין Node או שלא הותקנו התלויות (cd dashboard && npm ci).
"""
import shutil
import subprocess
from pathlib import Path

import pytest

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard"


@pytest.mark.skipif(shutil.which("npx") is None, reason="Node.js / npx not installed")
@pytest.mark.skipif(
    not (DASHBOARD / "node_modules" / "eslint").exists(),
    reason="dashboard deps not installed (cd dashboard && npm ci)",
)
def test_dashboard_eslint_has_no_errors():
    proc = subprocess.run(
        "npx eslint . --max-warnings=0",
        cwd=DASHBOARD,
        shell=True,  # npx הוא npx.cmd ב-Windows
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
