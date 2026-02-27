# YesCount Hybrid Strategy: History, Rationale, and Current Operating Model

Last updated: 2026-02-27
Status: Canonical strategy reference (Track A + modified Track B)

## Executive Summary

YesCount currently runs a hybrid strategy:

- Durable relational data in PostgreSQL when `DATABASE_URL` is set.
- SQLite fallback when `DATABASE_URL` is missing.
- Local Chroma for embeddings (not yet durable across host restarts).
- Weekly GitHub Actions ingestion plus runtime freshness-triggered refresh.

This document replaces the need to read Track A and Track B separately for day-to-day operations. Keep the older docs as historical context.

## Why We Moved to Hybrid

Originally, the app relied on local disk for both SQL and vectors. On Streamlit Cloud, local disk is ephemeral, which risks losing user/session data on restart. The highest user-facing risk was relational state (sessions, votes, availability, event records), so the first durability milestone focused on SQL.

That produced the current phased strategy:

1. Keep ingestion reliability and source controls from Track A.
2. Move structured runtime data to hosted Postgres from modified Track B.
3. Keep local Chroma temporarily as an explicit tradeoff.
4. Plan durable vector migration as a later phase.

## Strategy History (Track Evolution)

### Track A (implemented)

Track A introduced operational reliability for ingestion:

- Weekly scheduled workflow in GitHub Actions.
- Required source checks and run status tracking.
- Freshness-based ingestion trigger at app startup.
- Ingestion observability tables for run/source outcomes.

### Modified Track B (partially implemented, in active use)

Track B introduced durable SQL with low disruption:

- Runtime supports PostgreSQL via `DATABASE_URL`.
- Existing function contracts kept stable.
- SQLite fallback retained for resilience and local development.
- Chroma remains local in this phase.

### Current State

The app is best described as:

- Track A ingestion/ops controls + Track B durable SQL + local Chroma.

## Current Architecture

### Data planes

- SQL (sessions, participants, votes, availability, events, ingestion run tables):
  - Primary: Postgres (`DATABASE_URL`)
  - Fallback: SQLite (`SQLITE_DB_PATH`)
- Vector retrieval:
  - Local Chroma (`CHROMA_PERSIST_DIR`)

### Ingestion planes

- Scheduled: GitHub Actions weekly ingestion workflow.
- Runtime: stale-data refresh attempt on app startup.

## What This Means for Users

### Strengths

- Session and vote persistence is durable when Postgres is configured.
- Users are less likely to lose planning state after app restart.
- Ingestion has operational controls and fallback behavior.

### Tradeoffs

- Semantic/vector index can still reset on app host restart.
- Retrieval quality can temporarily degrade until vectors are rebuilt.
- Inconsistency risk remains if app and ingestion are not pointed at the same `DATABASE_URL`.

## Why This Is the Recommended Interim Approach

This hybrid approach gives the biggest usability gain now with limited migration risk:

- Protects highest-value user data first (SQL state).
- Avoids blocking release on a full vector migration.
- Preserves rollback flexibility (SQLite fallback).

## Operational Requirements (Must Hold True)

1. `DATABASE_URL` is set in Streamlit secrets for production.
2. `DATABASE_URL` is set in GitHub Actions secrets for weekly ingestion.
3. Both app and ingestion use the same Postgres target.
4. `BASE_URL` is production URL, not localhost.
5. Ingestion workflow runs are monitored and manually re-run after major scraping/curation changes.

## Recommended Next Action Plan

### Immediate (now)

- Keep this hybrid strategy as the production baseline.
- Run full quality gates (`lint`, `typecheck`, `tests`, `integration`, `smoke`).
- Run manual weekly ingestion after deploy and verify end-to-end flow.

### Near-term hardening

- Add CI coverage for Postgres path (not only SQLite fallback).
- Tighten secrets-scan policy and false-positive handling.
- Add ingestion post-run validation/alerting.

### Future phase

- Migrate Chroma to a durable managed vector backend.
- Add retrieval parity checks before vector cutover.

## Decision Guidance: Should We Consolidate Docs?

Yes. Keep this file as canonical strategy guidance and preserve Track A / Track B docs as supporting history.

Recommended conventions:

- This file: "what we do now" and "why."
- Track A/B docs: implementation history and deep reference details.

## Related Documents

- `docs/TRACK_A_WEEKLY_REFRESH.md`
- `docs/TRACK_B_DURABLE_STORAGE_REFERENCE.md`
- `docs/DEPLOYMENT_PRODUCTION.md`
- `docs/POST_DEPLOY_CHECKLIST_WALKTHROUGH.md`
