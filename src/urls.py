"""
URL validation and link-trust helpers.

Sample data (and eventually scraped postings) can end up with broken or
placeholder links. This module is the single place that decides whether a
stored URL is safe to show as a clickable link, and how much to trust it.
"""

from src.config import COMPANY_CAREERS_URLS, PLACEHOLDER_URL_MARKERS
from src.dedupe import normalize_text


def is_valid_url(url: str) -> bool:
    """A URL is usable if it's non-empty, starts with http(s)://, and
    doesn't contain a known placeholder/broken-link marker."""
    if not url or not url.strip():
        return False
    candidate = url.strip().lower()
    if not (candidate.startswith("http://") or candidate.startswith("https://")):
        return False
    if any(marker in candidate for marker in PLACEHOLDER_URL_MARKERS):
        return False
    return True


def link_status(url: str, source: str) -> str:
    """
    Classify how much a stored URL can be trusted:
      - "Missing"      -- no usable URL (empty, or fails is_valid_url)
      - "Needs Review" -- a valid URL, but from sample_source, which points
                           to a general company careers page rather than a
                           confirmed exact posting
      - "Verified"      -- a valid URL from a real posting source
    """
    if not is_valid_url(url):
        return "Missing"
    if source == "sample_source":
        return "Needs Review"
    return "Verified"


def get_company_careers_url(company: str) -> str:
    """Look up a known-good careers page for a company by name. Returns an
    empty string if there's no known mapping."""
    return COMPANY_CAREERS_URLS.get(normalize_text(company), "")
