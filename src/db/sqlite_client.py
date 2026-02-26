from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    date_start TEXT NOT NULL,
    date_end TEXT,
    location TEXT NOT NULL DEFAULT '',
    price_min REAL,
    price_max REAL,
    url TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL CHECK(source IN ('nyc_open_data', 'scraped')),
    source_id TEXT,
    raw_json TEXT,
    vibe_tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_events_date_start ON events(date_start);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_by TEXT NOT NULL,
    admin_preferences_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'locked', 'archived')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    name_normalized TEXT NOT NULL,
    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, name_normalized)
);

CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    interested INTEGER NOT NULL CHECK(interested IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, participant_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_votes_session ON votes(session_id);
CREATE INDEX IF NOT EXISTS idx_votes_event ON votes(session_id, event_id);

CREATE TABLE IF NOT EXISTS availability_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    time_start TEXT NOT NULL,
    time_end TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, participant_id, date, time_start, time_end)
);

CREATE INDEX IF NOT EXISTS idx_availability_session ON availability_slots(session_id);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('running', 'success', 'degraded', 'failed')),
    total_events_upserted INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_started_at ON ingestion_runs(started_at);

CREATE TABLE IF NOT EXISTS ingestion_source_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES ingestion_runs(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    required INTEGER NOT NULL CHECK(required IN (0,1)),
    status TEXT NOT NULL CHECK(status IN ('success', 'partial', 'failed', 'skipped')),
    events_found INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_ingestion_source_checks_run ON ingestion_source_checks(run_id);
"""

POSTGRES_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS events (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        date_start TIMESTAMPTZ NOT NULL,
        date_end TIMESTAMPTZ,
        location TEXT NOT NULL DEFAULT '',
        price_min DOUBLE PRECISION,
        price_max DOUBLE PRECISION,
        url TEXT NOT NULL DEFAULT '',
        source TEXT NOT NULL CHECK(source IN ('nyc_open_data', 'scraped')),
        source_id TEXT,
        raw_json TEXT,
        vibe_tags TEXT NOT NULL DEFAULT '[]',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source, source_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_events_date_start ON events(date_start)",
    "CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)",
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_by TEXT NOT NULL,
        admin_preferences_json TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'locked', 'archived')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS participants (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        name_normalized TEXT NOT NULL,
        joined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(session_id, name_normalized)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS votes (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        participant_id BIGINT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
        interested INTEGER NOT NULL CHECK(interested IN (0,1)),
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(session_id, participant_id, event_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_votes_session ON votes(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_votes_event ON votes(session_id, event_id)",
    """
    CREATE TABLE IF NOT EXISTS availability_slots (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        participant_id BIGINT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        date DATE NOT NULL,
        time_start TEXT NOT NULL,
        time_end TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(session_id, participant_id, date, time_start, time_end)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_availability_session ON availability_slots(session_id)",
    """
    CREATE TABLE IF NOT EXISTS ingestion_runs (
        id BIGSERIAL PRIMARY KEY,
        started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMPTZ,
        status TEXT NOT NULL CHECK(status IN ('running', 'success', 'degraded', 'failed')),
        total_events_upserted INTEGER NOT NULL DEFAULT 0,
        error_summary TEXT NOT NULL DEFAULT ''
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ingestion_runs_started_at ON ingestion_runs(started_at)",
    """
    CREATE TABLE IF NOT EXISTS ingestion_source_checks (
        id BIGSERIAL PRIMARY KEY,
        run_id BIGINT NOT NULL REFERENCES ingestion_runs(id) ON DELETE CASCADE,
        source_name TEXT NOT NULL,
        source_url TEXT NOT NULL,
        required INTEGER NOT NULL CHECK(required IN (0,1)),
        status TEXT NOT NULL CHECK(status IN ('success', 'partial', 'failed', 'skipped')),
        events_found INTEGER NOT NULL DEFAULT 0,
        error TEXT NOT NULL DEFAULT ''
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ingestion_source_checks_run ON ingestion_source_checks(run_id)",
]


def _is_postgres(conn: Any) -> bool:
    return conn.__class__.__module__.startswith("psycopg")


def _now_expr(conn: Any) -> str:
    return "CURRENT_TIMESTAMP" if _is_postgres(conn) else "datetime('now')"


def _adapt_sql(conn: Any, sql: str) -> str:
    return sql.replace("?", "%s") if _is_postgres(conn) else sql


def _execute(conn: Any, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> Any:
    if _is_postgres(conn):
        cur = conn.cursor()
        cur.execute(_adapt_sql(conn, sql), tuple(params))
        return cur
    return conn.execute(_adapt_sql(conn, sql), tuple(params))


def _executemany(conn: Any, sql: str, params_seq: list[tuple[Any, ...]]) -> Any:
    if _is_postgres(conn):
        cur = conn.cursor()
        cur.executemany(_adapt_sql(conn, sql), params_seq)
        return cur
    return conn.executemany(_adapt_sql(conn, sql), params_seq)


def _to_dict(row: Any) -> dict[str, Any]:
    return row if isinstance(row, dict) else dict(row)


def get_connection(db_path: str) -> Any:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        from psycopg import connect
        from psycopg.rows import dict_row

        return connect(database_url, row_factory=dict_row, autocommit=False)

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_schema(conn: Any) -> None:
    if _is_postgres(conn):
        cur = conn.cursor()
        for statement in POSTGRES_SCHEMA_STATEMENTS:
            cur.execute(statement)
    else:
        conn.executescript(SQLITE_SCHEMA)
    conn.commit()


def upsert_event(conn: Any, event: dict[str, Any]) -> int:
    now_sql = _now_expr(conn)
    _execute(
        conn,
        f"""
        INSERT INTO events (
            title, description, date_start, date_end, location, price_min, price_max, url,
            source, source_id, raw_json, vibe_tags, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {now_sql})
        ON CONFLICT(source, source_id) DO UPDATE SET
            title=excluded.title,
            description=excluded.description,
            date_start=excluded.date_start,
            date_end=excluded.date_end,
            location=excluded.location,
            price_min=excluded.price_min,
            price_max=excluded.price_max,
            url=excluded.url,
            raw_json=excluded.raw_json,
            vibe_tags=excluded.vibe_tags,
            updated_at={now_sql}
        """,
        [
            event["title"],
            event.get("description", ""),
            event["date_start"],
            event.get("date_end"),
            event.get("location", ""),
            event.get("price_min"),
            event.get("price_max"),
            event.get("url", ""),
            event["source"],
            event.get("source_id"),
            json.dumps(event.get("raw_json", {})),
            json.dumps(event.get("vibe_tags", [])),
        ],
    )
    row = _execute(
        conn,
        "SELECT id FROM events WHERE source = ? AND source_id = ?",
        [event["source"], event.get("source_id")],
    ).fetchone()
    conn.commit()
    return int(_to_dict(row)["id"])


def get_events(
    conn: Any,
    query: str = "",
    date_start: str | None = None,
    date_end: str | None = None,
    price_max: float | None = None,
    vibe_tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM events WHERE 1=1"
    params: list[Any] = []
    if query.strip():
        sql += " AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
        pattern = f"%{query.strip()}%"
        params.extend([pattern, pattern, pattern])
    if date_start:
        if _is_postgres(conn):
            sql += " AND date_start >= ?::timestamptz"
        else:
            sql += " AND date(date_start) >= date(?)"
        params.append(date_start)
    if date_end:
        if _is_postgres(conn):
            sql += " AND date_start <= ?::timestamptz"
        else:
            sql += " AND date(date_start) <= date(?)"
        params.append(date_end)
    if price_max is not None:
        sql += " AND (price_max IS NULL OR price_max <= ?)"
        params.append(price_max)
    sql += " ORDER BY date_start ASC LIMIT 500"
    rows = [_to_dict(row) for row in _execute(conn, sql, params).fetchall()]
    if vibe_tags:
        wanted = {tag.lower() for tag in vibe_tags}
        rows = [
            row
            for row in rows
            if wanted.intersection({tag.lower() for tag in json.loads(row.get("vibe_tags", "[]"))})
        ]
    return rows


def create_session(
    conn: Any,
    name: str,
    created_by: str,
    admin_preferences: dict[str, Any],
    expiry_days: int = 7,
) -> str:
    session_id = str(uuid.uuid4())
    expires_at = (datetime.now(UTC) + timedelta(days=expiry_days)).isoformat()
    _execute(
        conn,
        """
        INSERT INTO sessions (id, name, created_by, admin_preferences_json, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [session_id, name, created_by, json.dumps(admin_preferences), expires_at],
    )
    conn.commit()
    return session_id


def get_session(conn: Any, session_id: str) -> dict[str, Any] | None:
    row = _execute(conn, "SELECT * FROM sessions WHERE id = ?", [session_id]).fetchone()
    return _to_dict(row) if row else None


def update_session_status(conn: Any, session_id: str, status: str) -> bool:
    cur = _execute(
        conn,
        "UPDATE sessions SET status = ? WHERE id = ?",
        [status, session_id],
    )
    conn.commit()
    return cur.rowcount > 0


def create_or_get_participant(conn: Any, session_id: str, name: str) -> int:
    normalized = normalize_name(name)
    row = _execute(
        conn,
        "SELECT id FROM participants WHERE session_id = ? AND name_normalized = ?",
        [session_id, normalized],
    ).fetchone()
    if row:
        return int(_to_dict(row)["id"])
    _execute(
        conn,
        """
        INSERT INTO participants (session_id, name, name_normalized)
        VALUES (?, ?, ?)
        """,
        [session_id, name.strip(), normalized],
    )
    row2 = _execute(
        conn,
        "SELECT id FROM participants WHERE session_id = ? AND name_normalized = ?",
        [session_id, normalized],
    ).fetchone()
    conn.commit()
    return int(_to_dict(row2)["id"])


def get_participants(conn: Any, session_id: str) -> list[dict[str, Any]]:
    rows = _execute(
        conn,
        "SELECT * FROM participants WHERE session_id = ? ORDER BY joined_at ASC",
        [session_id],
    ).fetchall()
    return [_to_dict(row) for row in rows]


def upsert_vote(
    conn: Any,
    session_id: str,
    participant_id: int,
    event_id: int,
    interested: bool,
) -> None:
    now_sql = _now_expr(conn)
    _execute(
        conn,
        f"""
        INSERT INTO votes (session_id, participant_id, event_id, interested)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(session_id, participant_id, event_id)
        DO UPDATE SET interested = excluded.interested, created_at = {now_sql}
        """,
        [session_id, participant_id, event_id, 1 if interested else 0],
    )
    conn.commit()


def get_vote_tallies(conn: Any, session_id: str) -> dict[int, int]:
    rows = _execute(
        conn,
        """
        SELECT event_id, COUNT(*) as votes_yes
        FROM votes
        WHERE session_id = ? AND interested = 1
        GROUP BY event_id
        """,
        [session_id],
    ).fetchall()
    return {int(_to_dict(row)["event_id"]): int(_to_dict(row)["votes_yes"]) for row in rows}


def replace_availability(
    conn: Any,
    session_id: str,
    participant_id: int,
    slots: list[tuple[str, str, str]],
) -> None:
    _execute(
        conn,
        "DELETE FROM availability_slots WHERE session_id = ? AND participant_id = ?",
        [session_id, participant_id],
    )
    _executemany(
        conn,
        """
        INSERT INTO availability_slots (session_id, participant_id, date, time_start, time_end)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(session_id, participant_id, d, s, e) for d, s, e in slots],
    )
    conn.commit()


def get_availability(conn: Any, session_id: str) -> list[dict[str, Any]]:
    rows = _execute(
        conn,
        "SELECT * FROM availability_slots WHERE session_id = ?",
        [session_id],
    ).fetchall()
    return [_to_dict(row) for row in rows]


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split()).lower()


def create_ingestion_run(conn: Any) -> int:
    if _is_postgres(conn):
        row = _execute(
            conn, "INSERT INTO ingestion_runs (status) VALUES ('running') RETURNING id"
        ).fetchone()
    else:
        _execute(conn, "INSERT INTO ingestion_runs (status) VALUES ('running')")
        row = _execute(conn, "SELECT last_insert_rowid() AS id").fetchone()
    conn.commit()
    return int(_to_dict(row)["id"])


def finalize_ingestion_run(
    conn: Any,
    run_id: int,
    status: str,
    total_events_upserted: int,
    error_summary: str = "",
) -> None:
    now_sql = _now_expr(conn)
    _execute(
        conn,
        f"""
        UPDATE ingestion_runs
        SET status = ?, total_events_upserted = ?, error_summary = ?, finished_at = {now_sql}
        WHERE id = ?
        """,
        [status, total_events_upserted, error_summary[:1000], run_id],
    )
    conn.commit()


def record_ingestion_source_check(
    conn: Any,
    run_id: int,
    source_name: str,
    source_url: str,
    required: bool,
    status: str,
    events_found: int,
    error: str = "",
) -> None:
    _execute(
        conn,
        """
        INSERT INTO ingestion_source_checks (
            run_id, source_name, source_url, required, status, events_found, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            source_name,
            source_url,
            1 if required else 0,
            status,
            max(events_found, 0),
            error[:1000],
        ],
    )
    conn.commit()


def latest_successful_ingestion_run(conn: Any) -> dict[str, Any] | None:
    row = _execute(
        conn,
        """
        SELECT *
        FROM ingestion_runs
        WHERE status IN ('success', 'degraded')
        ORDER BY id DESC
        LIMIT 1
        """,
    ).fetchone()
    return _to_dict(row) if row else None
