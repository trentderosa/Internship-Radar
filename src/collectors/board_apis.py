"""
Real job board collector -- Greenhouse and Lever public APIs.

Unlike sample_source (static illustrative data) or github_sources (a
markdown-table scaffold, not yet wired in), this collector pulls *live*
postings directly from the same JSON APIs that power the public "Careers"
pages of companies using Greenhouse or Lever as their applicant tracking
system. No HTML scraping, no API key required -- both endpoints are
unauthenticated and intended for exactly this kind of public consumption:

  Greenhouse:  https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true
  Lever:       https://api.lever.co/v0/postings/<token>?mode=json

`<token>` is the identifier the company uses in its own board URL and is
configured per-company in src.config.BOARD_SOURCES.

Design goals:
- One bad/renamed token or one company's API being briefly down must never
  take down the whole refresh -- every network call is isolated and fails
  soft (logged in the returned stats, not raised).
- Only postings that actually look like a relevant internship are kept
  (see src.config.INTERNSHIP_TITLE_KEYWORDS / EXCLUDED_TITLE_KEYWORDS /
  RELEVANT_POSTING_KEYWORDS) -- a company's sales/legal/marketing
  internships are filtered out here so they never reach the dashboard or
  get scored, and postings explicitly for a season/year other than Summer
  2027 are filtered out too (see src.season).
- Output shape matches src.collectors.sample_source, plus `source_updated_at`
  and `season_status` (company, title, location, url, source, description,
  posted_at, source_updated_at, season_status), so app.py/db.py can treat
  every source identically.
- posted_at is only ever set from a field that represents genuine original
  publication (Lever's `createdAt`, or Greenhouse's `first_published` when
  the board provides it) -- Greenhouse's `updated_at` reflects the last
  time the posting's *listing* changed (which can be nothing more than a
  metadata edit) and is never used as a publication date. It's kept
  separately as source_updated_at so the UI can be honest about which date
  is which.
"""

import re
from datetime import datetime, timezone

import requests

from src.config import (
    BOARD_SOURCES,
    EXCLUDED_TITLE_KEYWORDS,
    INTERNSHIP_TITLE_KEYWORDS,
    RELEVANT_POSTING_KEYWORDS,
)
from src.season import classify_season
from src.text_match import any_keyword_present

SOURCE_NAME = "board_api"
REQUEST_TIMEOUT_SECONDS = 10

GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
LEVER_URL = "https://api.lever.co/v0/postings/{token}"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html_text: str) -> str:
    """Greenhouse job content comes back as HTML. Keep only the text --
    the dashboard/table render plain descriptions, not markup."""
    if not html_text:
        return ""
    text = _TAG_RE.sub(" ", html_text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_relevant_internship(title: str, description: str = "") -> bool:
    """
    Title is the primary (and for the internship/exclusion checks, the
    *only*) evidence -- see the INTERNSHIP_TITLE_KEYWORDS docstring in
    src/config.py for why. All matching is whole-word (src.text_match), so
    "Internal Tools Engineer" and "Director, International Tax" -- both
    real postings seen on live boards during development -- correctly fail
    the internship check instead of matching "intern" as a substring.
    """
    title_lower = (title or "").lower()
    if not any_keyword_present(INTERNSHIP_TITLE_KEYWORDS, title_lower):
        return False
    if any_keyword_present(EXCLUDED_TITLE_KEYWORDS, title_lower):
        return False

    text = f"{title_lower} {(description or '').lower()}"
    return any_keyword_present(RELEVANT_POSTING_KEYWORDS, text)


def _epoch_ms_to_iso(value) -> str:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).isoformat(
            timespec="seconds"
        )
    except (TypeError, ValueError, OSError):
        return ""


