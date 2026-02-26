# YesCount Acceptance Criteria Matrix

This matrix maps core PRD requirements to testable acceptance outcomes.

## Frontend

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| FE-01 | Landing create/join split | Landing shows create + join sections; create requires plan and connector names; join requires session id/url and participant name. |
| FE-02 | Session welcome routing | `?session=<uuid>` routes to welcome view with preview data for valid sessions. |
| FE-03 | Name validation | Participant names must be 1-50 chars and match allowed charset; invalid names show inline error and prevent submit. |
| FE-04 | Swipe voting | Yes/Skip writes a vote and advances only when write succeeds. |
| FE-05 | Search behavior | Search query max length 500; long or blank-after-trim queries are blocked; timeout surfaces retry-friendly error. |
| FE-06 | Filter application | Date, price, vibe filters reduce visible event stack deterministically. |
| FE-07 | Calendar editing | Participant can toggle 3 daily time slots and persist values to backend. |
| FE-08 | Group results | Results view renders top recommendations and overlap heatmap without edit controls for participants in locked sessions. |
| FE-09 | Navigation | Breadcrumb and back flow preserve logical progression landing -> swipe -> availability -> results. |
| FE-10 | Accessibility baseline | Keyboard traversal works for interactive controls and contrast remains readable in heatmap tiers. |

## Backend

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| BE-01 | SQLite schema | All tables exist with expected constraints and indices; migration runner records applied migrations. |
| BE-02 | Session lifecycle | Session supports create, preview, join, lock, archive, validity checks with correct status transitions. |
| BE-03 | Idempotent joins | Re-joining same normalized name returns existing participant record in session. |
| BE-04 | Vote persistence | Vote upsert enforces one vote per `(session, participant, event)` and supports updates. |
| BE-05 | Availability persistence | Availability upsert enforces one slot per `(session, participant, date, start, end)`. |
| BE-06 | Overlap computation | Group availability overlap = participants_in_slot / total_participants and is stable across reruns. |
| BE-07 | Recommendation ranking | Composite score uses configured weights and tie-break ordering. |
| BE-08 | Retrieval fallback | Retriever returns semantic results when vector index works and falls back to SQLite when vector query fails. |
| BE-09 | OpenAI resilience | SDK calls use explicit timeout/retries and typed exception handling for reliable errors. |
| BE-10 | Startup checks | Missing critical env vars fail startup validation with actionable errors. |

## Testing / CI

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| QA-01 | Test layout | `tests/` mirrors module structure with shared fixtures in `tests/conftest.py`. |
| QA-02 | Coverage gates | CI enforces minimum overall coverage threshold and reports module-level misses. |
| QA-03 | Integration suites | Session flow and retrieval/recommendation integration tests run in CI and pass. |
| QA-04 | Smoke markers | Smoke tests are marker-driven and runnable independently. |
| QA-05 | Security checks | SQL parameterization and name validation checks are covered by tests. |
| QA-06 | Flaky policy | Known flaky tests are explicitly marked and quarantined rather than silently retried. |
