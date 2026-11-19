import pytest

from scraper_service.utils import failure_message, is_content_valid, validate_content

# ---------------------------------------------------------------- valid pages

GREENHOUSE_JOB = """Title: Job Application for Backend Engineer at Acme
URL Source: https://boards.greenhouse.io/acme/jobs/4012345
Markdown Content:
# Backend Engineer
Tel Aviv, Israel

## About the role
We are looking for a Backend Engineer to join our platform team. You will design and
build scalable services in Python.

## Requirements
- 3+ years of experience with Python
- Experience with PostgreSQL and cloud infrastructure
- Strong communication skills

## Benefits
Hybrid work, learning budget.

This site is protected by reCAPTCHA and the Google Privacy Policy and Terms of Service apply.
We use cookies to improve your experience. Cookie settings.
"""

HEBREW_JOB = """Title: מפתח/ת Full Stack - דרושים
Markdown Content:
## תיאור המשרה
חברת הייטק מובילה בתל אביב מחפשת מפתח/ת Full Stack לצוות המוצר.
התפקיד כולל פיתוח צד שרת וצד לקוח, עבודה מול צוותי מוצר ועיצוב.

## דרישות
- ניסיון של שנתיים לפחות בפיתוח Python / Node.js
- ניסיון עם React
- היכרות עם מסדי נתונים - יתרון
היקף משרה: משרה מלאה. התחברות לאזור האישי | אנו משתמשים בעוגיות
"""

LINKEDIN_GUEST_JOB = """Title: Acme hiring Data Engineer in Tel Aviv-Yafo | LinkedIn
URL Source: https://www.linkedin.com/jobs/view/3912345678
Markdown Content:
Sign in Join now
## Data Engineer
Acme · Tel Aviv-Yafo · 2 weeks ago
### About the job
We're looking for a Data Engineer who will own our data pipelines.
Responsibilities: build ETL with Airflow and Spark; work with analysts.
Qualifications: 4+ years of experience, strong SQL skills.
Seniority level: Mid-Senior level. Employment type: Full-time.
Sign in to create job alert. LinkedIn uses cookies. Accept / Reject.
"""

SECURITY_JOB_WITH_ERROR_WORDS = """Title: Security Engineer
Markdown Content:
## About the role
You will investigate access denied events and 403 forbidden responses across our APIs,
and harden our page not found handling.
## Requirements
- 5 years of experience in application security
- Strong skills in threat modeling
## Responsibilities
Own incident response.
"""

JOB_WITH_404_IN_TITLE = """Title: Senior QA Engineer - Req 40412
Markdown Content:
We are looking for a Senior QA Engineer. Requirements: 4 years of experience in test
automation, strong skills in Python and Playwright. You will own our regression suite.
"""


@pytest.mark.parametrize(
    "text",
    [
        GREENHOUSE_JOB,
        HEBREW_JOB,
        LINKEDIN_GUEST_JOB,
        SECURITY_JOB_WITH_ERROR_WORDS,
        JOB_WITH_404_IN_TITLE,
    ],
    ids=["greenhouse_recaptcha_footer", "hebrew", "linkedin_guest", "security_terms", "req_404"],
)
def test_real_job_pages_are_valid(text):
    assert validate_content(text) == (True, "ok")


def test_greenhouse_recaptcha_footer_is_not_rejected():
    """באג: הבדיקה הישנה פסלה כל דף עם המילה captcha - כולל כל משרה ב-Greenhouse."""
    assert is_content_valid(GREENHOUSE_JOB)


# -------------------------------------------------------------- invalid pages

LINKEDIN_AUTHWALL = """Title: Sign Up | LinkedIn
URL Source: https://www.linkedin.com/authwall?trk=...
Markdown Content:
Make the most of your professional life
Email or phone, Password (6+ characters). By clicking Agree & Join, you agree to the
LinkedIn User Agreement, Privacy Policy, and Cookie Policy. Agree & Join.
Already on LinkedIn? Sign in. Looking to create a page for a business? Get help.
"""

GENERIC_LOGIN = """Title: Welcome back
Markdown Content:
Log in to your account to continue.
Email address
Password
Remember me on this device. Forgot password? Don't have an account yet? Create one in
less than a minute and get access to all of our tools and saved searches.
"""

COOKIE_WALL = """Title: Careers
Markdown Content:
We value your privacy. We use cookies and similar technologies to enhance your browsing
experience, serve personalized ads or content, and analyze our traffic. By clicking
"Accept All", you consent to our use of cookies. Customize. Reject All. Accept All.
Cookie Policy. Powered by a consent management platform.
"""

