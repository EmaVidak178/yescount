# Track A Runbook: Weekly Friday Refresh + Required Sources

## Goal

- Auto-refresh events weekly on Friday.
- Enforce required-source checks for configured websites.
- Keep app usable if one source fails.

## What Was Implemented

- Ingestion orchestrator: `src/ingestion/run_ingestion.py`
- Source config loader: `src/ingestion/source_config.py`
- Required sources config: `config/scraper_sites.yaml`
- Ingestion run/source tracking tables in SQLite:
  - `ingestion_runs`
  - `ingestion_source_checks`
- Freshness-triggered ingestion call from app runtime:
  - `app.py` -> `maybe_refresh_events()`
- Weekly scheduled workflow:
  - `.github/workflows/weekly_ingestion.yml`
- Environment variables updated in `.env.example`

## Required Environment Variables

- `OPENAI_API_KEY`
- `NYC_OPEN_DATA_APP_TOKEN`
- `NYC_OPEN_DATA_DATASET_ID`
- `SCRAPER_SITES_CONFIG_PATH` (default `config/scraper_sites.yaml`)
- `INGESTION_AUTO_REFRESH` (default `true`)
- `INGESTION_MAX_STALENESS_HOURS` (default `192`, 8 days)
- `INGESTION_REQUIRED_SOURCES_STRICT` (default `true`)

## Secret Setup Checklist

For GitHub Actions (`weekly_ingestion.yml`):
- `OPENAI_API_KEY`
- `NYC_OPEN_DATA_APP_TOKEN`
- `NYC_OPEN_DATA_DATASET_ID`

For Streamlit app secrets:
- `OPENAI_API_KEY`
- `NYC_OPEN_DATA_APP_TOKEN`
- `NYC_OPEN_DATA_DATASET_ID`
- `BASE_URL`
- `DATABASE_URL` (recommended for durable SQL persistence)

## Runtime Behavior

- If last successful run is older than `INGESTION_MAX_STALENESS_HOURS`, app attempts refresh.
- Required source failures:
  - strict mode (`true`): run status becomes `failed`
  - non-strict mode (`false`): run status becomes `degraded`
- Existing events remain available even on degraded/failed run.

## Friday Schedule

- Workflow cron: Friday at `10:00 UTC` (about 6:00 ET during daylight savings).

## Important Deployment Caveat

If app runtime uses local SQLite/Chroma on ephemeral disk, scheduled ingestion from a separate runner may not update the same persistent data users read from.

For reliable production behavior, ensure scheduler and app read/write the same durable storage backend.

## Manual Trigger

Use:

```bash
python -m src.ingestion.run_ingestion --force
```

or

```bash
make ingest
```
