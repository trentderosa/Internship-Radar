"""
Tests for src.dedupe -- URL normalization and dedupe-key construction.

Key behavior under test: normalize_url must strip *known tracking* query
params (utm_*, ref, fbclid, ...) but preserve any other query param, since
some boards' only per-posting identifier lives in the query string (e.g. a
Greenhouse embed URL's `gh_jid`). Dropping every param unconditionally --
the previous behavior -- risked silently collapsing two different postings
into one "duplicate".
"""

from src.dedupe import dedupe_job_list, dedupe_key, normalize_text, normalize_url


def test_normalize_url_strips_tracking_params():
    url = "https://boards.greenhouse.io/acme/jobs/123?utm_source=twitter&utm_campaign=fall"
    assert normalize_url(url) == "https://boards.greenhouse.io/acme/jobs/123"


def test_normalize_url_preserves_job_identifying_param():
    url = "https://job-boards.greenhouse.io/embed/job_app?for=acme&gh_jid=987654"
    normalized = normalize_url(url)
    assert "gh_jid=987654" in normalized


def test_normalize_url_preserving_param_distinguishes_two_postings():
    url_a = "https://job-boards.greenhouse.io/embed/job_app?for=acme&gh_jid=111"
    url_b = "https://job-boards.greenhouse.io/embed/job_app?for=acme&gh_jid=222"
    assert normalize_url(url_a) != normalize_url(url_b)


def test_normalize_url_strips_trailing_slash_and_lowercases():
    assert normalize_url("HTTPS://Example.com/Jobs/123/") == "https://example.com/jobs/123"


def test_normalize_url_param_order_does_not_matter():
    url_a = "https://x.com/job?gh_jid=1&other=2"
    url_b = "https://x.com/job?other=2&gh_jid=1"
    assert normalize_url(url_a) == normalize_url(url_b)


def test_normalize_url_empty():
    assert normalize_url("") == ""
    assert normalize_url(None) == ""


def test_normalize_text_lowercases_and_strips_punctuation():
    assert normalize_text("Capital One, Inc.") == "capital one inc"


def test_dedupe_key_uses_url_for_real_source():
    job = {"company": "Acme", "title": "SWE Intern", "location": "Remote",
           "url": "https://acme.com/jobs/1?utm_source=x", "source": "board_api"}
    assert dedupe_key(job) == "url:https://acme.com/jobs/1"


def test_dedupe_key_uses_combo_for_sample_source_even_with_url():
    job = {"company": "Acme", "title": "SWE Intern", "location": "Remote",
           "url": "https://acme.com/careers", "source": "sample_source"}
    assert dedupe_key(job).startswith("combo:")


def test_dedupe_key_falls_back_to_combo_without_url():
    job = {"company": "Acme", "title": "SWE Intern", "location": "Remote",
           "url": "", "source": "board_api"}
    assert dedupe_key(job) == "combo:acme|swe intern|remote"


def test_dedupe_job_list_removes_duplicates_within_batch():
    jobs = [
        {"company": "Acme", "title": "SWE Intern", "location": "Remote",
         "url": "https://acme.com/jobs/1", "source": "board_api"},
        {"company": "Acme", "title": "SWE Intern", "location": "Remote",
         "url": "https://acme.com/jobs/1?utm_source=linkedin", "source": "board_api"},
    ]
    result = dedupe_job_list(jobs)
    assert len(result) == 1
