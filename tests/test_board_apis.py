"""
Tests for src.collectors.board_apis -- relevance filtering, season
filtering, date-field handling, and network/malformed-response isolation.

All network access is mocked (monkeypatch on `requests.get`) -- these tests
never make a real HTTP call and never touch a paid API.
"""

import json

import pytest
import requests

from src.collectors import board_apis


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, json_error=False):
        self.status_code = status_code
        self._json_data = json_data
        self._json_error = json_error

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} error")

    def json(self):
        if self._json_error:
            raise json.JSONDecodeError("bad json", "", 0)
        return self._json_data


# ---------------------------------------------------------------------------
# _looks_like_relevant_internship -- title-evidence + exclusion + relevance
# ---------------------------------------------------------------------------

def test_excludes_full_time_role_mentioning_internal():
    assert not board_apis._looks_like_relevant_internship(
        "Internal Tools Engineer", "Full-time role building internal software tools."
    )


def test_excludes_role_mentioning_international():
    assert not board_apis._looks_like_relevant_internship(
        "Director, International Tax", "Leads international tax strategy."
    )


def test_includes_genuine_software_internship():
    assert board_apis._looks_like_relevant_internship(
        "Software Engineering Intern - Summer 2027",
        "Build backend services in Python.",
    )


def test_includes_genuine_coop():
    assert board_apis._looks_like_relevant_internship(
        "Software Developer Co-op", "Join our backend platform team."
    )


def test_excludes_sales_intern_even_when_description_mentions_engineering():
    assert not board_apis._looks_like_relevant_internship(
        "Sales Development Intern",
        "You'll partner closely with our software engineering team on outbound tooling.",
    )


def test_excludes_marketing_intern():
    assert not board_apis._looks_like_relevant_internship(
        "Marketing Intern", "Support our brand and social media campaigns."
    )


def test_excludes_legal_intern():
    assert not board_apis._looks_like_relevant_internship(
        "Legal Intern", "Support the legal team with contract review."
    )


def test_excludes_full_time_role_even_with_relevant_keywords():
    # No internship-title evidence at all -- must be excluded regardless of
    # how relevant the description sounds.
    assert not board_apis._looks_like_relevant_internship(
        "Senior Software Engineer, Backend", "Build our core platform in Python."
    )


def test_description_only_mention_of_interns_does_not_qualify_a_full_time_role():
    # The description references "our interns" but the title has no
    # internship evidence at all -- title is the required evidence.
    assert not board_apis._looks_like_relevant_internship(
        "Backend Software Engineer",
        "You'll mentor our summer interns as part of this full-time role.",
    )


# ---------------------------------------------------------------------------
# Greenhouse parsing -- posted_at vs source_updated_at
# ---------------------------------------------------------------------------

def test_greenhouse_does_not_use_updated_at_as_posted_at():
    raw = {
        "title": "Software Engineering Intern - Summer 2027",
        "location": {"name": "Remote"},
        "content": "<p>Great role</p>",
        "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/1",
        "updated_at": "2026-09-01T00:00:00Z",
        # no "first_published" provided by this board
    }
    parsed = board_apis._parse_greenhouse_job(raw, "Acme")
    assert parsed["posted_at"] == ""
    assert parsed["source_updated_at"] == "2026-09-01T00:00:00Z"


def test_greenhouse_uses_first_published_as_posted_at_when_present():
    raw = {
        "title": "Software Engineering Intern - Summer 2027",
        "location": {"name": "Remote"},
        "content": "<p>Great role</p>",
        "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/1",
        "updated_at": "2026-09-01T00:00:00Z",
        "first_published": "2026-06-15T00:00:00Z",
    }
    parsed = board_apis._parse_greenhouse_job(raw, "Acme")
    assert parsed["posted_at"] == "2026-06-15T00:00:00Z"
    assert parsed["source_updated_at"] == "2026-09-01T00:00:00Z"


