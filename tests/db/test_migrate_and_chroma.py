from __future__ import annotations

from pathlib import Path

from src.db.chroma_client import COLLECTION_NAME, get_collection
from src.db.migrate import apply_all
from src.db.sqlite_client import get_connection


def test_apply_all_creates_migrations_table(tmp_path: Path):
    db_path = str(tmp_path / "migrate.db")
    apply_all(db_path)
    conn = get_connection(db_path)
    row = conn.execute("SELECT COUNT(*) AS c FROM _migrations").fetchone()
    assert int(row["c"]) >= 1


def test_chroma_collection_creation(tmp_path: Path):
    from src.db.chroma_client import get_client

    client = get_client(str(tmp_path / "chroma"))
    collection = get_collection(client, COLLECTION_NAME)
    assert collection is not None
