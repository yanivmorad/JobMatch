"""
באג (סעיף 3): הדשבורד ייבא את lucide-react ו-axios בלי שהן מופיעות ב-package.json.
הבנייה עברה רק במחשב שבו החבילות היו מותקנות בתיקיית אב (C:/Users/<user>/node_modules),
ונכשלה ב-`npm ci && npm run build` על מכונה נקייה (Docker / Render).
"""
import json
import re
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard"

# import x from 'pkg' / import 'pkg' / import('pkg') / export ... from 'pkg'
_IMPORT_RE = re.compile(
    r"""(?:\bimport\s+(?:[\w*{}\s,$]+\s+from\s+)?|\bexport\s+[\w*{}\s,$]+\s+from\s+|\bimport\s*\()\s*['"]([^'"]+)['"]"""
)


def _package_name(spec: str) -> str:
    """'@scope/pkg/sub' -> '@scope/pkg', 'pkg/sub' -> 'pkg'"""
    parts = spec.split("/")
    return "/".join(parts[:2]) if spec.startswith("@") else parts[0]


def _imported_packages() -> dict:
    found = {}
    for path in (DASHBOARD / "src").rglob("*"):
        if path.suffix not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        for spec in _IMPORT_RE.findall(path.read_text(encoding="utf-8")):
            if spec.startswith((".", "/")):
                continue  # ייבוא מקומי
            found.setdefault(_package_name(spec), path.relative_to(DASHBOARD).as_posix())
    return found


def test_import_regex_sanity():
    sample = """
    import React, { useState } from 'react';
    import { Send } from "lucide-react";
    import './App.css';
    export { default } from '@scope/pkg/sub';
    const m = await import('lazy-pkg');
    """
    assert {_package_name(s) for s in _IMPORT_RE.findall(sample) if not s.startswith(".")} == {
        "react",
        "lucide-react",
        "@scope/pkg",
        "lazy-pkg",
    }


def test_every_imported_package_is_declared():
    pkg = json.loads((DASHBOARD / "package.json").read_text(encoding="utf-8"))
    declared = set(pkg.get("dependencies", {})) | set(pkg.get("devDependencies", {}))

    imported = _imported_packages()
    assert {"react", "axios", "lucide-react"} <= set(imported)  # הסורק עצמו עובד

    missing = {name: where for name, where in imported.items() if name not in declared}
    assert not missing, f"imported but not in dashboard/package.json: {missing}"


def test_runtime_imports_are_not_dev_only():
    """חבילה שהקוד מייבא בזמן ריצה צריכה להיות ב-dependencies, לא רק ב-devDependencies."""
    pkg = json.loads((DASHBOARD / "package.json").read_text(encoding="utf-8"))
    runtime = set(pkg.get("dependencies", {}))
    for name in ("axios", "lucide-react", "react", "react-dom"):
        assert name in runtime, f"{name} must be in dependencies"
