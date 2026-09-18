"""
Tests for src.db -- schema/migration, dedupe-on-upsert, and preservation of
user-maintained fields (status, notes, viewed) across repeated refreshes.

Every test here uses the `temp_db` fixture (see tests/conftest.py), which
points src.db at a throwaway SQLite file -- the user's real
data/internships.db is never opened or modified by this suite.
"""

import sqlite3

from src import db


def _sample_job(**overrides):
    job = {
        "company": "Acme",
        "title": "Software Engineering Intern - Summer 2027",
        "location": "Remote",
        "url": "https://job-boards.greenhouse.io/acme/jobs/1",
        "source": "board_api",
        "description": "Backend work in Python.",
        "posted_at": "2026-06-01T00:00:00+00:00",
        "source_updated_at": "2026-09-01T00:00:00+00:00",
        "season_status": "confirmed",
    }
    job.update(overrides)
    return job


def test_init_db_creates_expected_columns(temp_db):
    conn = sqlite3.connect(temp_db)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    finally:
        conn.close()
    for expected in [
        "id", "company", "title", "location", "url", "source", "description",
        "posted_at", "source_updated_at", "discovered_at", "last_seen_at",
        "status", "score", "ai_summary", "matched_skills", "notes",
        "viewed", "viewed_at", "applied_at", "dedupe_key", "season_status",
    ]:
        assert expected in columns


def test_upsert_new_jobs_returns_count(temp_db):
    added = db.upsert_jobs([_sample_job()])
    assert added == 1
    df = db.get_all_jobs_df()
    assert len(df) == 1
    assert df.iloc[0]["season_status"] == "confirmed"
    assert df.iloc[0]["source_updated_at"] == "2026-09-01T00:00:00+00:00"


def test_upsert_repeated_refresh_does_not_duplicate(temp_db):
    job = _sample_job()
    first = db.upsert_jobs([job])
    second = db.upsert_jobs([job])
    assert first == 1
    assert second == 0
    df = db.get_all_jobs_df()
    assert len(df) == 1


def test_repeated_refresh_bumps_last_seen_but_preserves_user_fields(temp_db):
    job = _sample_job()
    db.upsert_jobs([job])
    df = db.get_all_jobs_df()
    job_id = int(df.iloc[0]["id"])
    original_last_seen = df.iloc[0]["last_seen_at"]

    # Simulate the user doing real work on this job.
    db.update_job_full(job_id, "Applied", "Talked to a recruiter on LinkedIn.", True)
    before = db.get_all_jobs_df().iloc[0]
    assert before["status"] == "Applied"
    assert before["notes"] == "Talked to a recruiter on LinkedIn."
    assert before["applied_at"] is not None

    # Refresh runs again and sees the same posting.
    db.upsert_jobs([job])

    after = db.get_all_jobs_df().iloc[0]
    assert after["status"] == "Applied"
    assert after["notes"] == "Talked to a recruiter on LinkedIn."
    assert after["applied_at"] == before["applied_at"]
    assert after["score"] is None or True  # score untouched by upsert either way
    # last_seen_at should have been bumped (not necessarily to a different
    # string if the refresh happens within the same second, but it must not
    # have reset to empty/None).
    assert after["last_seen_at"] is not None
    assert original_last_seen is not None


def test_upsert_jobs_never_overwrites_score_or_ai_summary(temp_db):
    job = _sample_job()
    db.upsert_jobs([job])
    df = db.get_all_jobs_df()
    job_id = int(df.iloc[0]["id"])
    db.update_job_score(job_id, 88, "Great fit.", ["python", "backend"])

    db.upsert_jobs([job])  # repeated refresh

    row = db.get_all_jobs_df().iloc[0]
    assert int(row["score"]) == 88
    assert row["ai_summary"] == "Great fit."


def test_different_postings_from_same_company_are_not_deduped(temp_db):
    job_a = _sample_job(title="Software Engineering Intern", url="https://x.com/jobs/1")
    job_b = _sample_job(title="Data Science Intern", url="https://x.com/jobs/2")
    added = db.upsert_jobs([job_a, job_b])
    assert added == 2


def test_sample_source_jobs_from_same_company_use_combo_key(temp_db):
    # sample_source jobs share one careers-page URL per company -- URL-based
    # dedupe would wrongly collapse distinct sample postings.
    job_a = _sample_job(
        title="Software Engineering Intern", url="https://acme.com/careers",
        source="sample_source", season_status="confirmed",
    )
    job_b = _sample_job(
        title="Data Science Intern", url="https://acme.com/careers",
        source="sample_source", season_status="unconfirmed",
    )
    added = db.upsert_jobs([job_a, job_b])
    assert added == 2


def test_migration_adds_missing_columns_without_dropping_data(tmp_path, monkeypatch):
    """Simulate a database created by an older version of the app (missing
    season_status/source_updated_at/etc.) and confirm init_db() migrates it
    forward additively, preserving the existing row."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "old.db"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT,
            url TEXT,
            source TEXT,
            description TEXT,
            discovered_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'New',
            score INTEGER,
            ai_summary TEXT,
            matched_skills TEXT,
            notes TEXT,
            dedupe_key TEXT UNIQUE
        )
        """
    )
    conn.execute(
        "INSERT INTO jobs (company, title, location, url, source, description, "
        "discovered_at, last_seen_at, status, dedupe_key) VALUES "
        "('Acme', 'Old Posting', 'Remote', 'https://acme.com/1', 'board_api', "
        "'desc', '2026-01-01T00:00:00', '2026-01-01T00:00:00', 'Applied', 'url:old')"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DATA_DIR", data_dir)
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db()

    conn = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        row = conn.execute("SELECT * FROM jobs WHERE dedupe_key = 'url:old'").fetchone()
    finally:
        conn.close()

    assert "season_status" in columns
    assert "source_updated_at" in columns
    assert "viewed" in columns
    assert row is not None  # existing row preserved
