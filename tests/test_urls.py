"""Tests for src.urls -- link validity and trust-level classification."""

from src.urls import is_valid_url, link_status


def test_valid_real_url():
    assert is_valid_url("https://boards.greenhouse.io/acme/jobs/1") is True


def test_invalid_empty_url():
    assert is_valid_url("") is False
    assert is_valid_url(None) is False


def test_invalid_placeholder_url():
    assert is_valid_url("https://company.com/careers/software-engineer-2027") is False
    assert is_valid_url("https://acme.com/404") is False


def test_invalid_non_http_scheme():
    assert is_valid_url("ftp://acme.com/jobs/1") is False


def test_link_status_missing_for_invalid_url():
    assert link_status("", "board_api") == "Missing"


def test_link_status_needs_review_for_sample_source():
    assert link_status("https://acme.com/careers", "sample_source") == "Needs Review"


def test_link_status_verified_for_real_source():
    assert link_status("https://boards.greenhouse.io/acme/jobs/1", "board_api") == "Verified"
