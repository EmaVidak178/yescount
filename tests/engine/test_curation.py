"""Tests for event curation module."""

from __future__ import annotations

from src.engine.curation import (
    PRIORITY_KEYWORDS,
    curate_voting_events,
)


def test_filter_websites_only():
    events = [
        {"id": 1, "title": "A", "description": "x", "date_start": "2026-03-15", "source": "scraped"},
        {"id": 2, "title": "B", "description": "x", "date_start": "2026-03-16", "source": "nyc_open_data"},
    ]
    result = curate_voting_events(events, websites_only=True)
    assert len(result) == 1
    assert result[0]["source"] == "scraped"


def test_websites_only_false_includes_all():
    events = [
        {"id": 1, "title": "A", "description": "x", "date_start": "2026-03-15", "source": "scraped"},
        {"id": 2, "title": "B", "description": "x", "date_start": "2026-03-16", "source": "nyc_open_data"},
    ]
    result = curate_voting_events(events, websites_only=False)
    assert len(result) == 2


def test_filter_by_target_month():
    events = [
        {"id": 1, "title": "A", "description": "x", "date_start": "2026-03-15", "source": "scraped"},
        {"id": 2, "title": "B", "description": "x", "date_start": "2026-04-01", "source": "scraped"},
        {"id": 3, "title": "C", "description": "x", "date_start": "2026-02-28", "source": "scraped"},
    ]
    result = curate_voting_events(events, target_year=2026, target_month=3)
    assert len(result) == 1
    assert result[0]["id"] == 1


def test_filter_by_target_year_only():
    events = [
        {"id": 1, "title": "A", "description": "x", "date_start": "2026-03-15", "source": "scraped"},
        {"id": 2, "title": "B", "description": "x", "date_start": "2025-12-31", "source": "scraped"},
    ]
    result = curate_voting_events(events, target_year=2026)
    assert len(result) == 1
    assert result[0]["id"] == 1


def test_rank_by_quality_keywords():
    events = [
        {"id": 1, "title": "Generic event", "description": "Short", "date_start": "2026-03-15", "source": "scraped"},
        {"id": 2, "title": "Immersive theater pop-up", "description": "Festival exhibit", "date_start": "2026-03-16", "source": "scraped"},
    ]
    result = curate_voting_events(events)
    assert len(result) == 2
    assert result[0]["id"] == 2
    assert "immersive" in result[0]["title"].lower()


def test_rank_by_richness():
    events = [
        {"id": 1, "title": "X", "description": "", "date_start": "2026-03-15", "source": "scraped"},
        {"id": 2, "title": "Long descriptive title here", "description": "Detailed description with more context.", "date_start": "2026-03-16", "source": "scraped"},
    ]
    result = curate_voting_events(events)
    assert len(result) == 2
    assert result[0]["id"] == 2


def test_cap_at_top_n():
    events = [
        {"id": i, "title": "E", "description": "x", "date_start": "2026-03-15", "source": "scraped"}
        for i in range(50)
    ]
    result = curate_voting_events(events, top_n=30)
    assert len(result) == 30


def test_deterministic_ordering():
    events = [
        {"id": 3, "title": "Same", "description": "Same", "date_start": "2026-03-15", "source": "scraped"},
        {"id": 1, "title": "Same", "description": "Same", "date_start": "2026-03-15", "source": "scraped"},
        {"id": 2, "title": "Same", "description": "Same", "date_start": "2026-03-15", "source": "scraped"},
    ]
    result1 = curate_voting_events(events)
    result2 = curate_voting_events(events)
    assert [r["id"] for r in result1] == [r["id"] for r in result2]
    assert [r["id"] for r in result1] == [1, 2, 3]


def test_empty_input():
    assert curate_voting_events([]) == []


def test_no_matches_after_filter():
    events = [
        {"id": 1, "title": "A", "description": "x", "date_start": "2026-03-15", "source": "nyc_open_data"},
    ]
    result = curate_voting_events(events, websites_only=True)
    assert result == []


def test_priority_keywords_constant():
    assert "immersive" in PRIORITY_KEYWORDS
    assert "theater" in PRIORITY_KEYWORDS
    assert "festival" in PRIORITY_KEYWORDS
    assert "exhibit" in PRIORITY_KEYWORDS


def test_date_start_iso_format():
    events = [
        {"id": 1, "title": "A", "description": "x", "date_start": "2026-03-10T19:00:00+00:00", "source": "scraped"},
    ]
    result = curate_voting_events(events, target_year=2026, target_month=3)
    assert len(result) == 1


def test_invalid_date_start_filtered_out():
    """Events with invalid or missing date_start are excluded when target_month set."""
    events = [
        {"id": 1, "title": "A", "description": "x", "date_start": "not-a-date", "source": "scraped"},
        {"id": 2, "title": "B", "description": "x", "date_start": None, "source": "scraped"},
        {"id": 3, "title": "C", "description": "x", "date_start": "2026-03-15", "source": "scraped"},
    ]
    result = curate_voting_events(events, target_year=2026, target_month=3)
    assert len(result) == 1
    assert result[0]["id"] == 3


def test_missing_id_defaults_to_zero_in_sort():
    """Events without id use 0; deterministic ordering by id still works."""
    events = [
        {"id": 1, "title": "A", "description": "x", "date_start": "2026-03-15", "source": "scraped"},
        {"title": "Z", "description": "x", "date_start": "2026-03-15", "source": "scraped"},
    ]
    result = curate_voting_events(events)
    assert len(result) == 2
    # id=0 (missing) sorts before id=1, so Z comes first
    assert result[0]["title"] == "Z"


def test_fallback_to_upcoming_when_target_month_has_no_events():
    """When target month is empty, fallback returns upcoming websites-only events."""
    events = [
        {"id": 1, "title": "Feb event", "description": "x", "date_start": "2099-02-15", "source": "scraped"},
        {"id": 2, "title": "Apr event", "description": "x", "date_start": "2099-04-10", "source": "scraped"},
    ]
    result = curate_voting_events(events, target_year=2099, target_month=3, websites_only=True)
    assert len(result) == 2
    assert {row["id"] for row in result} == {1, 2}
