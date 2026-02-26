from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _get_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    nyc_open_data_app_token: str
    nyc_open_data_dataset_id: str
    database_url: str
    sqlite_db_path: str
    chroma_persist_dir: str
    session_expiry_days: int
    log_level: str
    base_url: str
    scraper_sites_config_path: str
    ingestion_auto_refresh: bool
    ingestion_max_staleness_hours: int
    ingestion_required_sources_strict: bool


def load_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        nyc_open_data_app_token=os.getenv("NYC_OPEN_DATA_APP_TOKEN", ""),
        nyc_open_data_dataset_id=os.getenv("NYC_OPEN_DATA_DATASET_ID", ""),
        database_url=os.getenv("DATABASE_URL", "").strip(),
        sqlite_db_path=os.getenv("SQLITE_DB_PATH", "data/yescount.db"),
        chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", "data/chroma/"),
        session_expiry_days=int(os.getenv("SESSION_EXPIRY_DAYS", "7")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        base_url=os.getenv("BASE_URL", "http://localhost:8501"),
        scraper_sites_config_path=os.getenv(
            "SCRAPER_SITES_CONFIG_PATH", "config/scraper_sites.yaml"
        ),
        ingestion_auto_refresh=_get_bool_env("INGESTION_AUTO_REFRESH", True),
        ingestion_max_staleness_hours=int(os.getenv("INGESTION_MAX_STALENESS_HOURS", "192")),
        ingestion_required_sources_strict=_get_bool_env("INGESTION_REQUIRED_SOURCES_STRICT", True),
    )


def validate_settings(settings: Settings) -> list[str]:
    errors: list[str] = []
    if not settings.openai_api_key:
        errors.append("OPENAI_API_KEY is required")
    if not settings.nyc_open_data_app_token:
        errors.append("NYC_OPEN_DATA_APP_TOKEN is required")
    if not settings.nyc_open_data_dataset_id:
        errors.append("NYC_OPEN_DATA_DATASET_ID is required")
    if settings.session_expiry_days <= 0:
        errors.append("SESSION_EXPIRY_DAYS must be > 0")
    if not settings.base_url:
        errors.append("BASE_URL is required")
    if "://" not in settings.base_url:
        errors.append("BASE_URL must include scheme, e.g. http://")
    if settings.ingestion_max_staleness_hours <= 0:
        errors.append("INGESTION_MAX_STALENESS_HOURS must be > 0")
    if settings.database_url and not settings.database_url.startswith(
        ("postgres://", "postgresql://")
    ):
        errors.append("DATABASE_URL must start with postgres:// or postgresql://")
    return errors


def ensure_runtime_dirs(settings: Settings) -> None:
    if not settings.database_url:
        Path(settings.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
