from __future__ import annotations

import pytest

from src.db.sqlite_client import create_session, upsert_event
from src.engine.availability import get_group_availability, set_availability
from src.engine.voting import cast_vote
from src.sessions.manager import join_session


@pytest.mark.integration
def test_session_vote_flow(sqlite_db, sample_event):
    upsert_event(sqlite_db, sample_event)
    session_id = create_session(
        sqlite_db,
        name="Flow",
        created_by="Ema",
        admin_preferences={},
        expiry_days=7,
    )
    participant_id = join_session(sqlite_db, session_id, "Leo")
    cast_vote(sqlite_db, session_id, participant_id, 1, True)
    set_availability(sqlite_db, session_id, participant_id, [("2026-03-10", "19:00", "21:00")])
    rows = sqlite_db.execute(
        "SELECT COUNT(*) AS c FROM votes WHERE session_id = ?", (session_id,)
    ).fetchone()
    assert int(rows["c"]) == 1
    availability = get_group_availability(sqlite_db, session_id)
    assert availability["participant_count"] == 1
    assert len(availability["slots"]) == 1
