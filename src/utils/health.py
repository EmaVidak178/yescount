from __future__ import annotations

from typing import Any


def liveness() -> dict[str, Any]:
    return {"ok": True}


def _database_ready(conn: Any) -> str:
    try:
        if hasattr(conn, "execute"):
            conn.execute("SELECT 1").fetchone()
        else:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        return "ready"
    except Exception as exc:
        return f"error: {exc}"


def readiness(conn: Any | None, chroma_collection: Any | None = None) -> dict[str, Any]:
    dependencies: dict[str, str] = {}
    if conn is None:
        dependencies["database"] = "error: unavailable"
    else:
        dependencies["database"] = _database_ready(conn)

    if chroma_collection is None:
        dependencies["chroma"] = "degraded: unavailable"
    else:
        try:
            # count() is a lightweight call that validates collection readiness.
            chroma_collection.count()
            dependencies["chroma"] = "ready"
        except Exception as exc:
            dependencies["chroma"] = f"degraded: {exc}"

    ok = dependencies["database"] == "ready"
    return {"ok": ok, "dependencies": dependencies}
