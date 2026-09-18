"""
Small persistence helper for "what happened on the last refresh".

This is deliberately separate from the jobs table in db.py -- it isn't job
data, it's metadata about the collection run itself (when it happened, how
many new postings each source contributed, which board tokens errored out).
Storing it as a small JSON file next to the SQLite database is simpler than
a schema migration for something this size, and it's fine if it's lost
(worst case: the dashboard just doesn't show a "Last refreshed" line until
the next refresh).
"""

import json
from datetime import datetime, timezone

from src.config import DATA_DIR

REFRESH_STATE_PATH = DATA_DIR / "last_refresh.json"


def save_refresh_state(source_counts: dict, board_stats: list) -> None:
    """
    source_counts: {"sample_source": <new int>, "board_api": <new int>}
    board_stats:   per-company stats from board_apis.fetch_all_board_jobs,
                   so Settings can show exactly which tokens are stale.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "refreshed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_counts": source_counts,
        "board_stats": board_stats,
    }
    try:
        REFRESH_STATE_PATH.write_text(json.dumps(state, indent=2))
    except OSError:
        # Best-effort only -- a failed write here should never break a
        # refresh that otherwise succeeded.
        pass


def load_refresh_state() -> dict:
    if not REFRESH_STATE_PATH.exists():
        return {}
    try:
        return json.loads(REFRESH_STATE_PATH.read_text())
    except (OSError, ValueError):
        return {}
