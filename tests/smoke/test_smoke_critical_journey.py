from __future__ import annotations

import pytest

from src.db.sqlite_client import create_session, upsert_event
from src.engine.admin_rules import load_preferences
from src.engine.availability import get_group_availability, set_availability
from src.engine.recommender import compute_recommendations
from src.engine.voting import cast_vote, get_session_vote_tallies
from src.sessions.manager import get_session_url, join_session
from src.utils.invite_text import generate_invite


@pytest.mark.smoke
def test_critical_user_journey_module_level(sqlite_db, sample_event):
    event_id = upsert_event(sqlite_db, sample_event)
    session_id = create_session(
        sqlite_db,
        name="Friday Plan",
        created_by="Ema",
        admin_preferences={"vibe_tags": ["artsy"]},
        expiry_days=7,
    )
    participant_id = join_session(sqlite_db, session_id, "Alex")
    cast_vote(sqlite_db, session_id, participant_id, event_id, True)
    set_availability(sqlite_db, session_id, participant_id, [("2026-03-10", "19:00", "21:00")])
    tallies = get_session_vote_tallies(sqlite_db, session_id)
    overlap = get_group_availability(sqlite_db, session_id)
    overlap_by_event = {event_id: overlap["slots"][0]["overlap_score"] if overlap["slots"] else 0.0}
    recommendations = compute_recommendations(
        events=[{**sample_event, "id": event_id}],
        vote_tallies=tallies,
        overlap_by_event_id=overlap_by_event,
        prefs=load_preferences({"vibe_tags": ["artsy"]}),
        top_n=5,
    )
    invite = generate_invite(
        session_name="Friday Plan",
        connector_name="Ema",
        session_url=get_session_url("https://yescount.example", session_id),
        top_event=recommendations[0] if recommendations else None,
    )
    assert len(recommendations) == 1
    assert "Join here:" in invite