def _fetch_greenhouse(token: str) -> list:
    url = GREENHOUSE_URL.format(token=token)
    response = requests.get(
        url, params={"content": "true"}, timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("jobs", []) or []


def _parse_greenhouse_job(raw: dict, company_display_name: str) -> dict:
    title = raw.get("title", "") or ""
    location = (raw.get("location") or {}).get("name", "") or ""
    description = _strip_html(raw.get("content", ""))
    # Some Greenhouse boards include a genuine "first_published" timestamp
    # in the jobs list response -- when present, that's a real publication
    # date. `updated_at` is NOT a publication date (it moves any time the
    # listing is edited) and must never be used for posted_at.
    posted_at = raw.get("first_published", "") or ""
    return {
        "company": company_display_name,
        "title": title,
        "location": location,
        "url": raw.get("absolute_url", "") or "",
        "source": SOURCE_NAME,
        "description": description,
        "posted_at": posted_at,
        "source_updated_at": raw.get("updated_at", "") or "",
    }


def _fetch_lever(token: str) -> list:
    url = LEVER_URL.format(token=token)
    response = requests.get(url, params={"mode": "json"}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def _parse_lever_posting(raw: dict, company_display_name: str) -> dict:
    title = raw.get("text", "") or ""
    categories = raw.get("categories") or {}
    location = categories.get("location", "") or ""
    description = _strip_html(raw.get("descriptionPlain") or raw.get("description") or "")
    return {
        "company": company_display_name,
        "title": title,
        "location": location,
        "url": raw.get("hostedUrl", "") or "",
        "source": SOURCE_NAME,
        "description": description,
        # Lever's createdAt genuinely is when the posting was created.
        "posted_at": _epoch_ms_to_iso(raw.get("createdAt")),
        "source_updated_at": _epoch_ms_to_iso(raw.get("updatedAt")),
    }


def fetch_company_jobs(source_config: dict) -> tuple:
    """
    Fetch and filter postings for a single company. Returns
    (jobs, error_message, excluded_season_count). error_message is None on
    success (even if zero relevant postings were found) -- callers use it
    purely for surfacing "this token looks stale" feedback, never to fail
    the batch. excluded_season_count is how many otherwise-relevant
    internship postings were dropped for naming an explicitly incompatible
    season/year (e.g. "Summer 2026"), so the UI can show that filtering is
    happening rather than making a source look emptier than it is.
    """
    company = source_config.get("company", "")
    board = source_config.get("board", "")
    token = source_config.get("token", "")

    try:
        if board == "greenhouse":
            raw_jobs = _fetch_greenhouse(token)
            parsed = [_parse_greenhouse_job(j, company) for j in raw_jobs]
        elif board == "lever":
            raw_jobs = _fetch_lever(token)
            parsed = [_parse_lever_posting(j, company) for j in raw_jobs]
        else:
            return [], f"Unknown board type '{board}'", 0
    except (requests.RequestException, ValueError) as exc:
        return [], f"{type(exc).__name__}: {exc}", 0

    relevant = [
        job for job in parsed
        if job["title"] and _looks_like_relevant_internship(job["title"], job["description"])
    ]

    kept = []
    excluded_season_count = 0
    for job in relevant:
        season_status = classify_season(job["title"], job["description"])
        if season_status == "incompatible":
            excluded_season_count += 1
            continue
        job["season_status"] = season_status
        kept.append(job)

    return kept, None, excluded_season_count


def fetch_all_board_jobs(sources: list = None) -> tuple:
    """
    Fetch every configured board source. Never raises -- a broken token or
    network error for one company just gets recorded in `stats` and skipped.

    Returns (jobs, stats) where stats is a list of per-source dicts:
      {"company": ..., "board": ..., "token": ..., "found": <int>,
       "excluded_season": <int>, "error": <str|None>}
    so the UI/settings page can show exactly what happened on the last
    refresh (including which tokens look like they need re-checking, and
    how many postings were filtered out for the wrong season).
    """
    sources = sources if sources is not None else BOARD_SOURCES
    all_jobs = []
    stats = []

    for source_config in sources:
        jobs, error, excluded_season = fetch_company_jobs(source_config)
        all_jobs.extend(jobs)
        stats.append(
            {
                "company": source_config.get("company", ""),
                "board": source_config.get("board", ""),
                "token": source_config.get("token", ""),
                "found": len(jobs),
                "excluded_season": excluded_season,
                "error": error,
            }
        )

    return all_jobs, stats
