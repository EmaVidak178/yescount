"""Event curation for UI voting list.

Filters and ranks events for websites-only mode with quality heuristics.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

PRIORITY_KEYWORDS = frozenset(
    {"immersive", "theater", "theatre", "pop-up", "popup", "exhibit", "festival"}
)
# Content that suggests NOT an event (news, guides, closures, lists)
NON_EVENT_KEYWORDS = frozenset(
    {
        "cheapest",
        "closure",
        "closed",
        "closing",
        "permanently closed",
        "news",
        "article",
        "report",
        "roundup",
        "guide to",
        "best bakery",
        "best restaurant",
        "best bars",
        "best things",
        "permanently shut",
        "shut down",
        "going out of business",
        "list of",
        "top 10",
        "top 15",
        "top 20",
        "things to know",
    }
)
DEFAULT_TOP_N = 30


def _parse_date_start(value: Any) -> datetime | None:
    """Parse date_start to datetime; return None if invalid."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    # Extract date part (YYYY-MM-DD) for reliable parsing
    date_part = s[:10] if len(s) >= 10 else s
    try:
        return datetime.strptime(date_part, "%Y-%m-%d")
    except ValueError:
        return None


def _richness_score(event: dict[str, Any]) -> float:
    """Score title + description richness (length and non-empty)."""
    title = (event.get("title") or "").strip()
    desc = (event.get("description") or "").strip()
    # Normalize: longer meaningful text = higher score
    title_len = len(title)
    desc_len = len(desc)
    return min(title_len * 0.5 + desc_len * 0.3, 50.0)


def _keyword_score(event: dict[str, Any]) -> float:
    """Score presence of priority keywords in title + description."""
    title = (event.get("title") or "").lower()
    desc = (event.get("description") or "").lower()
    text = f"{title} {desc}"
    hits = sum(1 for kw in PRIORITY_KEYWORDS if kw in text)
    return min(hits * 10.0, 30.0)


def _quality_score(event: dict[str, Any]) -> float:
    """Combined quality heuristic: richness + priority keywords."""
    return _richness_score(event) + _keyword_score(event)


def _looks_like_event(event: dict[str, Any]) -> bool:
    """Return False if content suggests a non-event (news, guide, closure, etc.)."""
    title = (event.get("title") or "").lower()
    desc = (event.get("description") or "").lower()
    text = f"{title} {desc}"
    if any(kw in text for kw in NON_EVENT_KEYWORDS):
        return False
    # Filter generic roundup/listicle records that often represent multiple events.
    if "things to do" in title or "happenings" in title or "you can't miss" in title:
        return False
    if "top " in title and any(ch.isdigit() for ch in title):
        return False
    return not ("best " in title and any(ch.isdigit() for ch in title))


def _in_target_month(dt: datetime | None, year: int | None, month: int | None) -> bool:
    """Return True if dt falls in target year/month (or if no filter)."""
    if dt is None:
        return False
    if year is None and month is None:
        return True
    if year is not None and dt.year != year:
        return False
    return not (month is not None and dt.month != month)


def curate_voting_events(
    events: list[dict[str, Any]],
    *,
    target_year: int | None = None,
    target_month: int | None = None,
    websites_only: bool = True,
    top_n: int = DEFAULT_TOP_N,
) -> list[dict[str, Any]]:
    """Filter and rank events for UI voting list.

    - Filter for websites-only mode (source == 'scraped') when websites_only=True.
    - Filter by target month when target_year/target_month are set.
    - Rank by quality heuristics (title/description richness + priority keywords).
    - Cap results at top_n (default 30).
    - Return stable deterministic ordering (quality desc, then id asc, then date_start asc).

    Args:
        events: Raw event dicts with id, title, description, date_start, source.
        target_year: Optional year to filter (e.g. 2026).
        target_month: Optional month 1-12 to filter.
        websites_only: If True, keep only source == 'scraped'.
        top_n: Maximum number of events to return.

    Returns:
        Sorted list of top events, capped at top_n.
    """
    website_events: list[dict[str, Any]] = []
    for ev in events:
        if websites_only and ev.get("source") != "scraped":
            continue
        website_events.append(ev)

    filtered: list[dict[str, Any]] = []
    for ev in website_events:
        if not _looks_like_event(ev):
            continue
        dt = _parse_date_start(ev.get("date_start"))
        if _in_target_month(dt, target_year, target_month):
            filtered.append(ev)

    # If target-month filter is too strict and returns no events, fall back to upcoming
    # websites-only events so users can still vote instead of seeing an empty page.
    if not filtered and (target_year is not None or target_month is not None):
        now_date = datetime.now(UTC).date()
        upcoming = []
        for ev in website_events:
            if not _looks_like_event(ev):
                continue
            dt = _parse_date_start(ev.get("date_start"))
            if dt is not None and dt.date() >= now_date:
                upcoming.append(ev)
        filtered = upcoming if upcoming else [e for e in website_events if _looks_like_event(e)]

    def sort_key(e: dict[str, Any]) -> tuple[float, int, str]:
        q = -_quality_score(e)  # negate for descending
        eid = int(e.get("id") or 0)
        ds = str(e.get("date_start") or "")
        return (q, eid, ds)

    filtered.sort(key=sort_key)
    return filtered[:top_n]
