from __future__ import annotations

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_by TEXT NOT NULL,
            admin_preferences_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'locked', 'archived')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def down(conn: sqlite3.Connection) -> None:
    conn.executescript("DROP TABLE IF EXISTS sessions;")
    conn.commit()
