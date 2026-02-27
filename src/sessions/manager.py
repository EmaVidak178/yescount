from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from src.db.sqlite_client import (
    create_or_get_participant,
    create_session,
    get_participants,
    get_session,
    normalize_name,
    update_session_status,
)

NAME_PATTERN = re.compile(r"^[A-Za-z0-9 '\-]{1,50}$")


def _is_postgres_conn(conn: Any) -> bool:
    return bool(conn.__class__.__module__.startswith("psycopg"))


def _execute(conn: Any, sql: str, params: tuple[Any, ...]) -> Any:
    if _is_postgres_conn(conn):
        cur = conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        return cur
    return conn.execute(sql, params)


def _parse_expires_at(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def validate_participant_name(name: str) -> str | None:
    cleaned = " ".join(name.strip().split())
    if not cleaned:
        return "Name is required."
    if len(cleaned) > 50:
        return "Name must be at most 50 characters."
    if not NAME_PATTERN.match(cleaned):
        return "Use letters, numbers, spaces, apostrophes, or hyphens only."
    return None


def is_session_valid(conn: Any, session_id: str) -> bool:
    session = get_session(conn, session_id)
    if not session:
        return False
    if session["status"] == "archived":
        return False
    expires_at = _parse_expires_at(session.get("expires_at"))
    if expires_at is None:
        return False
    return datetime.now(UTC) < expires_at


def create_new_session(
    conn: Any,
    name: str,
    created_by: str,
    admin_preferences: dict[str, Any],
    expiry_days: int,
) -> str:
    return create_session(
        conn,
        name=name,
        created_by=created_by,
        admin_preferences=admin_preferences,
        expiry_days=expiry_days,
    )


def join_session(conn: Any, session_id: str, participant_name: str) -> int:
    if not is_session_valid(conn, session_id):
        raise ValueError("Session is invalid or expired.")
    session = get_session(conn, session_id)
    if session and session["status"] == "locked":
        raise ValueError("Session is locked.")
    error = validate_participant_name(participant_name)
    if error:
        raise ValueError(error)
    participants = get_participants(conn, session_id)
    normalized = normalize_name(participant_name)
    exists = next((p for p in participants if p["name_normalized"] == normalized), None)
    if exists:
        return int(exists["id"])
    if len(participants) >= 10:
        raise ValueError("Session is full.")
    return create_or_get_participant(conn, session_id, participant_name)


def lock_session(conn: Any, session_id: str, actor_name: str) -> bool:
    session = get_session(conn, session_id)
    if not session:
        return False
    if normalize_name(session["created_by"]) != normalize_name(actor_name):
        return False
    if session["status"] != "open":
        return False
    return update_session_status(conn, session_id, "locked")


def archive_session(conn: Any, session_id: str) -> bool:
    return update_session_status(conn, session_id, "archived")


def get_session_preview(conn: Any, session_id: str) -> dict[str, Any] | None:
    session = get_session(conn, session_id)
    if not session:
        return None
    participants = get_participants(conn, session_id)
    top_events = _execute(
        conn,
        """
        SELECT e.title, COUNT(*) as vote_count
        FROM votes v
        JOIN events e ON v.event_id = e.id
        WHERE v.session_id = ? AND v.interested = 1
        GROUP BY v.event_id, e.id, e.title
        ORDER BY vote_count DESC
        LIMIT 3
        """,
        (session_id,),
    ).fetchall()
    return {
        "session": session,
        "participants": [p["name"] for p in participants],
        "top_events": [
            {"title": row["title"], "vote_count": int(row["vote_count"])} for row in top_events
        ],
    }


def get_session_url(base_url: str, session_id: str) -> str:
    return f"{base_url}?session={session_id}"
