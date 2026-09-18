"""
Stand-alone CLI to sanity-check every board token in src.config.BOARD_SOURCES
against the real Greenhouse/Lever APIs. Run this after pulling changes to
BOARD_SOURCES, or periodically, to catch a company that renamed its board or
switched ATS providers before it silently stops contributing postings.

    python scripts/verify_boards.py

Needs normal internet access (this repo's own sandboxed dev environment may
have outbound network restricted; this is expected to be run on a regular
machine, e.g. the same one you run `streamlit run app.py` on).

If a token comes back broken:
1. Search "<company> careers" and look for a "Powered by Greenhouse" or
   "Powered by Lever" footer, or open browser devtools -> Network tab while
   loading their careers page and look for a request to
   boards-api.greenhouse.io or api.lever.co -- the token is the path
   segment right after "/boards/" or "/postings/".
2. Update the "token" (and "board" if they switched providers) for that
   company in src/config.py's BOARD_SOURCES.
3. Re-run this script to confirm.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.collectors.board_apis import fetch_company_jobs  # noqa: E402
from src.config import BOARD_SOURCES  # noqa: E402


def main() -> int:
    if not BOARD_SOURCES:
        print("No board sources configured in src/config.py -- nothing to check.")
        return 0

    print(f"Checking {len(BOARD_SOURCES)} board source(s)...\n")
    broken = []

    for source in BOARD_SOURCES:
        jobs, error, excluded_season = fetch_company_jobs(source)
        label = f"{source['company']:<20} {source['board']:<10} token={source['token']}"
        if error:
            print(f"[BROKEN] {label} -- {error}")
            broken.append(source["company"])
        else:
            extra = f" (+{excluded_season} excluded for wrong season)" if excluded_season else ""
            print(f"[ok]     {label} -- {len(jobs)} relevant posting(s){extra}")

    print()
    if broken:
        print(f"{len(broken)} source(s) need attention: {', '.join(broken)}")
        return 1

    print("All board sources resolved successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
