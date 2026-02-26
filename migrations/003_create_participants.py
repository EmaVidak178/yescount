from __future__ import annotations

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            name_normalized TEXT NOT NULL,
            joined_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(session_id, name_normalized)
        );
        """
    )
    conn.commit()


def down(conn: sqlite3.Connection) -> None:
    conn.executescript("DROP TABLE IF EXISTS participants;")
    conn.commit()
