from __future__ import annotations

import re
from datetime import UTC
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


def _extract_date_start(raw_text: str) -> str | None:
    """Best-effort extraction of event date from scraped card text."""
    match = DATE_PATTERN.search(raw_text)
    if not match:
        return None
    try:
        dt = date_parser.parse(match.group(0))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def scrape_site(url: str, source_name: str | None = None) -> list[dict[str, Any]]:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    items: list[dict[str, Any]] = []
    source_label = source_name or url
    for idx, card in enumerate(soup.select("article, .event, .card")):
        raw_text = card.get_text(" ", strip=True)
        title = raw_text[:120]
        detected_date = _extract_date_start(raw_text)
        items.append(
            {
                "title": title or f"Scraped Event {idx + 1}",
                "description": raw_text,
                "date_start": detected_date,
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
