from __future__ import annotations

from src.engine.admin_rules import AdminPreferences
from src.engine.recommender import compute_recommendations


def test_compute_recommendations_orders_by_score():
    events = [
        {
            "id": 1,
            "title": "A",
            "date_start": "2026-03-01",
            "price_min": 10,
            "price_max": 20,
            "vibe_tags": "[]",
        },
        {
            "id": 2,
            "title": "B",
            "date_start": "2026-03-02",
            "price_min": 10,
            "price_max": 20,
            "vibe_tags": "[]",
        },
    ]
    recs = compute_recommendations(
        events=events,
        vote_tallies={1: 10, 2: 1},
        overlap_by_event_id={1: 1.0, 2: 0.1},
        prefs=AdminPreferences(),
        top_n=5,
    )
    assert recs[0]["id"] == 1
