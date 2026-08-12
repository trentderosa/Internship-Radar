"""
GitHub-based internship listing collector (scaffold).

Several popular internship-tracking repos on GitHub (for example the
"Summer2027-Internships" style README lists maintained by the community)
publish a markdown table of company / role / location / link rows. This
collector is a starting point for pulling from a source like that.

It is intentionally simple for this first version of Internship Radar:
- It is NOT wired into the default "Refresh Jobs" flow yet.
- Network or parsing failures must never crash the app, so every public
  function here fails soft and returns an empty list on error.

Future work: point RAW_MARKDOWN_URL at a real repo, tighten up the table
parsing, and add it as an optional source in Settings.
"""

import requests
import re

SOURCE_NAME = "github_sources"

# Placeholder: replace with a real raw README URL when ready to go live,
# e.g. "https://raw.githubusercontent.com/<org>/<repo>/main/README.md"
RAW_MARKDOWN_URL = ""

REQUEST_TIMEOUT_SECONDS = 10


def _parse_markdown_table(markdown_text: str) -> list:
    """
    Very small, forgiving parser for GitHub-flavored markdown tables shaped
    like: | Company | Role | Location | Link |

    This is deliberately not a full markdown parser -- just enough to pull
    rows out of the simple pipe-delimited tables these README lists use.
    """
    jobs = []
    lines = markdown_text.splitlines()

    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        # Skip markdown table separator rows like |---|---|---|
        if re.match(r"^\|[\s:\-|]+\|$", line):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue

        company, title, location = cells[0], cells[1], cells[2]
        if company.lower() in ("company", ""):
            continue  # header row

        # Try to pull a URL out of a markdown link like [Apply](https://...)
        url_match = re.search(r"\((https?://[^\s)]+)\)", line)
        url = url_match.group(1) if url_match else ""

        jobs.append(
            {
                "company": re.sub(r"[\[\]*]", "", company).strip(),
                "title": re.sub(r"[\[\]*]", "", title).strip(),
                "location": location.strip(),
                "url": url,
                "source": SOURCE_NAME,
                "description": f"{title} at {company} ({location}).",
            }
        )

    return jobs


def fetch_github_internships() -> list:
    """
    Fetch and parse internship postings from a public GitHub markdown list.

    Returns an empty list if RAW_MARKDOWN_URL is not configured, or if
    anything goes wrong fetching/parsing it. This keeps the collector safe
    to call from the app even before it's fully set up.
    """
    if not RAW_MARKDOWN_URL:
        return []

    try:
        response = requests.get(RAW_MARKDOWN_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return _parse_markdown_table(response.text)
    except (requests.RequestException, ValueError):
        # Network hiccup, bad URL, timeout, etc. -- fail soft.
        return []
