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


def test_whole_job_on_one_line_survives_a_cookie_sentence():
    """באג (E2E): HireMeTech מחזיר את כל המשרה בשורה אחת שמסתיימת בהודעת Cookie -
    השורה נמחקה, ו-Gemini קיבל רק כותרת וכישורים (ציון בלי תיאור)."""
    one_line = (
        "בוגר/ת מערכות מידע או מדעי המחשב ומעוניין/ת במשרת פיתוח ראשונה? לחברת Medatech המובילה "
        "בתחום ERP Priority דרוש.ה מפתח.ת. דרישות: תואר ראשון, ניסיון של עד שנתיים, ידע ב-SQL. "
        + "התפקיד כולל פיתוח מודלים ודוחות ועבודה מול לקוחות. " * 8
        + "אתר זה משתמש בטכנולוגיות לאיסוף מידע, כגון קובצי Cookie, לצורכי סטטיסטיקה ופרסום. הבנתי"
    )
    out = condense_description(f"Title: מפתח/ת Priority\n\n{one_line}")
    assert "Medatech" in out and "דרישות: תואר ראשון" in out
    assert "Cookie" not in out


def test_long_cookiebot_paragraph_without_job_content_is_still_dropped():
    banner = (
        "We use cookies to personalise content and ads, to provide social media features and to analyse "
        "our traffic. We also share information about your use of our site with our social media, "
        "advertising and analytics partners who may combine it with other information that you have "
        "provided to them or that they have collected from your use of their services."
    )
    job = "Requirements: 2+ years of experience with SQL. Responsibilities: build dashboards."
    out = condense_description(f"Title: Analyst\n\n{banner}\n\n{job}")
    assert "social media" not in out and "Requirements: 2+ years" in out


def test_short_job_line_mentioning_cookies_is_kept():
    line = "Requirements: experience building cookie-less ad tracking, 3+ years of Python."
    assert line in condense_description(f"Title: Engineer\n\n{line}")
