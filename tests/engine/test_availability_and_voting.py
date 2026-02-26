from __future__ import annotations

from src.db.sqlite_client import create_session, upsert_event
from src.engine.availability import get_group_availability, set_availability
from src.engine.voting import get_participant_votes, get_session_vote_tallies
from src.sessions.manager import join_session


def test_availability_overlap(sqlite_db):
    session_id = create_session(sqlite_db, "Plan", "Ema", {}, 7)
    participant_id = join_session(sqlite_db, session_id, "Alex")
    set_availability(sqlite_db, session_id, participant_id, [("2026-03-10", "17:00", "19:00")])
    data = get_group_availability(sqlite_db, session_id)
    assert data["participant_count"] == 1
    assert len(data["slots"]) == 1


def test_voting_helpers(sqlite_db, sample_event):
    upsert_event(sqlite_db, sample_event)
    session_id = create_session(sqlite_db, "Plan", "Ema", {}, 7)
    participant_id = join_session(sqlite_db, session_id, "Alex")
    from src.engine.voting import cast_vote

    cast_vote(sqlite_db, session_id, participant_id, 1, True)
    tallies = get_session_vote_tallies(sqlite_db, session_id)
    votes = get_participant_votes(sqlite_db, session_id, participant_id)
    assert tallies[1] == 1
    assert len(votes) == 1
