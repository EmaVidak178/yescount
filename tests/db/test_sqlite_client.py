from __future__ import annotations

from src.db.sqlite_client import create_session, get_events, upsert_event


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
