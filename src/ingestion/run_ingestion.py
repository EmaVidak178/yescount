from __future__ import annotations

import argparse
import sqlite3
import sys
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from openai import OpenAI

from src.config.settings import Settings, load_settings
from src.db.chroma_client import upsert_event_embedding
from src.db.sqlite_client import (
    create_ingestion_run,
    finalize_ingestion_run,
    latest_successful_ingestion_run,
    record_ingestion_source_check,
    upsert_event,
)
from src.ingestion.nyc_open_data import fetch_all_events, normalize_events
from src.ingestion.source_config import SourceTarget, load_sources
from src.ingestion.web_scraper import normalize_scraped_events, scrape_site
from src.rag.embedder import embed_batch


def _safe_rollback(conn: Any) -> None:
    """Reset failed DB transactions without masking original errors."""
    with suppress(Exception):
        conn.rollback()


def _log_source_status(
    source_name: str,
    status: str,
    events_found: int,
    error: str = "",
) -> None:
    msg = f"[INGESTION] source={source_name} status={status} events={events_found}"
    if error:
        msg += f" error={error}"
    stream = sys.stderr if status in {"failed", "partial"} else sys.stdout
    print(msg, file=stream)


def should_refresh(conn: sqlite3.Connection, max_staleness_hours: int) -> bool:
    latest = latest_successful_ingestion_run(conn)
    if not latest:
        return True
    finished_at = latest.get("finished_at")
    if not finished_at:
        return True
    try:
        normalized = str(finished_at).replace(" ", "T")
        last = datetime.fromisoformat(normalized)
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
    except ValueError:
        return True
    return datetime.now(UTC) - last > timedelta(hours=max_staleness_hours)


def _is_valid_event_datetime(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, datetime):
        return True
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return True
    except ValueError:
        try:
            datetime.strptime(text[:10], "%Y-%m-%d")
            return True
        except ValueError:
            return False


def _upsert_and_embed(
    conn: sqlite3.Connection,
    collection: Any | None,
    client: OpenAI | None,
    events: list[dict[str, Any]],
) -> tuple[int, int]:
    if not events:
        return 0, 0
    event_ids: list[int] = []
    docs: list[str] = []
    embedded_events: list[dict[str, Any]] = []
    skipped_invalid_date = 0
    for event in events:
        if not _is_valid_event_datetime(event.get("date_start")):
            skipped_invalid_date += 1
            print(
                (
                    "[INGESTION] skip_event reason=invalid_date_start "
                    f"source={event.get('source')} source_id={event.get('source_id')} "
                    f"title={str(event.get('title', ''))[:80]}"
                ),
                file=sys.stderr,
            )
            continue
        try:
            event_id = upsert_event(conn, event)
        except Exception as exc:
            skipped_invalid_date += 1
            _safe_rollback(conn)
            print(
                (
                    "[INGESTION] skip_event reason=upsert_error "
                    f"source={event.get('source')} source_id={event.get('source_id')} "
                    f"error={exc}"
                ),
                file=sys.stderr,
            )
            continue
        event_ids.append(event_id)
        embedded_events.append(event)
        docs.append(
            " | ".join(
                [
                    str(event.get("title", "")),
                    str(event.get("description", "")),
                    str(event.get("location", "")),
                ]
            ).strip()
        )

    if collection is None or client is None:
        return len(event_ids), skipped_invalid_date

    vectors = embed_batch(client, docs)
    for idx, event_id in enumerate(event_ids):
        vector = vectors[idx] if idx < len(vectors) else []
        if not vector:
            continue
        event = embedded_events[idx]
        upsert_event_embedding(
            collection=collection,
            event_id=event_id,
            document=docs[idx],
            embedding=vector,
            metadata={
                "date_start": event.get("date_start"),
                "price_max": event.get("price_max"),
                "source": event.get("source"),
            },
        )
    return len(event_ids), skipped_invalid_date


