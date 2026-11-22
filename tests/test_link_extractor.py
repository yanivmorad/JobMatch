"""חילוץ קישורי משרות מטקסט גולמי (הודעות וואטסאפ כמו שהמשתמש מקבל אותן)."""
from pathlib import Path

import pytest

from services.link_extractor import extract_job_links, ignore_reason, normalize_job_url

SAMPLE = (Path(__file__).parent / "fixtures" / "whatsapp_jobs.txt").read_text(encoding="utf-8")


def test_whatsapp_sample_extracts_exactly_the_job_links():
    result = extract_job_links(SAMPLE)
    assert result.jobs == [
        "https://hiremetech.com/job/147318715",
        "https://hiremetech.com/job/142860792",
        "https://rapaport.bamboohr.com/careers/307",
        "https://mazebolt.com/careers-apply/co/technical-services/0F.476/junior-customer-success-manager/all",
        "https://hibob-fa0ad69d0cb34a.careers.hibob.com/jobs/e49599be-f624-4f28-bf2c-8fb84d01597e",
        "https://job-boards.greenhouse.io/gitlab/jobs/8937825002",
        "https://www.sett.ai/careers/ai-artist/C4.57B/",
    ]


def test_whatsapp_sample_reports_what_was_ignored_and_why():
    ignored = {i["url"]: i["reason"] for i in extract_job_links(SAMPLE).ignored}
    assert ignored == {
        "https://apps.apple.com/il/app/orah-chat/id6825354831": "לא משרה (חנות אפליקציות)",
        "https://apps.apple.com/il/app/hireme-lite/id6833974939": "לא משרה (חנות אפליקציות)",
        "https://hiremetech.com/communities": "דף כללי של HireMeTech (לא משרה)",
        "https://hiremetech.com/meetups/groups": "דף כללי של HireMeTech (לא משרה)",
    }


def test_link_glued_to_hebrew_text_stops_at_the_hebrew():
    text = "לינק: https://x.careers.hibob.com/jobs/e49599be-8fb84d01597eערב טוב לכולם"
    assert extract_job_links(text).jobs == ["https://x.careers.hibob.com/jobs/e49599be-8fb84d01597e"]


def test_same_job_from_two_groups_is_one_link():
    text = (
        "https://hiremetech.com/job/1?utm_source=a&utm_content=x\n"
        "https://hiremetech.com/job/1?utm_source=b"
    )
    assert extract_job_links(text).jobs == ["https://hiremetech.com/job/1"]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("*לינק:* https://jobs.lever.co/acme/123*", "https://jobs.lever.co/acme/123"),  # בולד של וואטסאפ
        ("(https://jobs.lever.co/acme/123).", "https://jobs.lever.co/acme/123"),
        ("ראו https://jobs.lever.co/acme/123, וגם", "https://jobs.lever.co/acme/123"),
        ("www.comeet.com/jobs/acme/1A.2B3/role/4C.5D6", "https://www.comeet.com/jobs/acme/1A.2B3/role/4C.5D6"),
    ],
)
def test_surrounding_punctuation_is_not_part_of_the_link(text, expected):
    assert extract_job_links(text).jobs == [expected]


def test_query_params_that_identify_the_job_are_kept():
    assert normalize_job_url(
        "https://www.alljobs.co.il/Search/UploadSingle.aspx?JobID=8591522&utm_source=wa"
    ) == "https://www.alljobs.co.il/Search/UploadSingle.aspx?JobID=8591522"
    assert normalize_job_url(
        "https://careers.acme.com/jobs?gh_jid=4001&fbclid=abc"
    ) == "https://careers.acme.com/jobs?gh_jid=4001"


def test_linkedin_tracking_and_search_links():
    assert normalize_job_url(
        "https://il.linkedin.com/jobs/view/data-analyst-4492047393?trk=public_jobs&refId=x&trackingId=y"
    ) == "https://il.linkedin.com/jobs/view/data-analyst-4492047393"
    # קישור חיפוש עם משרה נבחרת -> דף המשרה עצמו
    assert normalize_job_url(
        "https://www.linkedin.com/jobs/search/?currentJobId=4418676195&keywords=data"
    ) == "https://www.linkedin.com/jobs/view/4418676195/"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/posts/someone_hiring-activity-123",
        "https://www.linkedin.com/company/acme/",
        "https://chat.whatsapp.com/AbCdEf",
        "https://wa.me/972500000000",
        "https://t.me/jobs_channel",
        "https://www.acme.com/",
        "https://hiremetech.com/he-il/jobs-app?view=jobs",
    ],
)
def test_non_job_links_are_ignored(url):
    assert ignore_reason(normalize_job_url(url)) is not None


@pytest.mark.parametrize(
    "url",
    [
        "https://hiremetech.com/he-il/job/153667177",
        "https://il.linkedin.com/jobs/view/senior-data-analyst-at-holisto-4418676195",
        "https://www.drushim.co.il/job/38846757/b4712ce9/",
        "https://amat.wd1.myworkdayjobs.com/External/job/RehovotISR/PWP-reaserch-Student_R2614690",
        "https://justt.ai/job/chargeback-analyst/",
    ],
)
def test_job_links_are_kept(url):
    assert ignore_reason(normalize_job_url(url)) is None


def test_text_without_links():
    result = extract_job_links("אין פה שום קישור, רק טקסט")
    assert result.jobs == [] and result.ignored == []
