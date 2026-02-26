from __future__ import annotations

import sqlite3
from typing import Any


def liveness() -> dict[str, Any]:
    return {"ok": True}


def readiness(conn: sqlite3.Connection, chroma_collection: Any | None = None) -> dict[str, Any]:
    dependencies: dict[str, str] = {}
    try:
        conn.execute("SELECT 1").fetchone()
        dependencies["sqlite"] = "ready"
    except sqlite3.Error as exc:
        dependencies["sqlite"] = f"error: {exc}"

    if chroma_collection is None:
        dependencies["chroma"] = "error: unavailable"
    else:
        try:
            # count() is a lightweight call that validates collection readiness.
            chroma_collection.count()
            dependencies["chroma"] = "ready"
        except Exception as exc:
            dependencies["chroma"] = f"error: {exc}"

    ok = all(value == "ready" for value in dependencies.values())
    return {"ok": ok, "dependencies": dependencies}
