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

- Streamlit Cloud ephemeral storage is accepted for MVP.
- Production-readiness requires migration to durable SQL and vector stores.
- Migration path and rollback checks are release-gated.
