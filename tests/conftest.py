from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest

from src.db.sqlite_client import get_connection, init_schema


@pytest.fixture
def sqlite_db(tmp_path: Path) -> Generator[sqlite3.Connection, None, None]:
    os.environ.pop("DATABASE_URL", None)
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def sample_event() -> dict[str, object]:
    return {
        "title": "Sample Event",
        "description": "Sample Description",
        "date_start": "2026-03-10T19:00:00+00:00",
        "date_end": None,
        "location": "NYC",
        "price_min": 10.0,
        "price_max": 20.0,
        "url": "https://example.com/event",
        "source": "scraped",
        "source_id": "sample-1",
        "raw_json": {"id": "sample-1"},
        "vibe_tags": ["artsy"],
    }
