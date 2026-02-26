from __future__ import annotations

from typing import Any

import chromadb

COLLECTION_NAME = "event_embeddings"


def get_client(persist_dir: str) -> Any:
    return chromadb.PersistentClient(path=persist_dir)


def get_collection(client: Any, name: str = COLLECTION_NAME) -> Any:
    return client.get_or_create_collection(name=name)


def upsert_event_embedding(
    collection: Any,
    event_id: int,
    document: str,
    embedding: list[float],
    metadata: dict[str, Any],
) -> None:
    collection.upsert(
        ids=[f"event_{event_id}"],
        documents=[document],
        embeddings=[embedding],
        metadatas=[metadata],
    )


def query_events(
    collection: Any,
    query_embedding: list[float],
    n_results: int = 20,
    where: dict[str, Any] | None = None,
) -> list[int]:
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where or {},
    )
    ids = result.get("ids", [[]])[0]
    out: list[int] = []
    for value in ids:
        if isinstance(value, str) and value.startswith("event_"):
            out.append(int(value.split("_", 1)[1]))
    return out
