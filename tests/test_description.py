"""ניקוי וחיתוך חכם של תיאור המשרה לפני שליחה ל-AI."""
from services.description import condense_description

_JOB_BODY = (
    "## About the role\nWe are looking for a Data Analyst.\n\n"
    "## Requirements\n- 2+ years of experience with SQL\n- Strong skills in Python\n\n"
    "## Responsibilities\n- You will build dashboards\n\n## Benefits\n- Hybrid"
)


def test_short_text_is_only_cleaned():
    text = "Title: Data Analyst\n\nURL Source: https://x\n\nMarkdown Content:\n[Apply](https://x/apply)\n\n" + _JOB_BODY
    out = condense_description(text, 8000)
    assert out.startswith("Data Analyst\n")
    assert "URL Source" not in out and "https://" not in out
    assert "Apply" in out and "2+ years of experience with SQL" in out


def test_images_links_and_repeated_menu_lines_are_removed():
    text = "![logo](https://x/logo.png)\nHome\nJobs\nHome\nJobs\n\n" + _JOB_BODY + "\nHome\nJobs"
    out = condense_description(text, 8000)
    assert "logo" not in out
    assert out.count("Home") == 1 and out.count("Jobs") == 1


def test_cookie_banner_lines_are_removed():
    text = (
        "We use cookies to improve your experience\n_clck\nmzb\\_utm\\_term\n__ft_referrer\n"
        "Microsoft Clarity sets this cookie to store sessions.\n\n" + _JOB_BODY
    )
    out = condense_description(text, 8000)
    assert "cookie" not in out.lower()
    assert "_clck" not in out and "mzb" not in out and "__ft" not in out
    assert "Requirements" in out


def test_long_text_keeps_the_job_section_not_the_navigation():
    nav = "\n".join(f"Similar job number {i} at company {i}" for i in range(600))  # ~22K תווים בלי סימני משרה
    footer = "\n".join(f"Footer link {i}" for i in range(300))
    out = condense_description(nav + "\n\n" + _JOB_BODY + "\n\n" + footer, 3000)
    assert len(out) <= 3000 + 40
    assert "2+ years of experience with SQL" in out and "You will build dashboards" in out
    assert out.endswith("[...התיאור קוצר...]")


def test_single_huge_line_is_cut_not_dropped():
    out = condense_description("Requirements: experience " + "x" * 20000, 2000)
    assert out.startswith("Requirements: experience") and len(out) < 2100


def test_empty():
    assert condense_description("", 100) == ""
