from __future__ import annotations

from typing import Any

from src.db.sqlite_client import (
    get_interested_participants_by_event,
    get_vote_tallies,
    row_to_dict,
    upsert_vote,
)


def _is_postgres_conn(conn: Any) -> bool:
    return bool(conn.__class__.__module__.startswith("psycopg"))


def _execute(conn: Any, sql: str, params: tuple[Any, ...]) -> Any:
    if _is_postgres_conn(conn):
        cur = conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        return cur
    return conn.execute(sql, params)


def cast_vote(
    conn: Any,
    session_id: str,
    participant_id: int,
    event_id: int,
    interested: bool,
) -> None:
    upsert_vote(conn, session_id, participant_id, event_id, interested)


def get_session_vote_tallies(conn: Any, session_id: str) -> dict[int, int]:
    return get_vote_tallies(conn, session_id)


def get_session_interested_participants_by_event(
    conn: Any, session_id: str
) -> dict[int, list[str]]:
    """Return mapping event_id -> [participant names] for interested votes in a session."""
    return get_interested_participants_by_event(conn, session_id)


def get_participant_votes(conn: Any, session_id: str, participant_id: int) -> list[dict[str, Any]]:
    rows = _execute(
        conn,
        """
        SELECT * FROM votes
        WHERE session_id = ? AND participant_id = ?
        ORDER BY created_at DESC
        """,
        (session_id, participant_id),
    ).fetchall()
    return [row_to_dict(row) for row in rows]
