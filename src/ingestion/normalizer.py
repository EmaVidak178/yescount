from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, cast

from dateutil import parser as date_parser

DEFAULT_VIBE_KEYWORDS = {
    "immersive": ["immersive", "interactive"],
    "artsy": ["gallery", "art", "museum"],
    "outdoor": ["park", "outdoor", "garden", "rooftop"],
    "nightlife": ["club", "bar", "dj", "nightlife"],
    "family": ["family", "kids", "children"],
}


def parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    dt = cast(datetime, date_parser.parse(raw))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def parse_price(raw: str | None) -> tuple[float | None, float | None]:
    if not raw:
        return None, None
    text = raw.lower().strip()
    if "free" in text:
        return 0.0, 0.0
    numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return None, None
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    return min(numbers), max(numbers)


def extract_vibe_tags(text: str) -> list[str]:
    lowered = text.lower()
    out: list[str] = []
    for tag, keywords in DEFAULT_VIBE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            out.append(tag)
    return sorted(set(out))


def normalize_nyc_open_data(raw: dict[str, Any]) -> dict[str, Any]:
    title = (raw.get("event_name") or raw.get("title") or "").strip()
    description = (raw.get("description") or raw.get("short_description") or "").strip()
    price_min, price_max = (0.0, 0.0) if raw.get("free") else parse_price(raw.get("price"))
    return {
        "title": title or "Untitled Event",
        "description": description,
        "date_start": parse_date(raw.get("start_date_time")) or datetime.now(UTC).isoformat(),
        "date_end": parse_date(raw.get("end_date_time")),
        "location": (raw.get("location") or raw.get("event_location") or "").strip(),
        "price_min": price_min,
        "price_max": price_max,
        "url": (raw.get("event_url") or raw.get("url") or "").strip(),
        "source": "nyc_open_data",
        "source_id": str(raw.get("event_id") or raw.get(":id") or title),
        "raw_json": raw,
        "vibe_tags": extract_vibe_tags(f"{title} {description}"),
    }


def normalize_scraped(raw: dict[str, Any]) -> dict[str, Any]:
    price_min, price_max = parse_price(raw.get("price"))
    title = (raw.get("title") or "").strip()
    description = (raw.get("description") or "").strip()
    return {
        "title": title or "Untitled Event",
        "description": description,
        "date_start": parse_date(raw.get("date_start")) or datetime.now(UTC).isoformat(),
        "date_end": parse_date(raw.get("date_end")),
        "location": (raw.get("location") or "").strip(),
        "price_min": price_min,
        "price_max": price_max,
        "url": (raw.get("url") or "").strip(),
        "source": "scraped",
        "source_id": str(raw.get("source_id") or title),
        "raw_json": raw,
        "vibe_tags": extract_vibe_tags(f"{title} {description}"),
    }
