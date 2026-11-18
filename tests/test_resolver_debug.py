import os

from scraper_service import resolvers


class _FakePage:
    def __init__(self):
        self.paths = []

    def screenshot(self, path):
        self.paths.append(path)
        with open(path, "wb") as f:
            f.write(b"png")


def test_no_screenshot_by_default(monkeypatch, tmp_path):
    """באג: צילום מסך נכתב תמיד לתיקיית העבודה (שורש הפרויקט)."""
    monkeypatch.delenv("DEBUG_SCREENSHOTS", raising=False)
    monkeypatch.setattr(resolvers, "DEBUG_DIR", str(tmp_path / "debug"))
    page = _FakePage()

    resolvers._debug_screenshot(page, "x.png")

    assert page.paths == []


def test_screenshot_goes_to_debug_dir_when_enabled(monkeypatch, tmp_path):
    debug_dir = tmp_path / "logs" / "debug"
    monkeypatch.setenv("DEBUG_SCREENSHOTS", "true")
    monkeypatch.setattr(resolvers, "DEBUG_DIR", str(debug_dir))
    page = _FakePage()

    resolvers._debug_screenshot(page, "missing_button_7.png")

    assert page.paths == [str(debug_dir / "missing_button_7.png")]
    assert (debug_dir / "missing_button_7.png").exists()


def test_default_debug_dir_is_under_logs():
    assert resolvers.DEBUG_DIR.replace(os.sep, "/").endswith("logs/debug")


def test_screenshot_failure_does_not_raise(monkeypatch, tmp_path):
    class _Broken:
        def screenshot(self, path):
            raise RuntimeError("page closed")

    monkeypatch.setenv("DEBUG_SCREENSHOTS", "1")
    monkeypatch.setattr(resolvers, "DEBUG_DIR", str(tmp_path))
    resolvers._debug_screenshot(_Broken(), "x.png")  # לא אמור לזרוק
