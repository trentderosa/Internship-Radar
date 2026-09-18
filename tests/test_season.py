"""
Tests for src.season -- Summer 2027 targeting.

Policy under test:
- Explicit "Summer 2027" (in any of the phrasings the regex handles) ->
  "confirmed".
- Any other explicit season+year combo (wrong season, wrong year, or both)
  -> "incompatible", meant to be excluded from collection.
- No season/year signal at all -> "unconfirmed", kept and labeled rather
  than guessed at.
- A bare year with no season word never gets upgraded to "confirmed" --
  the app must never invent "Summer" out of a posting that only says
  "2027".
"""

import pytest

from src.season import classify_season, season_label


@pytest.mark.parametrize(
    "title,description",
    [
        ("Software Engineering Intern - Summer 2027", ""),
        ("2027 Summer Software Engineering Intern", ""),
        ("Software Engineer Intern (Summer 2027)", ""),
        ("Data Science Intern", "Join us for our Summer 2027 internship cohort."),
        ("Software Engineering Intern - Summer '27", ""),
    ],
)
def test_confirmed_summer_2027(title, description):
    assert classify_season(title, description) == "confirmed"


@pytest.mark.parametrize(
    "title,description",
    [
        ("Software Engineering Intern - Summer 2026", ""),
        ("Fall 2027 Co-op", ""),
        ("Software Engineer Intern (Winter 2027)", ""),
        ("Data Science Intern", "This is a Spring 2027 internship."),
        ("2026 Internship Program", ""),
    ],
)
def test_incompatible_season_or_year(title, description):
    assert classify_season(title, description) == "incompatible"


@pytest.mark.parametrize(
    "title,description",
    [
        ("Software Engineering Intern", ""),
        ("Machine Learning Intern", "Work on ML models for our data platform."),
        ("2027 Internship Program", ""),  # bare correct year, no season word
    ],
)
def test_unconfirmed_when_no_clear_season_year_signal(title, description):
    assert classify_season(title, description) == "unconfirmed"


def test_never_invents_summer_from_bare_year():
    # A posting that only ever says "2027" (no "summer") must not be
    # reported as a confirmed Summer 2027 match.
    assert classify_season("2027 Internship Program", "Join our 2027 cohort.") == "unconfirmed"


def test_season_label_confirmed():
    assert season_label("confirmed") == "Summer 2027"


def test_season_label_unconfirmed():
    assert season_label("unconfirmed") == "Season unconfirmed"


def test_season_label_defaults_unconfirmed_for_unknown_or_missing_value():
    assert season_label(None) == "Season unconfirmed"
    assert season_label("") == "Season unconfirmed"
    assert season_label("incompatible") == "Season unconfirmed"
