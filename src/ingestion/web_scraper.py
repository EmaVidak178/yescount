from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from src.ingestion.normalizer import normalize_scraped

DATE_PATTERN = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)


def _extract_dates(raw_text: str) -> tuple[str | None, str]:
    """Extract a single clear date. Return (iso_datetime_or_none, status)."""
    matches = DATE_PATTERN.findall(raw_text)
    if not matches:
        return None, "unclear"
    unique = []
    seen = set()
    for m in matches:
        key = m.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)
    # More than one distinct date usually means a range/recurring schedule.
    if len(unique) != 1:
        return None, "multiple"
    try:
        # Use a midnight default to avoid inheriting "current time" from parser defaults.
        default_dt = datetime(datetime.now(UTC).year, 1, 1, 0, 0, tzinfo=UTC)
        dt = date_parser.parse(unique[0], default=default_dt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return dt.isoformat(), "single"
    except (ValueError, TypeError, OverflowError):
        return None, "unclear"


def scrape_site(url: str, source_name: str | None = None) -> list[dict[str, Any]]:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    items: list[dict[str, Any]] = []
    source_label = source_name or url
    for idx, card in enumerate(soup.select("article, .event, .card")):
        raw_text = card.get_text(" ", strip=True)
        title = raw_text[:120]
        detected_date, date_status = _extract_dates(raw_text)
        items.append(
            {
                "title": title or f"Scraped Event {idx + 1}",
                "description": raw_text,
                "date_start": detected_date,
                "date_status": date_status,
                "source_id": f"{source_label}-{idx}",
                "url": url,
                "location": "",
                "price": None,
            }
        )
    return items


def scrape_all(
    urls: list[str], source_name_by_url: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    labels = source_name_by_url or {}
    for url in urls:
        try:
            out.extend(scrape_site(url, source_name=labels.get(url)))
        except requests.RequestException:
            continue
    return out


def normalize_scraped_events(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_scraped(item) for item in raw_events]
