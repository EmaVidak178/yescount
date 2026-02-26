from __future__ import annotations

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
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
        """
    )
    conn.commit()


def down(conn: sqlite3.Connection) -> None:
    conn.executescript("DROP TABLE IF EXISTS votes;")
    conn.commit()
