from __future__ import annotations

from src.config.settings import Settings
from src.db.sqlite_client import latest_successful_ingestion_run
from src.ingestion.run_ingestion import run_ingestion, should_refresh


def _settings(strict_required: bool = True, dataset_id: str = "") -> Settings:
    return Settings(
        openai_api_key="",
        nyc_open_data_app_token="token",
        nyc_open_data_dataset_id=dataset_id,
        database_url="",
        sqlite_db_path="data/yescount.db",
        chroma_persist_dir="data/chroma/",
        session_expiry_days=7,
        log_level="INFO",
        base_url="http://localhost:8501",
        scraper_sites_config_path="config/scraper_sites.yaml",
        ingestion_auto_refresh=True,
        ingestion_max_staleness_hours=192,
        ingestion_required_sources_strict=strict_required,
    )


def test_should_refresh_when_no_successful_run(sqlite_db):
    assert should_refresh(sqlite_db, max_staleness_hours=192) is True


def test_run_ingestion_degraded_when_required_source_fails_and_not_strict(sqlite_db, mocker):
    mocker.patch("src.ingestion.run_ingestion.load_sources", return_value=[])
    result = run_ingestion(conn=sqlite_db, settings=_settings(strict_required=False), force=True)
    assert result["status"] == "degraded"
    latest = latest_successful_ingestion_run(sqlite_db)
    assert latest is not None
    assert latest["status"] == "degraded"


def test_run_ingestion_failed_when_required_source_fails_and_strict(sqlite_db, mocker):
    mocker.patch("src.ingestion.run_ingestion.load_sources", return_value=[])
    result = run_ingestion(conn=sqlite_db, settings=_settings(strict_required=True), force=True)
    assert result["status"] == "failed"


def test_required_source_partial_does_not_fail_run(sqlite_db, mocker):
    mocker.patch("src.ingestion.run_ingestion.fetch_all_events", return_value=[{"event_name": "A"}])
    mocker.patch(
        "src.ingestion.run_ingestion.load_sources",
        return_value=[
            type(
                "Source",
                (),
                {
                    "name": "required_site",
                    "url": "https://example.com",
                    "required": True,
                    "enabled": True,
                },
            )()
        ],
    )
    mocker.patch("src.ingestion.run_ingestion.scrape_site", return_value=[])
    result = run_ingestion(
        conn=sqlite_db,
        settings=_settings(strict_required=True, dataset_id="dataset"),
        force=True,
    )
    assert result["status"] == "success"