def test_lever_created_at_used_as_posted_at():
    raw = {
        "text": "Software Engineering Intern - Summer 2027",
        "categories": {"location": "Remote"},
        "descriptionPlain": "Great role",
        "hostedUrl": "https://jobs.lever.co/acme/1",
        "createdAt": 1750000000000,
        "updatedAt": 1751000000000,
    }
    parsed = board_apis._parse_lever_posting(raw, "Acme")
    assert parsed["posted_at"] != ""
    assert parsed["source_updated_at"] != ""
    assert parsed["posted_at"] != parsed["source_updated_at"]


# ---------------------------------------------------------------------------
# fetch_company_jobs -- network isolation, malformed responses, season filter
# ---------------------------------------------------------------------------

def test_fetch_company_jobs_isolates_network_error(monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.exceptions.ConnectionError("boom")

    monkeypatch.setattr(board_apis.requests, "get", fake_get)
    jobs, error, excluded = board_apis.fetch_company_jobs(
        {"company": "Acme", "board": "greenhouse", "token": "acme"}
    )
    assert jobs == []
    assert excluded == 0
    assert "ConnectionError" in error


def test_fetch_company_jobs_isolates_http_error(monkeypatch):
    monkeypatch.setattr(
        board_apis.requests, "get", lambda *a, **k: _FakeResponse(status_code=404)
    )
    jobs, error, excluded = board_apis.fetch_company_jobs(
        {"company": "Acme", "board": "greenhouse", "token": "stale-token"}
    )
    assert jobs == []
    assert error is not None


def test_fetch_company_jobs_isolates_malformed_json(monkeypatch):
    monkeypatch.setattr(
        board_apis.requests, "get", lambda *a, **k: _FakeResponse(json_error=True)
    )
    jobs, error, excluded = board_apis.fetch_company_jobs(
        {"company": "Acme", "board": "greenhouse", "token": "acme"}
    )
    assert jobs == []
    assert error is not None


def test_fetch_company_jobs_unknown_board_type():
    jobs, error, excluded = board_apis.fetch_company_jobs(
        {"company": "Acme", "board": "workday", "token": "acme"}
    )
    assert jobs == []
    assert "Unknown board type" in error


def test_fetch_company_jobs_filters_incompatible_season(monkeypatch):
    payload = {
        "jobs": [
            {
                "title": "Software Engineering Intern - Summer 2027",
                "location": {"name": "Remote"},
                "content": "Python backend work.",
                "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/1",
            },
            {
                "title": "Software Engineering Intern - Summer 2026",
                "location": {"name": "Remote"},
                "content": "Python backend work.",
                "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/2",
            },
        ]
    }
    monkeypatch.setattr(
        board_apis.requests, "get", lambda *a, **k: _FakeResponse(json_data=payload)
    )
    jobs, error, excluded = board_apis.fetch_company_jobs(
        {"company": "Acme", "board": "greenhouse", "token": "acme"}
    )
    assert error is None
    assert len(jobs) == 1
    assert jobs[0]["title"].endswith("2027")
    assert jobs[0]["season_status"] == "confirmed"
    assert excluded == 1


def test_fetch_all_board_jobs_one_bad_source_does_not_break_others(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        if "broken" in url:
            raise requests.exceptions.Timeout("slow")
        return _FakeResponse(json_data={"jobs": [
            {
                "title": "Software Engineering Intern - Summer 2027",
                "location": {"name": "Remote"},
                "content": "Python backend work.",
                "absolute_url": "https://job-boards.greenhouse.io/good/jobs/1",
            },
        ]})

    monkeypatch.setattr(board_apis.requests, "get", fake_get)
    sources = [
        {"company": "Broken Co", "board": "greenhouse", "token": "broken"},
        {"company": "Good Co", "board": "greenhouse", "token": "good"},
    ]
    jobs, stats = board_apis.fetch_all_board_jobs(sources)
    assert len(jobs) == 1
    assert jobs[0]["company"] == "Good Co"
    assert len(stats) == 2
    broken_stat = next(s for s in stats if s["company"] == "Broken Co")
    good_stat = next(s for s in stats if s["company"] == "Good Co")
    assert broken_stat["error"] is not None
    assert broken_stat["found"] == 0
    assert good_stat["error"] is None
    assert good_stat["found"] == 1
