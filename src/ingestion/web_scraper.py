from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

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

DATE_RANGE_PATTERN = re.compile(
    r"\b("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\s+(\d{1,2})\s*[-\u2013]\s*(\d{1,2})(?:,\s*(\d{4}))?\b",
    re.IGNORECASE,
)

GENERIC_LISTICLE_PATTERNS = (
    "things to do",
    "best",
    "top ",
    "happenings",
    "you can't miss",
)


def _extract_dates(raw_text: str) -> tuple[str | None, str | None, str]:
    """Extract date(s). Returns (date_start_iso, date_end_iso, status)."""
    # Handle explicit ranges like "March 4-6, 2026".
    range_match = DATE_RANGE_PATTERN.search(raw_text)
    if range_match:
        month, start_day, end_day, year = range_match.groups()
        year_part = year or str(datetime.now(UTC).year)
        try:
            start_dt = date_parser.parse(
                f"{month} {start_day}, {year_part}",
                default=datetime(int(year_part), 1, 1, 0, 0, tzinfo=UTC),
            )
            end_dt = date_parser.parse(
                f"{month} {end_day}, {year_part}",
                default=datetime(int(year_part), 1, 1, 0, 0, tzinfo=UTC),
            )
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=UTC)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=UTC)
            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            return start_dt.isoformat(), end_dt.isoformat(), "range"
        except (ValueError, TypeError, OverflowError):
            return None, None, "unclear"

    matches = DATE_PATTERN.findall(raw_text)
    if not matches:
        return None, None, "unclear"
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
        return None, None, "multiple"
    try:
        # Use a midnight default to avoid inheriting "current time" from parser defaults.
        default_dt = datetime(datetime.now(UTC).year, 1, 1, 0, 0, tzinfo=UTC)
        dt = date_parser.parse(unique[0], default=default_dt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return dt.isoformat(), None, "single"
    except (ValueError, TypeError, OverflowError):
        return None, None, "unclear"


def _clean_title(text: str) -> str:
    title = re.sub(r"^\s*\d+\s*[\.\)]\s*", "", text).strip()
    return re.sub(r"\s+", " ", title)


def _looks_like_listicle_title(title: str) -> bool:
    t = title.lower()
    if any(part in t for part in GENERIC_LISTICLE_PATTERNS):
        return True
    return bool(re.search(r"\b(top|best)\s+\d+\b", t))


def _extract_image_url(node: Any, base_url: str) -> str | None:
    img = node.select_one("img")
    if img is None:
        return None
    src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
    if not src:
        return None
    if src.startswith("http://") or src.startswith("https://"):
        return src
    if src.startswith("//"):
        return f"https:{src}"
    return urljoin(base_url, src)


def _build_source_id(source_label: str, title: str) -> str:
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:12]
    return f"{source_label}-{digest}"


def _extract_secretnyc_events(
    soup: BeautifulSoup, url: str, source_label: str
) -> list[dict[str, Any]]:
    """Extract individual events from SecretNYC list pages."""
    out: list[dict[str, Any]] = []
    headings = soup.select("h2")
    for h2 in headings:
        title = _clean_title(h2.get_text(" ", strip=True))
        if not title or len(title) < 8:
            continue
        # Skip generic sections, newsletter/footer blocks, and listicle container title.
        low = title.lower()
        if low.startswith("latest posts") or low.startswith("discover our cities"):
            continue
        if "stay in the loop" in low or "subscribe" in low:
            continue
        if _looks_like_listicle_title(title):
            continue

        # Collect nearby text for this specific section.
        section_text_parts: list[str] = []
        section_image = _extract_image_url(h2, url)
        for sib in h2.find_next_siblings():
            if getattr(sib, "name", None) == "h2":
                break
            text = sib.get_text(" ", strip=True)
            if text:
                section_text_parts.append(text)
            if section_image is None:
                section_image = _extract_image_url(sib, url)
            if len(" ".join(section_text_parts)) > 1000:
                break
        section_text = " ".join(section_text_parts).strip()
        if len(section_text) < 30:
            continue
        date_start, date_end, date_status = _extract_dates(section_text)
        out.append(
            {
                "title": title,
                "description": section_text,
                "date_start": date_start,
                "date_end": date_end,
                "date_status": date_status,
                "source_id": _build_source_id(source_label, title),
                "url": url,
                "location": "",
                "price": None,
                "image_url": section_image,
            }
        )
    return out


def scrape_site(url: str, source_name: str | None = None) -> list[dict[str, Any]]:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    items: list[dict[str, Any]] = []
    source_label = source_name or url

    # Site-specific extraction for list-style articles with many embedded events.
    if "secretnyc.co" in url:
        extracted = _extract_secretnyc_events(soup, url, source_label)
        if extracted:
            return extracted

    for idx, card in enumerate(soup.select("article, .event, .card")):
        raw_text = card.get_text(" ", strip=True)
        if len(raw_text) > 3500 and len(DATE_PATTERN.findall(raw_text)) > 3:
            # Avoid treating giant list pages as a single event.
            continue
        title = raw_text[:120]
        detected_date, detected_end, date_status = _extract_dates(raw_text)
        image_url = _extract_image_url(card, url)
        items.append(
            {
                "title": title or f"Scraped Event {idx + 1}",
                "description": raw_text,
                "date_start": detected_date,
                "date_end": detected_end,
                "date_status": date_status,
                "source_id": _build_source_id(source_label, title or f"Scraped Event {idx + 1}"),
                "url": url,
                "location": "",
                "price": None,
                "image_url": image_url,
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
