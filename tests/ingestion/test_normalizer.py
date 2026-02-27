from __future__ import annotations

from src.ingestion.normalizer import (
    extract_vibe_tags,
    normalize_nyc_open_data,
    normalize_scraped,
    parse_date,
    parse_price,
)


def test_parse_price_and_free():
    assert parse_price("Free") == (0.0, 0.0)
    assert parse_price("$10-$25") == (10.0, 25.0)
    assert parse_price("$15") == (15.0, 15.0)


def test_parse_date_and_vibes():
    value = parse_date("2026-03-10 19:00")
    assert value is not None
    tags = extract_vibe_tags("Interactive art museum in a park")
    assert "immersive" in tags
    assert "artsy" in tags


def test_normalize_nyc_event():
    raw = {
        "event_name": "Sample",
        "description": "Outdoor event",
        "start_date_time": "2026-03-10T19:00:00Z",
        "event_url": "https://example.com",
        "event_id": "abc1",
    }
    normalized = normalize_nyc_open_data(raw)
    assert normalized["title"] == "Sample"
    assert normalized["source"] == "nyc_open_data"


def test_normalize_scraped_uses_none_for_missing_date():
    raw = {
        "title": "Untimed Event",
        "description": "No date provided",
        "date_start": "",
        "source_id": "missing-date",
    }
    normalized = normalize_scraped(raw)
    assert normalized["date_start"] is None
