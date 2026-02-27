from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.db.sqlite_client import create_session
from src.sessions.manager import is_session_valid, join_session, validate_participant_name


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


def test_is_session_valid_accepts_datetime_value(mocker):
    future = datetime.now(UTC) + timedelta(days=1)
    mocker.patch(
        "src.sessions.manager.get_session",
        return_value={"status": "open", "expires_at": future},
    )
    assert is_session_valid(conn=object(), session_id="abc") is True
