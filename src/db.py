"""
SQLite persistence layer for Internship Radar.

Everything the app does to store or retrieve jobs goes through this module.
It is responsible for:
- creating the database/table if they don't exist yet
- inserting new jobs while deduplicating against what's already stored
- updating a job's score/status/notes
- reading jobs back out as a pandas DataFrame for the dashboard

Keeping this in one place means app.py never has to write raw SQL.
"""

import sqlite3
from datetime import datetime, timezone

import pandas as pd

from src.config import DATA_DIR, DB_PATH, DEFAULT_STATUS, PLACEHOLDER_URL_MARKERS
from src.dedupe import dedupe_key
from src.urls import get_company_careers_url

JOB_COLUMNS = [
    "id",
    "company",
    "title",
    "location",
    "url",
    "source",
    "description",
    "posted_at",
    "source_updated_at",
    "discovered_at",
    "last_seen_at",
    "status",
    "score",
    "ai_summary",
    "matched_skills",
    "notes",
    "viewed",
    "viewed_at",
    "applied_at",
    "dedupe_key",
    "season_status",
]

# Columns that may be missing on a database created by an older version of
# the app. Each entry is (column_name, SQL type/default) used to build an
# ALTER TABLE ... ADD COLUMN statement. Migration is additive-only -- it
# never drops or rewrites existing data.
#
# Four distinct dates/timestamps are tracked on each job, and it matters
# that they stay distinct:
#   - posted_at         -- genuine original publication date, when the
#                           source actually provides one (never a source's
#                           "last updated" field -- see board_apis.py).
#   - source_updated_at  -- when the source system says the listing itself
#                           was last modified (e.g. Greenhouse's updated_at).
#   - discovered_at      -- when *this app* first saw the posting (set once,
#                           on insert, never changed).
#   - last_seen_at       -- when *this app* most recently saw the posting
#                           still listed by its source (bumped on every
#                           refresh that finds it again).
_MIGRATION_COLUMNS = [
    ("viewed", "INTEGER NOT NULL DEFAULT 0"),
    ("viewed_at", "TEXT"),
    ("applied_at", "TEXT"),
    ("posted_at", "TEXT"),
    ("source_updated_at", "TEXT"),
    ("season_status", "TEXT"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    """Open a connection to the SQLite database, creating the folder/file
    if this is the first time the app has run."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the jobs table if it doesn't already exist, and migrate an
    existing table forward if it's missing newer columns. Safe to call
    every time the app starts -- never drops or rewrites existing rows."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                company        TEXT NOT NULL,
                title          TEXT NOT NULL,
                location       TEXT,
                url            TEXT,
                source         TEXT,
                description    TEXT,
                posted_at      TEXT,
                source_updated_at TEXT,
                discovered_at  TEXT NOT NULL,
                last_seen_at   TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'New',
                score          INTEGER,
                ai_summary     TEXT,
                matched_skills TEXT,
                notes          TEXT,
                viewed         INTEGER NOT NULL DEFAULT 0,
                viewed_at      TEXT,
                applied_at     TEXT,
                dedupe_key     TEXT UNIQUE,
                season_status  TEXT
            )
            """
        )
        conn.commit()

        existing_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
        }
        for column_name, column_def in _MIGRATION_COLUMNS:
            if column_name not in existing_columns:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_def}")
        conn.commit()
    finally:
        conn.close()

    clean_placeholder_urls()


def clean_placeholder_urls() -> int:
    """
    One-time-per-row cleanup for jobs already saved with a broken URL.
    Two rules, so real posting links are never touched:

      1. Rows from "sample_source" always get reconciled to that company's
         known-good careers page. Sample jobs never had a real posting to
         link to in the first place -- earlier versions of the sample data
         guessed a specific posting path (e.g. ".../machine-learning-intern-
         2027") that doesn't actually exist and 404s. Those guessed paths
         don't necessarily contain an obvious marker like "/404", so they
         need reconciling unconditionally, not just marker-matching.
      2. Rows from any other source are only touched if their URL contains
         an obvious placeholder marker (see PLACEHOLDER_URL_MARKERS) -- a
         real collector's posting URL would never match one of these, so
         this never overwrites real data.

    Each bad URL is replaced with a known-good company careers page if one
    exists, otherwise cleared so the UI shows "No verified link" instead of
    a dead one. Jobs themselves are never deleted. Safe to call on every
    startup -- it's a no-op once a row is already correct. Returns the
    number of rows updated.
    """
    conn = get_connection()
    updated = 0
    try:
        rows = conn.execute("SELECT id, company, url, source FROM jobs").fetchall()
        for row in rows:
            url = (row["url"] or "").strip()
            replacement = get_company_careers_url(row["company"])

            if row["source"] == "sample_source":
                if url != replacement:
                    conn.execute("UPDATE jobs SET url = ? WHERE id = ?", (replacement, row["id"]))
                    updated += 1
                continue

            if url and any(marker in url.lower() for marker in PLACEHOLDER_URL_MARKERS):
                conn.execute("UPDATE jobs SET url = ? WHERE id = ?", (replacement, row["id"]))
                updated += 1
        conn.commit()
    finally:
        conn.close()

    return updated


