from __future__ import annotations

from typing import Any, cast

from src.config.settings import Settings, validate_settings


def _valid_settings(**overrides: object) -> Settings:
    defaults = {
        "openai_api_key": "sk-test",
        "nyc_open_data_app_token": "token",
        "nyc_open_data_dataset_id": "dataset",
        "database_url": "",
        "sqlite_db_path": "data/yescount.db",
        "chroma_persist_dir": "data/chroma/",
        "session_expiry_days": 7,
        "log_level": "INFO",
        "base_url": "http://localhost:8501",
        "scraper_sites_config_path": "config/scraper_sites.yaml",
        "ingestion_auto_refresh": True,
        "ingestion_max_staleness_hours": 192,
        "ingestion_required_sources_strict": True,
    }
    defaults.update(overrides)
    return Settings(**cast(dict[str, Any], defaults))


def test_validate_settings_rejects_empty_scraper_config_path():
    """Missing or empty SCRAPER_SITES_CONFIG_PATH produces a validation error."""
    settings = _valid_settings(scraper_sites_config_path="")
    errors = validate_settings(settings)
    assert any("SCRAPER_SITES_CONFIG_PATH" in e for e in errors)


def test_validate_settings_rejects_whitespace_only_scraper_config_path():
    """Whitespace-only SCRAPER_SITES_CONFIG_PATH produces a validation error."""
    settings = _valid_settings(scraper_sites_config_path="   ")
    errors = validate_settings(settings)
    assert any("SCRAPER_SITES_CONFIG_PATH" in e for e in errors)


def test_validate_settings_accepts_valid_scraper_config_path():
    """Non-empty scraper config path passes validation (path existence not checked)."""
    settings = _valid_settings(scraper_sites_config_path="config/scraper_sites.yaml")
    errors = validate_settings(settings)
    scraper_errors = [e for e in errors if "SCRAPER_SITES_CONFIG_PATH" in e]
    assert len(scraper_errors) == 0
