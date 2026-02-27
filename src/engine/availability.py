from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.db.sqlite_client import get_availability, replace_availability


def _is_postgres_conn(conn: Any) -> bool:
    return bool(conn.__class__.__module__.startswith("psycopg"))


def _execute(conn: Any, sql: str, params: tuple[Any, ...]) -> Any:
    if _is_postgres_conn(conn):
        cur = conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        return cur
    return conn.execute(sql, params)


def set_availability(
    conn: Any,
    session_id: str,
    participant_id: int,
    slots: list[tuple[str, str, str]],
) -> None:
    replace_availability(conn, session_id, participant_id, slots)


def get_group_availability(conn: Any, session_id: str) -> dict[str, Any]:
    participants = _execute(
        conn,
        "SELECT id, name FROM participants WHERE session_id = ?",
        (session_id,),
    ).fetchall()
    participant_count = max(len(participants), 1)
    slots = get_availability(conn, session_id)
    grouped: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for row in slots:
        key = (row["date"], row["time_start"], row["time_end"])
        grouped[key].append(int(row["participant_id"]))
    return {
        "participant_count": len(participants),
        "slots": [
            {
                "date": date,
                "time_start": time_start,
                "time_end": time_end,
                "participant_ids": ids,
                "overlap_score": len(ids) / participant_count,
            }
            for (date, time_start, time_end), ids in grouped.items()
        ],
    }
