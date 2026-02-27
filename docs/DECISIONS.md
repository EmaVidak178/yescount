# YesCount Decision Log

Status: approved-for-build
Date: 2026-02-25
Owner: implementation agent

## 1) Session Expiry Policy

- `SESSION_EXPIRY_DAYS` (default `7`) defines session expiration.
- `expires_at` is set at session creation: `created_at + SESSION_EXPIRY_DAYS`.
- Expired sessions are read-only:
  - join is blocked,
  - vote writes are blocked,
  - availability writes are blocked.
- Expired sessions remain previewable for transparency.

## 2) Session Lock Policy

- Only the connector (session creator) can lock a session.
- Lock transition allowed only from `open -> locked`.
- Locked sessions remain visible and recommendation results are viewable.
- Locked sessions block any further vote and availability writes.
- Unlocking is out-of-scope for MVP.

## 3) Participant Identity and Matching

- Participant uniqueness is `(session_id, normalized_name)`.
- `normalized_name` means `strip()` + case-insensitive compare.
- Display keeps original casing from first successful join.
- Duplicate join attempts return existing participant id (idempotent join).

## 4) Recommendation Output Defaults

- Recommendation list defaults to top `5` items.
- Sorting:
  1. composite score (desc),
  2. overlap score (desc),
  3. lower `price_min` first,
  4. earlier `date_start`.
- If fewer than 5 candidates exist, return available candidates without error.

## 5) Calendar Boundaries

- Week navigation is clamped to configured session date range.
- Only date cells inside the session date range are interactive.
- Out-of-range cells are rendered disabled.

## 6) Search and Retrieval Defaults

- Search timeout is 30 seconds.
- Primary retrieval: Chroma semantic query + metadata filters.
- Fallback retrieval: SQLite filter-only search when vector retrieval fails.
- If retrieval yields zero results, show explicit empty-state messaging.

## 7) Cache Invalidation

- Clear relevant cache entries after:
  - vote writes,
  - availability writes,
  - session lock/archival,
  - ingestion updates.
- Avoid global cache clears unless data model version changes.

## 8) MVP Durability Stance

- Current production stance is hybrid:
  - durable SQL in Postgres when `DATABASE_URL` is set,
  - SQLite fallback when `DATABASE_URL` is absent,
  - local Chroma vectors as a temporary accepted risk.
- Production readiness currently requires durable SQL and explicit acceptance/monitoring of temporary local vector risk.
- Full durable vector migration remains a next-phase milestone.
- Canonical reference: `docs/HYBRID_STRATEGY_HISTORY_AND_GUIDE.md`.

## 9) Voting Window and Monthly Scope

- Voting month is computed as the next calendar month.
- Voting UI prominently shows the target month and deadline.
- Voting is intended to open on Friday of the last week of the current month and close on day 1 of the target month (UTC), and the app enforces open/closed state in UI.
- If strict target-month curation yields zero cards, fallback curation shows upcoming website-sourced events to avoid an empty voting screen.

## 10) Curation Policy for Voting Cards

- Voting cards are websites-only (`source == "scraped"`), capped at 30 cards.
- Event quality ranking uses text richness and priority keyword scoring.
- Generic roundup/listicle records (for example "Top X things to do") should not appear as standalone events when itemized extraction is available.
- Event schedule display on cards follows:
  - single-date events: specific event date,
  - bounded date ranges: short range label (for example, `Aug 19 - Aug 21`),
  - recurring/multi-date/unclear patterns: `Multiple dates`.

## 11) Landing and Session Date Boundaries

- Landing screen includes a hero image (`assets/yescount-hero.png`) with fallback branding if the image is missing.
- A full-width top banner (`assets/yescount_banner.png`) is rendered on all pages.
- Session creation date range is hard-capped to 31 days from selected start date:
  - UI cap via `st.date_input(max_value=...)`,
  - server-side guard before session creation.

## 12) Availability UX Simplification

- Availability is simplified to a single evening slot per day (`19:00-22:00`).
- Each day uses explicit tri-state selection:
  - `No response`,
  - `Available`,
  - `Unavailable`.

## 13) Event Card Presentation

- Event cards use a 3-column masonry layout (dynamic card heights).
- If event media is missing, a colorful branded placeholder is shown to preserve visual continuity.
- Card vote checkbox copy is `Yes! Count me in!`.
- Card titles and summaries are LLM-generated in batch with session cache fallback.

## 14) Ingestion Error Handling

- Ingestion now rolls back failed DB transactions before finalizing run status to avoid Postgres `InFailedSqlTransaction` cascades.
- CLI ingestion exits non-zero when run status is `failed`.
