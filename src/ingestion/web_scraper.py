from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup

from src.ingestion.normalizer import normalize_scraped


def scrape_site(url: str, source_name: str | None = None) -> list[dict[str, Any]]:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    items: list[dict[str, Any]] = []
    source_label = source_name or url
    for idx, card in enumerate(soup.select("article, .event, .card")):
        raw_text = card.get_text(" ", strip=True)
        title = raw_text[:120]
        items.append(
            {
                "title": title or f"Scraped Event {idx + 1}",
                "description": raw_text,
                "date_start": None,
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
