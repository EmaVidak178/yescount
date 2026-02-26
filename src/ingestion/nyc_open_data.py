from __future__ import annotations

from typing import Any

import requests

from src.ingestion.normalizer import normalize_nyc_open_data

BASE_URL = "https://data.cityofnewyork.us/resource"


def fetch_events(
    dataset_id: str,
    app_token: str,
    limit: int = 200,
    offset: int = 0,
    timeout_seconds: int = 30,
) -> list[dict[str, Any]]:
    resp = requests.get(
        f"{BASE_URL}/{dataset_id}.json",
        headers={"X-App-Token": app_token},
        params={"$limit": limit, "$offset": offset},
        timeout=timeout_seconds,
    )
    resp.raise_for_status()
    payload = resp.json()
    return payload if isinstance(payload, list) else []


def fetch_all_events(dataset_id: str, app_token: str, page_size: int = 200) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        chunk = fetch_events(dataset_id, app_token, limit=page_size, offset=offset)
        if not chunk:
            break
        out.extend(chunk)
        offset += page_size
    return out


def normalize_events(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_nyc_open_data(item) for item in raw_events]
