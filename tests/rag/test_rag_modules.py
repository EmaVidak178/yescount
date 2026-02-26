from __future__ import annotations

from types import SimpleNamespace

from src.db.sqlite_client import upsert_event
from src.rag.retriever import retrieve_events


class _FakeEmbeddings:
    def create(self, model, input):
        if isinstance(input, list):
            return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2]) for _ in input])
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])


class _FakeClient:
    embeddings = _FakeEmbeddings()


def test_retriever_falls_back_to_sql(sqlite_db, sample_event):
    upsert_event(sqlite_db, sample_event)
    rows = retrieve_events(sqlite_db, collection=None, client=None, query="sample")
    assert len(rows) == 1


def test_embed_batch_and_retrieve_with_fake_collection(sqlite_db, sample_event, mocker):
    upsert_event(sqlite_db, sample_event)
    mocker.patch("src.rag.retriever.query_events", return_value=[1])
    fake_collection = object()
    rows = retrieve_events(
        sqlite_db,
        collection=fake_collection,
        client=_FakeClient(),
        query="sample",
        vibe_tags=[],
    )
    assert rows[0]["id"] == 1
