from __future__ import annotations

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
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
        """
    )
    conn.commit()


def down(conn: sqlite3.Connection) -> None:
    conn.executescript("DROP TABLE IF EXISTS availability_slots;")
    conn.commit()
