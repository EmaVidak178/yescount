from __future__ import annotations

import pytest

from src.db.sqlite_client import create_session
from src.sessions.manager import join_session, lock_session


@pytest.mark.integration
def test_duplicate_join_returns_same_participant_id(sqlite_db):
    session_id = create_session(
        sqlite_db,
        name="Crew Night",
        created_by="Ema",
        admin_preferences={},
        expiry_days=7,
    )
    participant_a = join_session(sqlite_db, session_id, " Alex ")
    participant_b = join_session(sqlite_db, session_id, "alex")
    assert participant_a == participant_b


@pytest.mark.integration
def test_lock_is_single_transition_and_blocks_repeated_locks(sqlite_db):
    session_id = create_session(
        sqlite_db,
        name="Crew Night",
        created_by="Ema",
        admin_preferences={},
        expiry_days=7,
    )
    first = lock_session(sqlite_db, session_id, actor_name="Ema")
    second = lock_session(sqlite_db, session_id, actor_name="Ema")
    assert first is True
    assert second is False
