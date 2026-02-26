from __future__ import annotations

from src.db.sqlite_client import create_session
from src.sessions.manager import join_session, validate_participant_name


def test_validate_participant_name():
    assert validate_participant_name("Alex-1") is None
    assert validate_participant_name("") is not None


def test_join_session(sqlite_db):
    session_id = create_session(
        sqlite_db,
        name="Weekend Plan",
        created_by="Connector",
        admin_preferences={},
        expiry_days=7,
    )
    participant_id = join_session(sqlite_db, session_id, "Alex")
    assert participant_id > 0
