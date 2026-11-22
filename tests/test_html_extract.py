from scraper_service.html_extract import html_to_document

_LONG = "<p>" + "We are looking for an engineer with 2+ years of experience in Python and SQL. " * 10 + "</p>"


def test_main_content_without_scripts_or_navigation():
    html = f"""<html><head><meta property="og:title" content="Backend Engineer - Acme">
    <title>Careers | Acme</title><script>window.x = 1</script></head>
    <body><nav>Home About Jobs</nav><main><h1>Backend Engineer</h1>{_LONG}</main>
    <aside>Similar jobs</aside><footer>Copyright</footer></body></html>"""
    doc = html_to_document(html, "https://acme.com/jobs/1")

    assert doc.startswith("Title: Backend Engineer - Acme\n")  # og:title קודם ל-<title>
    assert "URL Source: https://acme.com/jobs/1" in doc
    assert "# Backend Engineer" in doc and "2+ years of experience" in doc
    for junk in ("window.x", "Home About Jobs", "Similar jobs", "Copyright"):
        assert junk not in doc


def test_tiny_main_falls_back_to_the_whole_body():
    """<main> שיש בו רק באנר - התיאור עצמו מחוץ לו."""
    html = f"<html><body><main><h2>Join us!</h2></main><div class='job'>{_LONG}</div></body></html>"
    assert "2+ years of experience" in html_to_document(html, "https://acme.com/j")


def test_asp_net_page_inside_a_form_is_kept():
    """ב-ASP.NET (AllJobs) כל הדף בתוך <form> - אסור לזרוק אותו."""
    html = f"<html><body><form id='aspnetForm'><div id='content'>{_LONG}</div></form></body></html>"
    assert "2+ years of experience" in html_to_document(html, "https://www.alljobs.co.il/x.aspx?JobID=1")


def test_final_url_line_only_after_a_redirect():
    html = f"<html><body>{_LONG}</body></html>"
    assert "Final URL" not in html_to_document(html, "https://acme.com/j/1", final_url="https://acme.com/j/1/")
    doc = html_to_document(html, "https://acme.com/j/1", final_url="https://acme.com/careers")
    assert "Final URL: https://acme.com/careers" in doc
