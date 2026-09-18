"""
Season/year classification for internship postings.

Internship Radar targets **Summer 2027**. Postings need to fall into one of
three buckets:

- "confirmed"    -- the text explicitly says "Summer 2027" (or an
                     equivalent phrasing). Safe to treat as a real match.
- "incompatible" -- the text explicitly names a different season and/or
                     year (e.g. "Summer 2026", "Fall 2027", "2026
                     Internship Program"). These should be excluded from
                     collection entirely.
- "unconfirmed"  -- no clear season/year signal either way (e.g. just
                     "Software Engineering Intern" with no date). These are
                     kept, but clearly labeled "Season unconfirmed" and
                     never counted as a confirmed Summer 2027 match --
                     per project policy we never invent a date that isn't
                     actually stated.

This is a deliberately conservative, regex-based heuristic over free text,
not a real date parser -- it will not catch every phrasing a company might
use, and that's an accepted, documented limitation (see README). It is
tuned to avoid two failure modes seen in practice: silently keeping a
Summer 2026 posting because only a bare "2026" appeared, and silently
inventing "Summer" for a posting that only ever says "2027" with no season
word attached.
"""

import re

TARGET_SEASON = "summer"
TARGET_YEAR = 2027

_SEASON_ALT = r"(summer|fall|autumn|winter|spring)"
_YEAR_ALT = r"(20\d{2})"
_GAP = r"[^a-z0-9]{0,12}"

# "Summer 2027", "Summer, 2027", "Summer of 2027", "Summer - 2027"
_SEASON_THEN_YEAR_RE = re.compile(
    rf"\b{_SEASON_ALT}\b{_GAP}{_YEAR_ALT}\b", re.IGNORECASE
)
# "2027 Summer", "2027 Summer Internship"
_YEAR_THEN_SEASON_RE = re.compile(
    rf"\b{_YEAR_ALT}\b{_GAP}{_SEASON_ALT}\b", re.IGNORECASE
)
# "Summer '27" / "Summer 27" -- a shorthand two-digit year, assumed 2000s.
_SEASON_THEN_SHORT_YEAR_RE = re.compile(
    rf"\b{_SEASON_ALT}\b[^a-z0-9]{{0,4}}'?(\d{{2}})\b", re.IGNORECASE
)

# A bare year mentioned close to internship/program language, with no
# season word attached at all (e.g. "2026 Internship Program", "Class of
# 2026"). Close enough to be an explicit signal, not close enough to be a
# real season match -- these push a posting to "incompatible" if the year
# is wrong, but never to "confirmed" if the year happens to be right,
# since no season was actually stated.
_PROGRAM_CONTEXT_WORDS = (
    "intern", "internship", "co-op", "coop", "program", "cohort",
    "class of", "recruiting", "rotational",
)
_BARE_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def _normalize_short_year(two_digit: str) -> int:
    return 2000 + int(two_digit)


def _find_season_year_pairs(text: str) -> list:
    """Return a list of (season, year) tuples for every explicit
    season+year combination found in `text` (already lowercased)."""
    pairs = []
    for m in _SEASON_THEN_YEAR_RE.finditer(text):
        pairs.append((m.group(1).lower(), int(m.group(2))))
    for m in _YEAR_THEN_SEASON_RE.finditer(text):
        pairs.append((m.group(2).lower(), int(m.group(1))))
    for m in _SEASON_THEN_SHORT_YEAR_RE.finditer(text):
        pairs.append((m.group(1).lower(), _normalize_short_year(m.group(2))))
    return pairs


def _find_program_context_bare_years(text: str) -> list:
    """Years mentioned within a short window of internship/program
    language but with no season word directly attached to them."""
    years = []
    for m in _BARE_YEAR_RE.finditer(text):
        year = int(m.group(1))
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 40)
        window = text[start:end]
        if any(word in window for word in _PROGRAM_CONTEXT_WORDS):
            years.append(year)
    return years


def classify_season(title: str, description: str = "") -> str:
    """
    Classify a posting's season/year fit against TARGET_SEASON/TARGET_YEAR.
    Returns "confirmed", "incompatible", or "unconfirmed". Never raises.
    """
    text = f"{title or ''} {description or ''}".lower()

    pairs = _find_season_year_pairs(text)
    if any(season == TARGET_SEASON and year == TARGET_YEAR for season, year in pairs):
        return "confirmed"
    if pairs:
        # At least one explicit season+year combo was found, and none of
        # them was Summer 2027 -- an explicit mismatch.
        return "incompatible"

    bare_years = _find_program_context_bare_years(text)
    if any(year != TARGET_YEAR for year in bare_years):
        return "incompatible"

    # Either no year signal at all, or only a bare TARGET_YEAR with no
    # season word -- not enough to confidently call it "Summer 2027"
    # without inventing the season, so it stays unconfirmed.
    return "unconfirmed"


SEASON_LABELS = {
    "confirmed": f"Summer {TARGET_YEAR}",
    "unconfirmed": "Season unconfirmed",
}


def season_label(season_status: str) -> str:
    """Human-readable label for a stored season_status value. Treats
    anything unrecognized (including None/empty, e.g. rows from before this
    column existed) as unconfirmed rather than guessing."""
    return SEASON_LABELS.get(season_status, SEASON_LABELS["unconfirmed"])
