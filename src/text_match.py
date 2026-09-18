"""
Shared keyword-matching helpers.

Plain `keyword in text` substring matching has a real, demonstrated bug:
"intern" is a substring of "internal" and "international", "ai" is a
substring of ordinary words like "maintain" and "domain", and so on. That
bug is exactly what let full-time roles like "Internal Tools Engineer" or
"Director, International Tax" get miscounted as internships when this
project's live board collector was checked against real Greenhouse data
(see src/collectors/board_apis.py). `keyword_present()` bounds every match
on both sides by "not an alphanumeric character" so short keywords can't
match as part of a longer word, while still matching multi-word phrases
("machine learning") and symbol-containing keywords ("c++", "c#") that
plain `\\b` regex word boundaries don't handle well.
"""

import re

_WORD_CHAR = r"[a-z0-9]"


def keyword_present(keyword: str, text: str) -> bool:
    """True if `keyword` appears in `text` (both assumed already lowercased)
    as a whole word/phrase, not as a substring of some longer word."""
    if not keyword or not text:
        return False
    pattern = (
        r"(?<!" + _WORD_CHAR + r")"
        + re.escape(keyword)
        + r"(?!" + _WORD_CHAR + r")"
    )
    return re.search(pattern, text) is not None


def any_keyword_present(keywords, text: str) -> bool:
    """True if any keyword in `keywords` is present in `text` as a whole
    word/phrase (see keyword_present)."""
    return any(keyword_present(kw, text) for kw in keywords)


def matched_keywords(keywords, text: str) -> list:
    """Return the subset of `keywords` that are present in `text` as whole
    words/phrases, preserving the input order."""
    return [kw for kw in keywords if keyword_present(kw, text)]
