from __future__ import annotations

import pytest

from src.config.settings import Settings, validate_settings


@pytest.mark.smoke
def test_settings_validation_flags_missing_keys():
    settings = Settings(
        openai_api_key="",
        nyc_open_data_app_token="",
        nyc_open_data_dataset_id="",
        database_url="",
        sqlite_db_path="data/yescount.db",
        chroma_persist_dir="data/chroma/",
        session_expiry_days=7,
        log_level="INFO",
        base_url="http://localhost:8501",
        scraper_sites_config_path="config/scraper_sites.yaml",
        ingestion_auto_refresh=True,
        ingestion_max_staleness_hours=192,
        ingestion_required_sources_strict=True,
    )
    errors = validate_settings(settings)
    assert "OPENAI_API_KEY is required" in errors
    assert "NYC_OPEN_DATA_APP_TOKEN is required" in errors
    assert "NYC_OPEN_DATA_DATASET_ID is required" in errors
