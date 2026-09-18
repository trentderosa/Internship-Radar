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
  (see src.config.INTERNSHIP_TITLE_KEYWORDS / RELEVANT_POSTING_KEYWORDS) --
  a company's sales/legal/marketing internships are filtered out here so
  they never reach the dashboard or get scored.
- Output shape matches src.collectors.sample_source exactly (company,
  title, location, url, source, description, plus an optional
  posted_at), so app.py can treat every source identically.
"""

import re
from datetime import datetime, timezone

import requests

from src.config import (
    BOARD_SOURCES,
    INTERNSHIP_TITLE_KEYWORDS,
    RELEVANT_POSTING_KEYWORDS,
)
from src.dedupe import normalize_text

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
    text = f" {title} {description} ".lower()
    is_internship = any(kw in text for kw in INTERNSHIP_TITLE_KEYWORDS)
    if not is_internship:
        return False
    return any(kw in text for kw in RELEVANT_POSTING_KEYWORDS)


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
    return {
        "company": company_display_name,
        "title": title,
        "location": location,
        "url": raw.get("absolute_url", "") or "",
        "source": SOURCE_NAME,
        "description": description,
        "posted_at": raw.get("updated_at", "") or "",
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
        "posted_at": _epoch_ms_to_iso(raw.get("createdAt")),
    }


def fetch_company_jobs(source_config: dict) -> tuple:
    """
    Fetch and filter postings for a single company. Returns
    (jobs, error_message). error_message is None on success (even if zero
    relevant postings were found) -- callers use it purely for
    surfacing "this token looks stale" feedback, never to fail the batch.
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
            return [], f"Unknown board type '{board}'"
    except (requests.RequestException, ValueError) as exc:
        return [], f"{type(exc).__name__}: {exc}"

    relevant = [
        job for job in parsed
        if job["title"] and _looks_like_relevant_internship(job["title"], job["description"])
    ]
    return relevant, None


def fetch_all_board_jobs(sources: list = None) -> tuple:
    """
    Fetch every configured board source. Never raises -- a broken token or
    network error for one company just gets recorded in `stats` and skipped.

    Returns (jobs, stats) where stats is a list of per-source dicts:
      {"company": ..., "board": ..., "token": ..., "found": <int>, "error": <str|None>}
    so the UI/settings page can show exactly what happened on the last
    refresh (including which tokens look like they need re-checking).
    """
    sources = sources if sources is not None else BOARD_SOURCES
    all_jobs = []
    stats = []

    for source_config in sources:
        jobs, error = fetch_company_jobs(source_config)
        all_jobs.extend(jobs)
        stats.append(
            {
                "company": source_config.get("company", ""),
                "board": source_config.get("board", ""),
                "token": source_config.get("token", ""),
                "found": len(jobs),
                "error": error,
            }
        )

    return all_jobs, stats
