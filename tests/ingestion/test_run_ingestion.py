from __future__ import annotations

from src.config.settings import Settings
from src.db.sqlite_client import latest_successful_ingestion_run
from src.ingestion.run_ingestion import run_ingestion, should_refresh


def _source(name: str, url: str, required: bool = True, enabled: bool = True):
    return type(
        "Source",
        (),
        {
            "name": name,
            "url": url,
            "required": required,
            "enabled": enabled,
        },
    )()


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
        return_value=[_source("required_site", "https://example.com", required=True)],
    )
    mocker.patch("src.ingestion.run_ingestion.scrape_site", return_value=[])
    result = run_ingestion(
        conn=sqlite_db,
        settings=_settings(strict_required=True, dataset_id="dataset"),
        force=True,
    )
    assert result["status"] == "success"


def test_run_ingestion_skips_invalid_scraped_event_datetime(sqlite_db, mocker):
    mocker.patch("src.ingestion.run_ingestion.fetch_all_events", return_value=[])
    mocker.patch(
        "src.ingestion.run_ingestion.load_sources",
        return_value=[_source("scraper_site", "https://example.com", required=True)],
    )
    mocker.patch("src.ingestion.run_ingestion.scrape_site", return_value=[{"id": "raw"}])
    mocker.patch(
        "src.ingestion.run_ingestion.normalize_scraped_events",
        return_value=[
            {
                "title": "Bad Date Event",
                "description": "invalid date row",
                "date_start": "",
                "date_end": None,
                "location": "NYC",
                "price_min": None,
                "price_max": None,
                "url": "https://example.com/bad",
                "source": "scraped",
                "source_id": "bad-1",
                "raw_json": {},
                "vibe_tags": [],
            },
            {
                "title": "Valid Date Event",
                "description": "valid date row",
                "date_start": "2026-03-10T19:00:00+00:00",
                "date_end": None,
                "location": "NYC",
                "price_min": None,
                "price_max": None,
                "url": "https://example.com/good",
                "source": "scraped",
                "source_id": "good-1",
                "raw_json": {},
                "vibe_tags": [],
            },
        ],
    )

    result = run_ingestion(
        conn=sqlite_db,
        settings=_settings(strict_required=True, dataset_id="dataset"),
        force=True,
    )

    assert result["status"] == "success"
    assert result["events_upserted"] == 1

    inserted = sqlite_db.execute(
        "SELECT COUNT(*) AS cnt FROM events WHERE source = 'scraped'"
    ).fetchone()
    assert inserted["cnt"] == 1

    source_check = sqlite_db.execute(
        "SELECT status, error FROM ingestion_source_checks WHERE source_name = ? ORDER BY id DESC LIMIT 1",
        ("scraper_site",),
    ).fetchone()
    assert source_check["status"] == "success"
    assert "skipped_invalid_date=1" in source_check["error"]


def test_run_ingestion_continues_after_one_source_fails(sqlite_db, mocker):
    mocker.patch("src.ingestion.run_ingestion.fetch_all_events", return_value=[])
    mocker.patch(
        "src.ingestion.run_ingestion.load_sources",
        return_value=[
            _source("broken_source", "https://broken.example.com", required=False),
            _source("healthy_source", "https://healthy.example.com", required=False),
        ],
    )

    def _fake_scrape(url: str, source_name: str):
        if "broken" in url:
            raise RuntimeError("boom")
        return [{"id": "raw-ok"}]

    mocker.patch("src.ingestion.run_ingestion.scrape_site", side_effect=_fake_scrape)
    mocker.patch(
        "src.ingestion.run_ingestion.normalize_scraped_events",
        return_value=[
            {
                "title": "Recovered Event",
                "description": "source continuation works",
                "date_start": "2026-04-01T19:00:00+00:00",
                "date_end": None,
                "location": "NYC",
                "price_min": None,
                "price_max": None,
                "url": "https://example.com/recovered",
                "source": "scraped",
                "source_id": "recovered-1",
                "raw_json": {},
                "vibe_tags": [],
            }
        ],
    )

    result = run_ingestion(
        conn=sqlite_db,
        settings=_settings(strict_required=True, dataset_id="dataset"),
        force=True,
    )

    assert result["status"] == "success"
    assert result["events_upserted"] == 1

    checks = sqlite_db.execute(
        "SELECT source_name, status FROM ingestion_source_checks WHERE source_name IN (?, ?)",
        ("broken_source", "healthy_source"),
    ).fetchall()
    statuses = {row["source_name"]: row["status"] for row in checks}
    assert statuses["broken_source"] == "failed"
    assert statuses["healthy_source"] == "success"


def test_run_ingestion_continues_when_single_event_upsert_raises(sqlite_db, mocker):
    mocker.patch("src.ingestion.run_ingestion.fetch_all_events", return_value=[])
    mocker.patch(
        "src.ingestion.run_ingestion.load_sources",
        return_value=[_source("mixed_source", "https://mixed.example.com", required=False)],
    )
    mocker.patch("src.ingestion.run_ingestion.scrape_site", return_value=[{"id": "raw-mixed"}])
    mocker.patch(
        "src.ingestion.run_ingestion.normalize_scraped_events",
        return_value=[
            {
                "title": "First Event",
                "description": "will fail during upsert",
                "date_start": "2026-04-10T19:00:00+00:00",
                "date_end": None,
                "location": "NYC",
                "price_min": None,
                "price_max": None,
                "url": "https://example.com/first",
                "source": "scraped",
                "source_id": "first-fails",
                "raw_json": {},
                "vibe_tags": [],
            },
            {
                "title": "Second Event",
                "description": "should still insert",
                "date_start": "2026-04-11T19:00:00+00:00",
                "date_end": None,
                "location": "NYC",
                "price_min": None,
                "price_max": None,
                "url": "https://example.com/second",
                "source": "scraped",
                "source_id": "second-ok",
                "raw_json": {},
                "vibe_tags": [],
            },
        ],
    )

    from src.db.sqlite_client import upsert_event as real_upsert

    call_state = {"n": 0}

    def _flaky_upsert(conn, event):
        call_state["n"] += 1
        if call_state["n"] == 1:
            raise RuntimeError("synthetic upsert failure")
        return real_upsert(conn, event)

    mocker.patch("src.ingestion.run_ingestion.upsert_event", side_effect=_flaky_upsert)

    result = run_ingestion(
        conn=sqlite_db,
        settings=_settings(strict_required=True, dataset_id="dataset"),
        force=True,
    )

    assert result["status"] == "success"
    assert result["events_upserted"] == 1

    inserted = sqlite_db.execute(
        "SELECT COUNT(*) AS cnt FROM events WHERE source = 'scraped'"
    ).fetchone()
    assert inserted["cnt"] == 1

    source_check = sqlite_db.execute(
        "SELECT status, error FROM ingestion_source_checks WHERE source_name = ? ORDER BY id DESC LIMIT 1",
        ("mixed_source",),
    ).fetchone()
    assert source_check["status"] == "success"
    assert "skipped_invalid_date=1" in source_check["error"]
