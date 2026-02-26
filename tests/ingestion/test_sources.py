from __future__ import annotations

from unittest.mock import patch

import requests

from src.ingestion.nyc_open_data import normalize_events
from src.ingestion.web_scraper import normalize_scraped_events, scrape_all


@patch("src.ingestion.web_scraper.scrape_site")
def test_scrape_all_handles_partial_failures(mock_scrape):
    mock_scrape.side_effect = [[{"title": "A"}], requests.RequestException("boom")]
    out = scrape_all(["https://a.example", "https://b.example"])
    assert len(out) == 1


def test_normalize_helpers():
    events = normalize_events([{"event_name": "A", "start_date_time": "2026-01-01"}])
    assert events[0]["source"] == "nyc_open_data"
    scraped = normalize_scraped_events([{"title": "B", "date_start": "2026-01-02"}])
    assert scraped[0]["source"] == "scraped"