def run_ingestion(
    *,
    conn: sqlite3.Connection,
    settings: Settings,
    collection: Any | None = None,
    client: OpenAI | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if not force and not should_refresh(conn, settings.ingestion_max_staleness_hours):
        return {"status": "skipped", "reason": "fresh_enough", "events_upserted": 0}

    run_id = create_ingestion_run(conn)
    total_upserted = 0
    required_failed: list[str] = []
    errors: list[str] = []

    try:
        if settings.nyc_open_data_dataset_id:
            raw = fetch_all_events(
                dataset_id=settings.nyc_open_data_dataset_id,
                app_token=settings.nyc_open_data_app_token,
            )
            normalized = normalize_events(raw)
            inserted, skipped_invalid = _upsert_and_embed(conn, collection, client, normalized)
            total_upserted += inserted
            nyc_status = "success" if inserted > 0 else "partial"
            nyc_error = f"skipped_invalid_date={skipped_invalid}" if skipped_invalid else ""
            record_ingestion_source_check(
                conn,
                run_id=run_id,
                source_name="nyc_open_data",
                source_url="https://data.cityofnewyork.us/",
                required=True,
                status=nyc_status,
                events_found=inserted,
                error=nyc_error,
            )
            _log_source_status("nyc_open_data", nyc_status, inserted, nyc_error)
        else:
            record_ingestion_source_check(
                conn,
                run_id=run_id,
                source_name="nyc_open_data",
                source_url="https://data.cityofnewyork.us/",
                required=True,
                status="skipped",
                events_found=0,
                error="NYC_OPEN_DATA_DATASET_ID not configured",
            )
            _log_source_status(
                "nyc_open_data",
                "skipped",
                0,
                "NYC_OPEN_DATA_DATASET_ID not configured",
            )
            required_failed.append("nyc_open_data")

        sources: list[SourceTarget] = load_sources(settings.scraper_sites_config_path)
        for source in sources:
            if not source.enabled:
                record_ingestion_source_check(
                    conn,
                    run_id=run_id,
                    source_name=source.name,
                    source_url=source.url,
                    required=source.required,
                    status="skipped",
                    events_found=0,
                    error="disabled",
                )
                _log_source_status(source.name, "skipped", 0, "disabled")
                continue

            try:
                raw_scraped = scrape_site(source.url, source_name=source.name)
                normalized_scraped = normalize_scraped_events(raw_scraped)
                inserted, skipped_invalid = _upsert_and_embed(
                    conn, collection, client, normalized_scraped
                )
                total_upserted += inserted
                status = "success" if inserted > 0 else "partial"
                source_error = ""
                if inserted == 0:
                    source_error = "no events extracted"
                if skipped_invalid:
                    extra = f"skipped_invalid_date={skipped_invalid}"
                    source_error = f"{source_error}; {extra}".strip("; ").strip()
                record_ingestion_source_check(
                    conn,
                    run_id=run_id,
                    source_name=source.name,
                    source_url=source.url,
                    required=source.required,
                    status=status,
                    events_found=inserted,
                    error=source_error,
                )
                _log_source_status(
                    source.name,
                    status,
                    inserted,
                    source_error,
                )
            except requests.RequestException as exc:
                _safe_rollback(conn)
                if source.required:
                    required_failed.append(source.name)
                record_ingestion_source_check(
                    conn,
                    run_id=run_id,
                    source_name=source.name,
                    source_url=source.url,
                    required=source.required,
                    status="failed",
                    events_found=0,
                    error=str(exc),
                )
                _log_source_status(source.name, "failed", 0, str(exc))
            except Exception as exc:
                _safe_rollback(conn)
                if source.required:
                    required_failed.append(source.name)
                record_ingestion_source_check(
                    conn,
                    run_id=run_id,
                    source_name=source.name,
                    source_url=source.url,
                    required=source.required,
                    status="failed",
                    events_found=0,
                    error=str(exc),
                )
                _log_source_status(source.name, "failed", 0, str(exc))

        if required_failed:
            status = "failed" if settings.ingestion_required_sources_strict else "degraded"
            summary = f"required source failures: {', '.join(sorted(set(required_failed)))}"
            finalize_ingestion_run(
                conn,
                run_id=run_id,
                status=status,
                total_events_upserted=total_upserted,
                error_summary=summary,
            )
            print(
                f"[INGESTION] run_status={status} total_events={total_upserted} {summary}",
                file=sys.stderr,
            )
            return {
                "status": status,
                "events_upserted": total_upserted,
                "required_failed": sorted(set(required_failed)),
            }

        finalize_ingestion_run(
            conn,
            run_id=run_id,
            status="success",
            total_events_upserted=total_upserted,
            error_summary="",
        )
        print(
            f"[INGESTION] run_status=success total_events={total_upserted}",
            file=sys.stdout,
        )
        return {"status": "success", "events_upserted": total_upserted}
    except Exception as exc:
        errors.append(str(exc))
        _safe_rollback(conn)
        finalize_ingestion_run(
            conn,
            run_id=run_id,
            status="failed",
            total_events_upserted=total_upserted,
            error_summary="; ".join(errors)[:1000],
        )
        print(
            f"[INGESTION] run_status=failed total_events={total_upserted} error={errors[-1]}",
            file=sys.stderr,
        )
        return {"status": "failed", "events_upserted": total_upserted, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    from src.db.sqlite_client import get_connection, init_schema

    conn = get_connection(settings.sqlite_db_path)
    init_schema(conn)

    collection = None
    client: OpenAI | None = None
    if settings.openai_api_key:
        try:
            from src.db.chroma_client import get_client, get_collection

            chroma = get_client(settings.chroma_persist_dir)
            collection = get_collection(chroma)
            client = OpenAI(api_key=settings.openai_api_key, timeout=20.0, max_retries=3)
        except Exception:
            collection = None
            client = None

    result = run_ingestion(
        conn=conn,
        settings=settings,
        collection=collection,
        client=client,
        force=args.force,
    )
    print(result)
    if result.get("status") == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
