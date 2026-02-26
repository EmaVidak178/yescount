from __future__ import annotations

from typing import Any

from src.engine.admin_rules import AdminPreferences, apply_hard_filters, compute_admin_score


def compute_recommendations(
    events: list[dict[str, Any]],
    vote_tallies: dict[int, int],
    overlap_by_event_id: dict[int, float],
    prefs: AdminPreferences,
    w_interest: float = 0.4,
    w_overlap: float = 0.4,
    w_admin: float = 0.2,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    filtered = apply_hard_filters(events, prefs)
    max_votes = max(vote_tallies.values(), default=1)
    ranked: list[dict[str, Any]] = []
    for event in filtered:
        event_id = int(event["id"])
        interest_score = vote_tallies.get(event_id, 0) / max_votes
        overlap_score = overlap_by_event_id.get(event_id, 0.0)
        admin_score = compute_admin_score(event, prefs)
        composite = (
            (w_interest * interest_score) + (w_overlap * overlap_score) + (w_admin * admin_score)
        )
        ranked.append(
            {
                **event,
                "interest_score": interest_score,
                "overlap_score": overlap_score,
                "admin_score": admin_score,
                "composite_score": composite,
            }
        )
    ranked.sort(
        key=lambda e: (
            -e["composite_score"],
            -e["overlap_score"],
            float(e["price_min"] or 0.0),
            str(e["date_start"]),
        )
    )
    return ranked[:top_n]
