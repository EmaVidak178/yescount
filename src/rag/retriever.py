from __future__ import annotations

from typing import Any

import openai
from chromadb.api.models.Collection import Collection
from openai import OpenAI

from src.db.chroma_client import query_events
from src.db.sqlite_client import get_events, row_to_dict
from src.rag.embedder import embed_text


def _is_postgres_conn(conn: Any) -> bool:
    return bool(conn.__class__.__module__.startswith("psycopg"))


def _execute(conn: Any, sql: str, params: list[Any]) -> Any:
    if _is_postgres_conn(conn):
        cur = conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        return cur
    return conn.execute(sql, params)


def _where_clause(
    date_start: str | None, date_end: str | None, price_max: float | None
) -> dict[str, Any]:
    where: dict[str, Any] = {}
    if date_start:
        where["date_start"] = {"$gte": date_start}
    if date_end:
        where["date_start"] = (
            {"$lte": date_end}
            if "date_start" not in where
            else {
                "$and": [{"date_start": {"$gte": date_start}}, {"date_start": {"$lte": date_end}}]
            }
        )
    if price_max is not None:
        where["price_max"] = {"$lte": price_max}
    return where


def retrieve_events(
    conn: Any,
    collection: Collection | None,
    client: OpenAI | None,
    query: str = "",
    date_start: str | None = None,
    date_end: str | None = None,
    price_max: float | None = None,
    vibe_tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    # Context7 best practice: graceful fallback when vector or API path fails.
    if collection is None or client is None or not query.strip():
        return get_events(conn, query, date_start, date_end, price_max, vibe_tags)

    try:
        query_embedding = embed_text(client, query.strip())
        event_ids = query_events(
            collection,
            query_embedding=query_embedding,
            where=_where_clause(date_start, date_end, price_max),
        )
        if not event_ids:
            return []
        placeholders = ",".join(["?"] * len(event_ids))
        rows = _execute(
            conn,
            f"SELECT * FROM events WHERE id IN ({placeholders})",
            event_ids,
        ).fetchall()
        by_id = {row["id"]: row_to_dict(row) for row in rows}
        ordered = [by_id[event_id] for event_id in event_ids if event_id in by_id]
        if vibe_tags:
            wanted = {tag.lower() for tag in vibe_tags}
            return [
                row
                for row in ordered
                if wanted.intersection(
                    set(
                        (row.get("vibe_tags") or "")
                        .lower()
                        .replace("[", "")
                        .replace("]", "")
                        .replace('"', "")
                        .replace(" ", "")
                        .split(",")
                    )
                )
            ]
        return ordered
    except (openai.APIError, Exception):
        return get_events(conn, query, date_start, date_end, price_max, vibe_tags)
