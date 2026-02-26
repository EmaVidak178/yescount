from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

DEFAULT_REQUIRED_SOURCES = [
    {"name": "secretnyc", "url": "https://secretnyc.co/", "required": True, "enabled": True},
    {
        "name": "timeout_newyork",
        "url": "https://www.timeout.com/newyork",
        "required": True,
        "enabled": True,
    },
    {"name": "hiddennyc", "url": "https://hiddennyc.net/", "required": True, "enabled": True},
    {
        "name": "untappedcities",
        "url": "https://www.untappedcities.com/",
        "required": True,
        "enabled": True,
    },
    {
        "name": "anisah_immersive",
        "url": "https://anisahauduevans.com/new-york-immersive-experiences-nyc/",
        "required": True,
        "enabled": True,
    },
    {
        "name": "fever_newyork",
        "url": "https://feverup.com/en/new-york",
        "required": True,
        "enabled": True,
    },
]


@dataclass(frozen=True)
class SourceTarget:
    name: str
    url: str
    required: bool
    enabled: bool


def _coerce_source(item: dict[str, Any]) -> SourceTarget:
    return SourceTarget(
        name=str(item.get("name", "")).strip(),
        url=str(item.get("url", "")).strip(),
        required=bool(item.get("required", False)),
        enabled=bool(item.get("enabled", True)),
    )


def load_sources(config_path: str) -> list[SourceTarget]:
    path = Path(config_path)
    raw: list[dict[str, Any]]
    if path.exists():
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        raw = payload.get("sources", []) if isinstance(payload, dict) else []
    else:
        raw = DEFAULT_REQUIRED_SOURCES

    targets = [_coerce_source(item) for item in raw if isinstance(item, dict)]
    return [target for target in targets if target.name and target.url]