def upsert_jobs(jobs: list) -> int:
    """
    Insert a batch of freshly-collected jobs, skipping any that already
    exist in the database (matched by URL, or by normalized
    company+title+location when there's no URL).

    Existing jobs that show up again just get their last_seen_at bumped so
    we know the posting is still live. Returns the count of NEW jobs added.
    """
    conn = get_connection()
    new_count = 0
    try:
        for job in jobs:
            key = dedupe_key(job)
            now = _now_iso()

            existing = conn.execute(
                "SELECT id FROM jobs WHERE dedupe_key = ?", (key,)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE jobs SET last_seen_at = ? WHERE id = ?",
                    (now, existing["id"]),
                )
                continue

            conn.execute(
                """
                INSERT INTO jobs (
                    company, title, location, url, source, description,
                    posted_at, source_updated_at, discovered_at, last_seen_at,
                    status, score, ai_summary, matched_skills, notes,
                    viewed, viewed_at, applied_at, dedupe_key, season_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.get("company", "").strip(),
                    job.get("title", "").strip(),
                    job.get("location", "").strip(),
                    job.get("url", "").strip(),
                    job.get("source", "").strip(),
                    job.get("description", "").strip(),
                    (job.get("posted_at") or "").strip(),
                    (job.get("source_updated_at") or "").strip(),
                    now,
                    now,
                    DEFAULT_STATUS,
                    None,
                    None,
                    None,
                    None,
                    0,
                    None,
                    None,
                    key,
                    (job.get("season_status") or "unconfirmed").strip(),
                ),
            )
            new_count += 1
        conn.commit()
    finally:
        conn.close()

    return new_count


def get_jobs_needing_score() -> list:
    """Return jobs that haven't been scored yet (score IS NULL), as a list
    of plain dicts -- used right after a refresh to rank new postings."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM jobs WHERE score IS NULL").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_job_score(job_id: int, score: int, summary: str, matched_skills: list) -> None:
    """Save the score/summary/matched_skills produced by the ranker."""
    conn = get_connection()
    try:
        skills_text = ", ".join(matched_skills) if matched_skills else ""
        conn.execute(
            "UPDATE jobs SET score = ?, ai_summary = ?, matched_skills = ? WHERE id = ?",
            (score, summary, skills_text, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def _apply_status_side_effects(conn: sqlite3.Connection, job_id: int, status: str) -> None:
    """
    Setting a status is a deliberate action, so it always implies the job
    has been viewed. On top of that, specific statuses stamp their own
    timestamp the first time they're reached:
      - "Applied"  -> applied_at, if not already set
      - "Viewed"   -> viewed_at, if not already set (also handled generically below)
    Existing timestamps are never overwritten.
    """
    now = _now_iso()
    conn.execute(
        "UPDATE jobs SET viewed = 1, viewed_at = COALESCE(viewed_at, ?) WHERE id = ?",
        (now, job_id),
    )
    if status == "Applied":
        conn.execute(
            "UPDATE jobs SET applied_at = COALESCE(applied_at, ?) WHERE id = ?",
            (now, job_id),
        )


def update_job_status(job_id: int, status: str) -> None:
    """Update a job's status, applying viewed/applied_at side effects."""
    conn = get_connection()
    try:
        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        _apply_status_side_effects(conn, job_id, status)
        conn.commit()
    finally:
        conn.close()


def update_job_full(job_id: int, status: str, notes: str, viewed: bool) -> None:
    """Update status + notes + the viewed flag together -- used by the job
    detail editor, where `viewed` is a checkbox the user can set directly.
    Setting status to "Applied" stamps applied_at the first time it happens;
    checking "Viewed" stamps viewed_at the first time it happens."""
    conn = get_connection()
    try:
        now = _now_iso()
        conn.execute(
            "UPDATE jobs SET status = ?, notes = ?, viewed = ? WHERE id = ?",
            (status, notes, 1 if viewed else 0, job_id),
        )
        if viewed:
            conn.execute(
                "UPDATE jobs SET viewed_at = COALESCE(viewed_at, ?) WHERE id = ?",
                (now, job_id),
            )
        if status == "Applied":
            conn.execute(
                "UPDATE jobs SET applied_at = COALESCE(applied_at, ?) WHERE id = ?",
                (now, job_id),
            )
        conn.commit()
    finally:
        conn.close()


def mark_viewed(job_id: int) -> None:
    """Mark a job as viewed without changing its status -- used when a job
    is opened/selected in the detail editor."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE jobs SET viewed = 1, viewed_at = COALESCE(viewed_at, ?) WHERE id = ?",
            (_now_iso(), job_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_jobs_df() -> pd.DataFrame:
    """Return every job in the database as a pandas DataFrame, newest
    first. Returns an empty (but correctly-shaped) DataFrame if the table
    is empty or doesn't exist yet."""
    init_db()  # make sure the table exists before we query it
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM jobs ORDER BY discovered_at DESC", conn
        )
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame(columns=[c for c in JOB_COLUMNS])

    return df
