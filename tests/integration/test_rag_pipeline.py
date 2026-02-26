from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.db.sqlite_client import upsert_event
from src.rag.retriever import retrieve_events


class _FakeEmbeddings:
    def create(self, model, input):
        if isinstance(input, list):
            return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2]) for _ in input])
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])


class _FakeClient:
    embeddings = _FakeEmbeddings()


@pytest.mark.integration
def test_rag_pipeline_vector_path_returns_ranked_rows(sqlite_db, sample_event, mocker):
    upsert_event(sqlite_db, sample_event)
    mocker.patch("src.rag.retriever.query_events", return_value=[1])
    rows = retrieve_events(
        conn=sqlite_db,
        collection=object(),
        client=_FakeClient(),
        query="sample event",
        date_start="2026-01-01",
        date_end="2026-12-31",
        price_max=50.0,
        vibe_tags=[],
    )
    assert len(rows) == 1
    assert int(rows[0]["id"]) == 1


@pytest.mark.integration
def test_rag_pipeline_falls_back_when_vector_path_errors(sqlite_db, sample_event, mocker):
    upsert_event(sqlite_db, sample_event)
    mocker.patch("src.rag.retriever.query_events", side_effect=RuntimeError("chroma unavailable"))
    rows = retrieve_events(
        conn=sqlite_db,
        collection=object(),
        client=_FakeClient(),
        query="Sample",
        date_start=None,
        date_end=None,
        price_max=None,
        vibe_tags=None,
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "Sample Event"
