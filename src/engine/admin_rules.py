from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdminPreferences:
    budget_cap: float | None = None
    vibe_tags: list[str] = field(default_factory=list)
    min_attendees: int = 1
    blackout_dates: list[str] = field(default_factory=list)
    date_range_start: str | None = None
    date_range_end: str | None = None


def load_preferences(payload: dict[str, Any] | None) -> AdminPreferences:
    payload = payload or {}
    return AdminPreferences(
        budget_cap=payload.get("budget_cap"),
        vibe_tags=payload.get("vibe_tags", []),
        min_attendees=int(payload.get("min_attendees", 1)),
        blackout_dates=payload.get("blackout_dates", []),
        date_range_start=payload.get("date_range_start"),
        date_range_end=payload.get("date_range_end"),
    )


def apply_hard_filters(
    events: list[dict[str, Any]], prefs: AdminPreferences
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for event in events:
        val = event.get("date_start")
        event_date = str(val)[:10] if val else ""
        if (
            prefs.budget_cap is not None
            and event.get("price_max") not in (None, "")
            and float(event["price_max"]) > prefs.budget_cap
        ):
            continue
        if event_date and event_date in set(prefs.blackout_dates):
            continue
        if prefs.date_range_start and event_date and event_date < prefs.date_range_start:
            continue
        if prefs.date_range_end and event_date and event_date > prefs.date_range_end:
            continue
        out.append(event)
    return out


def compute_admin_score(event: dict[str, Any], prefs: AdminPreferences) -> float:
    if not prefs.vibe_tags:
        return 0.0
    event_tags = set(
        str(event.get("vibe_tags", ""))
        .lower()
        .replace("[", "")
        .replace("]", "")
        .replace('"', "")
        .replace(" ", "")
        .split(",")
    )
    wanted = {tag.lower() for tag in prefs.vibe_tags}
    if not event_tags:
        return 0.0
    return len(event_tags.intersection(wanted)) / max(len(wanted), 1)
