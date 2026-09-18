"""
Shared pytest fixtures.

Every test in this suite that touches the database uses the `temp_db`
fixture below, which points src.db at a throwaway SQLite file in pytest's
own tmp_path rather than the user's real data/internships.db. No test here
ever opens the real database or calls a paid API (OpenAI) -- ranker tests
exercise the keyword fallback path directly instead of going through
rank_job()/the OpenAI client.
"""

import pytest

from src import db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point src.db at an isolated, empty SQLite database for the duration
    of a test. Never touches the user's real data/internships.db."""
    data_dir = tmp_path / "data"
    db_path = data_dir / "test_internships.db"
    monkeypatch.setattr(db, "DATA_DIR", data_dir)
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db()
    return db_path
