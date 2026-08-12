"""
Deduplication helpers.

Jobs are deduplicated primarily by URL. When a posting has no URL -- or
when its URL isn't a per-posting link in the first place -- we fall back to
a normalized company + title + location key. Normalization strips
whitespace/punctuation and lowercases everything so trivial formatting
differences ("Capital One" vs "Capital One ") don't create duplicates.
"""

import re


def normalize_text(value: str) -> str:
    """Lowercase, collapse whitespace, and strip punctuation-ish noise."""
    if not value:
        return ""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\s]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_url(url: str) -> str:
    """Normalize a URL for comparison (strip trailing slash/query noise)."""
    if not url:
        return ""
    url = url.strip().lower()
    url = url.split("?")[0]  # drop query params (tracking params, etc.)
    url = url.rstrip("/")
    return url


def dedupe_key(job: dict) -> str:
    """
    Build the key used to detect duplicate postings.

    If the job has a URL, the key is the normalized URL -- unless it's from
    "sample_source", which intentionally points every posting from a given
    company at that one company's general careers page (there's no real
    per-posting URL for sample data). Keying on URL there would wrongly
    collapse distinct sample postings from the same company (e.g. Capital
    One's Software Engineering and Data Science interns) into a single
    "duplicate". Real collectors provide an exact posting URL per job, so
    URL-based keying is correct for them. Whenever URL-based keying isn't
    used, we fall back to a composite of normalized company + title + location.
    """
    url = normalize_url(job.get("url", ""))
    if url and job.get("source") != "sample_source":
        return f"url:{url}"

    company = normalize_text(job.get("company", ""))
    title = normalize_text(job.get("title", ""))
    location = normalize_text(job.get("location", ""))
    return f"combo:{company}|{title}|{location}"


def dedupe_job_list(jobs: list) -> list:
    """Remove duplicates within a single batch of freshly-collected jobs."""
    seen = set()
    unique_jobs = []
    for job in jobs:
        key = dedupe_key(job)
        if key in seen:
            continue
        seen.add(key)
        unique_jobs.append(job)
    return unique_jobs