HEBREW_UNAVAILABLE = """Title: AllJobs - לוח דרושים
Markdown Content:
דף הבית | חיפוש משרות | חברות | מדריכים
המשרה אינה זמינה יותר. ייתכן שהמעסיק הסיר אותה או שהיא כבר אוישה.
משרות דומות שעשויות לעניין אותך: מפתח Backend, מפתח Full Stack, מהנדס DevOps.
"""

LINKEDIN_CLOSED = LINKEDIN_GUEST_JOB.replace(
    "Acme · Tel Aviv-Yafo · 2 weeks ago", "No longer accepting applications"
)

GREENHOUSE_CLOSED = """Title: Acme
Markdown Content:
Sorry, but the job you are looking for is no longer open. You can view all open
positions at Acme on our careers page, and sign up for job alerts to hear about new
roles that match your interests and experience.
"""

CLOUDFLARE = """Title: Just a moment...
URL Source: https://jobs.example.com/123
Markdown Content:
jobs.example.com
Checking your browser before accessing jobs.example.com. This process is automatic.
Your browser will redirect to your requested content shortly. Please allow up to 5 seconds.
"""

JINA_404 = """Title: Not Found
URL Source: https://jobs.lever.co/acme/abc
Warning: Target URL returned error 404: Not Found
Markdown Content:
Sorry, we couldn't find anything here. The job posting you're looking for might have
closed, or it might have been removed. Please check the URL or browse our other roles.
"""

ERROR_PAGE = """Title: Acme Careers
Markdown Content:
Home | About | Careers | Contact
Page not found. The page you requested could not be found. It may have been moved or
deleted. Please return to the homepage and try again, or contact our support team.
"""

CAPTCHA_PAGE = """Title: Security check
Markdown Content:
Please complete the CAPTCHA below so we know you're a person and not an automated
program. This helps us keep the site safe for everyone. Having trouble? Refresh the
page or try again later from a different network connection.
"""

COMPANY_HOMEPAGE = """Title: Acme - Home
Markdown Content:
Acme builds tools for modern teams. Our platform helps thousands of companies around
the world collaborate, share documents and move faster. Read our blog, meet our
customers, and see our pricing plans for startups and enterprises.
"""


@pytest.mark.parametrize(
    "text, reason",
    [
        (LINKEDIN_AUTHWALL, "bad_title"),
        (GENERIC_LOGIN, "login_wall"),
        (COOKIE_WALL, "cookie_wall"),
        (HEBREW_UNAVAILABLE, "job_unavailable"),
        (LINKEDIN_CLOSED, "job_unavailable"),
        (GREENHOUSE_CLOSED, "job_unavailable"),
        (CLOUDFLARE, "blocked"),
        (JINA_404, "http_error_404"),
        (ERROR_PAGE, "error_page"),
        (CAPTCHA_PAGE, "captcha"),
        (COMPANY_HOMEPAGE, "no_job_content"),
        ("Short text", "too_short"),
        ("", "empty"),
        (None, "empty"),
    ],
    ids=[
        "linkedin_authwall",
        "login",
        "cookies",
        "hebrew_unavailable",
        "linkedin_closed",
        "greenhouse_closed",
        "cloudflare",
        "jina_404",
        "error_page",
        "captcha",
        "homepage",
        "short",
        "empty",
        "none",
    ],
)
def test_non_job_pages_are_rejected(text, reason):
    """באג: דפי התחברות / cookies / 'המשרה אינה זמינה' עברו את הבדיקה הישנה."""
    assert validate_content(text) == (False, reason)


def test_html_title_is_checked_for_playwright_content():
    html = "<html><head><title>Login | Acme</title></head><body>" + "x " * 200 + "</body></html>"
    assert validate_content(html) == (False, "bad_title")


# ------------------------------------------------------------ user messages


def test_failure_message_prefers_most_informative_reason():
    # Jina ראה דף התחברות, Playwright ראה דף בלי תוכן -> מדווחים על ההתחברות
    assert "התחברות" in failure_message(["login_wall", "no_job_content"])
    assert "סגורה" in failure_message(["too_short", "job_unavailable"])
    assert "404" in failure_message(["http_error_404"])
    assert failure_message([None, "too_short"]) == "הסורק לא הצליח לחלץ תיאור משרה"
