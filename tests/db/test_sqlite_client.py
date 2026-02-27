from __future__ import annotations

import os

import pytest

from src.db.sqlite_client import create_session, get_connection, get_events, upsert_event


def test_upsert_event_and_fetch(sqlite_db, sample_event):
    event_id = upsert_event(sqlite_db, sample_event)
    assert event_id > 0
    events = get_events(sqlite_db)
    assert len(events) == 1
    assert events[0]["title"] == "Sample Event"


def test_create_session(sqlite_db):
    session_id = create_session(
        sqlite_db,
        name="Night Out",
        created_by="Ema",
        admin_preferences={"budget_cap": 30.0},
        expiry_days=7,
    )
    assert isinstance(session_id, str)
    assert len(session_id) > 10


def test_get_connection_falls_back_to_sqlite_when_database_url_empty(tmp_path):
    """When DATABASE_URL is unset/empty, get_connection uses SQLite at db_path."""
    os.environ.pop("DATABASE_URL", None)
    db_path = str(tmp_path / "fallback.db")
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT 1 AS n").fetchone()
        assert row is not None
        assert row[0] == 1 or row["n"] == 1
    finally:
        conn.close()


def test_get_connection_raises_when_database_url_invalid(tmp_path, mocker):
    """When DATABASE_URL is set but psycopg.connect fails, get_connection propagates the error."""
    pytest.importorskip("psycopg")
    mocker.patch("psycopg.connect", side_effect=ConnectionError("connection refused"))
    os.environ["DATABASE_URL"] = (
        "postgresql://user:pass@invalid:5432/db"  # pragma: allowlist secret
    )
    try:
        with pytest.raises(ConnectionError, match="connection refused"):
            get_connection(str(tmp_path / "unused.db"))
    finally:
        os.environ.pop("DATABASE_URL", None)


def test_get_connection_raises_when_database_url_unreachable(tmp_path, mocker):
    """When DATABASE_URL is set but connect raises, get_connection does not silently fall back."""
    pytest.importorskip("psycopg")
    mocker.patch("psycopg.connect", side_effect=Exception("network unreachable"))
    os.environ["DATABASE_URL"] = "postgresql://user:pass@host:5432/db"  # pragma: allowlist secret
    try:
        with pytest.raises(Exception, match="network unreachable"):
            get_connection(str(tmp_path / "unused.db"))
    finally:
        os.environ.pop("DATABASE_URL", None)
