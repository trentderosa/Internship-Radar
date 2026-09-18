"""
Tests for the keyword-fallback scorer in src.ranker.

These tests call `_fallback_score()` directly -- never `rank_job()` or
`_openai_score()` -- so this suite never makes a network call or spends a
paid OpenAI API credit, regardless of whether a real OPENAI_API_KEY is
configured in the developer's .env.
"""

from src.ranker import _fallback_score


def test_no_false_positive_on_java_substring_of_javascript():
    job = {"title": "Frontend Intern", "description": "Build UIs with JavaScript and CSS.", "location": ""}
    result = _fallback_score(job)
    assert "java" not in result["matched_skills"]


def test_no_false_positive_on_ai_substring_of_maintain_domain_training():
    job = {
        "title": "Support Intern",
        "description": "You'll maintain documentation and help with training materials in this domain.",
        "location": "",
    }
    result = _fallback_score(job)
    assert "ai" not in result["matched_skills"]


def test_matches_genuine_skills():
    job = {
        "title": "Software Engineering Intern",
        "description": "Work with Python, SQL, and AWS cloud infrastructure.",
        "location": "",
    }
    result = _fallback_score(job)
    assert "python" in result["matched_skills"]
    assert "sql" in result["matched_skills"]
    assert "cloud" in result["matched_skills"] or "aws" in result["matched_skills"]
    assert result["score"] > 0


def test_location_bonus_applied_for_preferred_location():
    job = {"title": "Software Engineer Intern", "description": "Python backend work.", "location": "Arlington, VA"}
    job_no_pref = {"title": "Software Engineer Intern", "description": "Python backend work.", "location": "Boise, ID"}
    result_pref = _fallback_score(job)
    result_no_pref = _fallback_score(job_no_pref)
    assert result_pref["score"] >= result_no_pref["score"]


def test_empty_posting_scores_zero():
    job = {"title": "", "description": "", "location": ""}
    result = _fallback_score(job)
    assert result["score"] == 0
    assert result["matched_skills"] == []


def test_rank_job_uses_fallback_when_no_openai_client(monkeypatch):
    """Force the no-API-key path explicitly (regardless of what's in this
    machine's .env) so this test never risks a real network/API call."""
    import src.ranker as ranker

    monkeypatch.setattr(ranker, "_client", None)
    job = {"title": "Data Science Intern", "description": "Python and pandas.", "location": "Remote"}
    result = ranker.rank_job(job)
    assert "python" in result["matched_skills"]
