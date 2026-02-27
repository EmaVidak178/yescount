from __future__ import annotations

from src.db.sqlite_client import create_session, upsert_event
from src.engine.availability import get_group_availability, set_availability
from src.engine.voting import (
    cast_vote,
    get_participant_votes,
    get_session_interested_participants_by_event,
    get_session_vote_tallies,
)
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
    cast_vote(sqlite_db, session_id, participant_id, 1, True)
    tallies = get_session_vote_tallies(sqlite_db, session_id)
    votes = get_participant_votes(sqlite_db, session_id, participant_id)
    assert tallies[1] == 1
    assert len(votes) == 1


def test_get_session_interested_participants_by_event(sqlite_db, sample_event):
    """Returns event_id -> [participant names] for interested votes."""
    event_id = upsert_event(sqlite_db, sample_event)
    session_id = create_session(sqlite_db, "Plan", "Ema", {}, 7)
    alex_id = join_session(sqlite_db, session_id, "Alex")
    beth_id = join_session(sqlite_db, session_id, "Beth")
    cast_vote(sqlite_db, session_id, alex_id, event_id, True)
    cast_vote(sqlite_db, session_id, beth_id, event_id, True)
    mapping = get_session_interested_participants_by_event(sqlite_db, session_id)
    assert mapping[event_id] == ["Alex", "Beth"]


def test_get_session_interested_participants_by_event_excludes_not_interested(
    sqlite_db, sample_event
):
    """Only interested=1 votes are included."""
    event_id = upsert_event(sqlite_db, sample_event)
    session_id = create_session(sqlite_db, "Plan", "Ema", {}, 7)
    alex_id = join_session(sqlite_db, session_id, "Alex")
    beth_id = join_session(sqlite_db, session_id, "Beth")
    cast_vote(sqlite_db, session_id, alex_id, event_id, True)
    cast_vote(sqlite_db, session_id, beth_id, event_id, False)
    mapping = get_session_interested_participants_by_event(sqlite_db, session_id)
    assert mapping[event_id] == ["Alex"]


def test_get_session_interested_participants_by_event_empty_session(sqlite_db):
    """Empty session returns empty mapping."""
    session_id = create_session(sqlite_db, "Plan", "Ema", {}, 7)
    mapping = get_session_interested_participants_by_event(sqlite_db, session_id)
    assert mapping == {}


def test_session_with_no_votes_returns_empty_tallies(sqlite_db):
    """get_session_vote_tallies returns empty dict when no votes cast."""
    session_id = create_session(sqlite_db, "Plan", "Ema", {}, 7)
    tallies = get_session_vote_tallies(sqlite_db, session_id)
    assert tallies == {}


def test_vote_change_interested_to_not_interested(sqlite_db, sample_event):
    """cast_vote upsert: changing interested to False removes from tally."""
    event_id = upsert_event(sqlite_db, sample_event)
    session_id = create_session(sqlite_db, "Plan", "Ema", {}, 7)
    participant_id = join_session(sqlite_db, session_id, "Alex")
    cast_vote(sqlite_db, session_id, participant_id, event_id, True)
    assert get_session_vote_tallies(sqlite_db, session_id)[event_id] == 1
    cast_vote(sqlite_db, session_id, participant_id, event_id, False)
    assert event_id not in get_session_vote_tallies(sqlite_db, session_id)


def test_get_session_interested_participants_by_event_stable_ordering(
    sqlite_db, sample_event
):
    """Participant names are stably ordered by name within each event."""
    event_id = upsert_event(sqlite_db, sample_event)
    session_id = create_session(sqlite_db, "Plan", "Ema", {}, 7)
    charlie_id = join_session(sqlite_db, session_id, "Charlie")
    alex_id = join_session(sqlite_db, session_id, "Alex")
    beth_id = join_session(sqlite_db, session_id, "Beth")
    cast_vote(sqlite_db, session_id, charlie_id, event_id, True)
    cast_vote(sqlite_db, session_id, alex_id, event_id, True)
    cast_vote(sqlite_db, session_id, beth_id, event_id, True)
    mapping = get_session_interested_participants_by_event(sqlite_db, session_id)
    assert mapping[event_id] == ["Alex", "Beth", "Charlie"]
