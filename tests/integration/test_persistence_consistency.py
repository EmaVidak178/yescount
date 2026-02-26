from __future__ import annotations

import pytest

from src.db.sqlite_client import get_availability, get_events, upsert_event


@pytest.mark.integration
def test_event_upsert_updates_existing_row(sqlite_db, sample_event):
    event_id_1 = upsert_event(sqlite_db, sample_event)
    updated_event = {**sample_event, "title": "Updated Event Title"}
    event_id_2 = upsert_event(sqlite_db, updated_event)
    rows = get_events(sqlite_db, query="Updated Event Title")
    assert event_id_1 == event_id_2
    assert len(rows) == 1
    assert rows[0]["title"] == "Updated Event Title"


@pytest.mark.integration
def test_availability_replace_is_idempotent(sqlite_db):
    session_id = "session-1"
    participant_id = 11
    sqlite_db.execute(
        "INSERT INTO sessions (id, name, created_by, admin_preferences_json, expires_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, "Plan", "Ema", "{}", "2999-01-01T00:00:00+00:00"),
    )
    sqlite_db.execute(
        "INSERT INTO participants (id, session_id, name, name_normalized) VALUES (?, ?, ?, ?)",
        (participant_id, session_id, "Alex", "alex"),
    )
    sqlite_db.commit()
    slots = [("2026-03-10", "19:00", "21:00")]
    from src.db.sqlite_client import replace_availability

    replace_availability(sqlite_db, session_id, participant_id, slots)
    replace_availability(sqlite_db, session_id, participant_id, slots)
    stored = get_availability(sqlite_db, session_id)
    assert len(stored) == 1
