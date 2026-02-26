from __future__ import annotations

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
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
        """
    )
    conn.commit()


def down(conn: sqlite3.Connection) -> None:
    conn.executescript("DROP TABLE IF EXISTS events;")
    conn.commit()
