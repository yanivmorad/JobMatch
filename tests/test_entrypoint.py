"""
סעיף 5: נקודת ההרצה של השרת.
run_server.bat וה-Dockerfile מריצים את המודול src.server:app מתיקיית השורש, בעוד ש-server.py
מייבא את המודולים הפנימיים כ-top-level (db.*, routes.*). הבדיקות מוודאות ששתי נקודות ההרצה
זהות, ושהייבוא בצורה הזו באמת עובד (בתהליך נפרד, בלי ה-pythonpath של pytest).
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_server_imports_as_src_server_from_project_root():
    code = (
        "import src.server as s; "
        "paths = {getattr(r, 'path', '') for r in s.app.routes}; "
        "assert {'/api/results', '/api/profile/resume'} <= paths, paths; "
        "print('ok')"
    )
    # -I: בלי PYTHONPATH / site של המשתמש - בדיוק כמו uvicorn שמופעל מהשורש
    proc = subprocess.run(
        [sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, '.'); {code}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().endswith("ok")


def _app_target(text: str) -> str:
    m = re.search(r"uvicorn\s+([\w.]+:\w+)", text)
    assert m, "no 'uvicorn <module>:<app>' found"
    return m.group(1)


def test_bat_and_dockerfile_use_the_same_entry_point():
    bat = (ROOT / "run_server.bat").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert _app_target(bat) == _app_target(dockerfile) == "src.server:app"


def test_bat_runs_from_project_root_with_the_venv():
    bat = (ROOT / "run_server.bat").read_text(encoding="utf-8")
    assert 'cd /d "%~dp0"' in bat  # אחרת .env / data\ לא נמצאים כשמפעילים מתיקייה אחרת
    assert r".venv\Scripts\python.exe" in bat
    assert "-m uvicorn" in bat  # ולא uvicorn גלובלי מה-PATH
