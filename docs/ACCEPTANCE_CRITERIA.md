# YesCount Acceptance Criteria Matrix

This matrix maps core PRD requirements to testable acceptance outcomes.

## Frontend

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| FE-01 | Landing create/join split | Landing shows hero + create and join cards; create requires plan and connector names; join requires session id/url and participant name. |
| FE-02 | Session welcome routing | `?session=<uuid>` routes to welcome view with preview data for valid sessions. |
| FE-03 | Name validation | Participant names must be 1-50 chars and match allowed charset; invalid names show inline error and prevent submit. |
| FE-04 | Curated voting cards | Swipe view renders up to 30 curated websites-only cards with clear title, short summary, schedule label, location, and optional price metadata. |
| FE-05 | Monthly voting window | Voting view shows target month + deadline and blocks voting interactions when the voting window is closed. |
| FE-06 | Empty-month fallback | If strict target-month curation returns zero events, UI falls back to upcoming websites-only curated cards instead of showing a permanently empty state. |
| FE-07 | Calendar editing | Participant can mark one evening slot per day as `Available`/`Unavailable`/`No response`, and persisted availability maps only `Available` to a stored slot. |
| FE-08 | Group results | Results view renders top recommendations, interested participant names per event, and top overlap dates/times for gathering. |
| FE-09 | Navigation | Breadcrumb and back flow preserve logical progression landing -> swipe -> availability -> results. |
| FE-10 | Accessibility baseline | Keyboard traversal works for interactive controls and contrast remains readable in heatmap tiers. |

## Backend

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| BE-01 | SQLite schema | All tables exist with expected constraints and indices; migration runner records applied migrations. |
| BE-02 | Session lifecycle | Session supports create, preview, join, lock, archive, validity checks with correct status transitions. |
| BE-03 | Idempotent joins | Re-joining same normalized name returns existing participant record in session. |
| BE-04 | Vote persistence | Vote upsert enforces one vote per `(session, participant, event)` and supports updates. |
| BE-05 | Availability persistence | Availability replace/upsert enforces one slot per `(session, participant, date, start, end)` and stores only selected `Available` evening slots. |
| BE-06 | Overlap computation | Group availability overlap = participants_in_slot / total_participants and is stable across reruns. |
| BE-07 | Recommendation ranking | Composite score uses configured weights and tie-break ordering. |
| BE-08 | Retrieval fallback | Retriever returns semantic results when vector index works and falls back to SQLite when vector query fails. |
| BE-09 | OpenAI resilience | SDK calls use explicit timeout/retries and typed exception handling for reliable errors. |
| BE-10 | Startup checks | Missing critical env vars fail startup validation with actionable errors; readiness requires database and treats Chroma as optional/degraded. |

## Testing / CI

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| QA-01 | Test layout | `tests/` mirrors module structure with shared fixtures in `tests/conftest.py`. |
| QA-02 | Coverage gates | CI enforces minimum overall coverage threshold and reports module-level misses. |
| QA-03 | Integration suites | Session flow and retrieval/recommendation integration tests run in CI and pass. |
| QA-04 | Smoke markers | Smoke tests are marker-driven and runnable independently. |
| QA-05 | Security checks | SQL parameterization and name validation checks are covered by tests. |
| QA-06 | Flaky policy | Known flaky tests are explicitly marked and quarantined rather than silently retried. |
