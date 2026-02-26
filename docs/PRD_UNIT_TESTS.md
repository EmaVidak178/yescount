# YesCount -- Unit Tests PRD

> Sub-PRD of [PRD_MASTER.md](PRD_MASTER.md)

---

## 1. Overview

This document defines the testing strategy for YesCount: framework choice, directory layout, coverage targets, test categories with concrete examples, shared fixtures, and the mocking approach for external services (OpenAI, Socrata API, web scraping targets).

---

## 2. Framework and Tooling

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner |
| `pytest-cov` | Coverage reporting |
| `pytest-mock` | `mocker` fixture (thin wrapper over `unittest.mock`) |
| `responses` | Mock HTTP requests to Socrata API and scraping targets |
| `freezegun` | Freeze `datetime.now()` for time-dependent tests |

All test dependencies go in `requirements-dev.txt`.

---

## 3. Directory Structure

The `tests/` directory mirrors `src/`:

```
tests/
├── conftest.py                 # Shared fixtures
├── ingestion/
│   ├── test_nyc_open_data.py
│   ├── test_web_scraper.py
│   └── test_normalizer.py
├── db/
│   ├── test_sqlite_client.py
│   └── test_chroma_client.py
├── rag/
│   ├── test_embedder.py
│   ├── test_retriever.py
│   └── test_llm_chain.py
├── engine/
│   ├── test_voting.py
│   ├── test_availability.py
│   ├── test_recommender.py
│   └── test_admin_rules.py
├── sessions/
│   └── test_manager.py
└── utils/
    └── test_invite_text.py
```

---

## 4. Coverage Targets

| Scope | Target |
|-------|--------|
| Backend logic (`src/engine/`, `src/rag/`, `src/sessions/`) | 80%+ line coverage |
| Data layer (`src/db/`, `src/ingestion/`) | 75%+ line coverage |
| Utilities (`src/utils/`) | 90%+ line coverage |
| Overall project | 60%+ line coverage |

Coverage is enforced in CI via `pytest --cov=src --cov-fail-under=60`.

**Coverage policy requirements:**
- Coverage checks are blocking in CI.
- Critical modules (`src/engine/`, `src/rag/`, `src/sessions/`) should not regress below their target bands.
- PRs that lower overall coverage below threshold are not releasable.

---

## 5. Test Categories and Examples

### 5.1 Ingestion Tests

**`tests/ingestion/test_nyc_open_data.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_fetch_events_success` | Given a mocked 200 response with 3 events, `fetch_events()` returns a list of 3 dicts |
| `test_fetch_events_pagination` | Given 2 pages of 1000 events each plus a final page of 50, `fetch_all_events()` returns 2050 events |
| `test_fetch_events_rate_limit_retry` | Given a 429 on the first call and 200 on the second, the function retries and succeeds |
| `test_fetch_events_server_error` | Given a 500 after all retries, raises `IngestionError` |
| `test_fetch_events_filters_past` | Verifies the SoQL `$where` clause excludes events before the cutoff date |

**`tests/ingestion/test_web_scraper.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_scrape_site_parses_events` | Given mock HTML matching a `SiteConfig`, returns normalized event dicts |
| `test_scrape_site_handles_missing_fields` | When a required CSS selector matches nothing, the event is skipped with a warning |
| `test_scrape_all_aggregates` | Given 2 site configs, returns combined events from both |

**`tests/ingestion/test_normalizer.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_normalize_nyc_open_data_full` | A complete Socrata row maps correctly to all `events` columns |
| `test_normalize_nyc_open_data_minimal` | A row with only required fields produces valid output with defaults |
| `test_parse_date_iso` | `"2026-03-15T19:00:00"` -> `"2026-03-15T19:00:00"` |
| `test_parse_date_human` | `"Sat, Mar 15 at 7 PM"` -> `"2026-03-15T19:00:00"` |
| `test_parse_price_free` | `"Free"` -> `(0.0, 0.0)` |
| `test_parse_price_range` | `"$10-$25"` -> `(10.0, 25.0)` |
| `test_parse_price_single` | `"$15"` -> `(15.0, 15.0)` |
| `test_parse_price_unknown` | `""` -> `(None, None)` |
| `test_extract_vibe_tags` | `"An immersive artsy experience"` -> `["immersive", "artsy"]` |
| `test_extract_vibe_tags_none` | `"A regular event"` -> `[]` |

### 5.2 Database Tests

**`tests/db/test_sqlite_client.py`**

All tests use an in-memory SQLite database (`:memory:`) with migrations applied in a fixture.

| Test | What It Verifies |
|------|-----------------|
| `test_upsert_event_insert` | New event is inserted; returns a valid row id |
| `test_upsert_event_update` | Re-inserting with same `(source, source_id)` updates fields |
| `test_get_events_no_filter` | Returns all events |
| `test_get_events_date_filter` | Only returns events within the specified date range |
| `test_get_events_price_filter` | Only returns events at or below the price threshold |
| `test_create_session` | Returns a valid UUID; row is retrievable |
| `test_add_participant_unique` | Adding the same name twice to a session raises `IntegrityError` |
| `test_upsert_vote` | Initial insert works; re-upserting changes the `interested` value |
| `test_upsert_availability` | Slot is persisted; re-upserting is idempotent |
| `test_cascade_delete_session` | Deleting a session cascades to participants, votes, and availability |

**`tests/db/test_chroma_client.py`**

Uses ChromaDB's ephemeral (in-memory) client.

| Test | What It Verifies |
|------|-----------------|
| `test_upsert_and_query` | Upsert 5 events; query returns closest match by cosine similarity |
| `test_metadata_filter` | Query with `where={"price_min": {"$lte": 20}}` excludes expensive events |
| `test_delete_event` | After delete, the event no longer appears in query results |
| `test_upsert_batch` | Batch-upserting 100 events succeeds and all are queryable |

### 5.3 RAG Tests

**`tests/rag/test_embedder.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_embed_text_returns_vector` | Mocked OpenAI call returns a 1536-dim list of floats |
| `test_embed_batch_chunks` | A batch of 250 texts is split into 3 API calls (100, 100, 50) |
| `test_embed_text_retry_on_rate_limit` | 429 triggers retry; second call succeeds |

**`tests/rag/test_retriever.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_retrieve_events_returns_full_records` | Given mocked ChromaDB results, the output includes full SQLite event data |
| `test_retrieve_events_with_date_filter` | `date_range` param is passed as a `$where` clause to ChromaDB |
| `test_retrieve_events_with_price_filter` | `price_max` param filters via metadata |
| `test_retrieve_events_empty_results` | Returns an empty list (not an error) when no events match |

**`tests/rag/test_llm_chain.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_summarize_events_prompt` | The prompt sent to OpenAI includes the query and all event titles |
| `test_summarize_events_response` | Mocked GPT response is returned as-is |
| `test_generate_event_card_json` | Returns a dict with `tagline` and `vibe` keys |

### 5.4 Engine Tests

**`tests/engine/test_voting.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_cast_vote_yes` | Persists a vote with `interested=True` |
| `test_cast_vote_skip` | Persists a vote with `interested=False` |
| `test_cast_vote_update` | Changing from skip to yes updates the existing row |
| `test_get_vote_tallies` | 3 yes + 1 skip on event A -> `VoteTally(yes_count=3, total_votes=4)` |
| `test_get_participant_votes` | Returns only votes for the specified participant |

**`tests/engine/test_availability.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_set_availability_persists` | Slots are stored in the DB |
| `test_set_availability_replaces` | Re-submitting replaces previous slots for the same participant |
| `test_get_group_availability` | Returns correct `{date: {slot: [names]}}` structure |
| `test_compute_overlap_matrix_full` | All 3 participants available on Friday 7-9pm -> `overlap_score=1.0` |
| `test_compute_overlap_matrix_partial` | 2 of 4 available -> `overlap_score=0.5` |
| `test_compute_overlap_matrix_none` | No overlapping slots -> empty matrix |

**`tests/engine/test_recommender.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_compute_recommendations_basic` | Event with 3/3 yes votes and 1.0 overlap scores highest |
| `test_compute_recommendations_admin_weight` | An event matching admin vibe tags scores higher than one that doesn't, all else equal |
| `test_compute_recommendations_tiebreaker_price` | Equal scores -> lower-price event ranks first |
| `test_compute_recommendations_tiebreaker_date` | Equal scores and price -> earlier-date event ranks first |
| `test_compute_recommendations_top_n` | Only top-N results are returned |
| `test_rank_events_only` | Pre-availability ranking uses interest scores only |

**`tests/engine/test_admin_rules.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_load_preferences_defaults` | Empty JSON -> all defaults (no budget cap, no vibe tags, etc.) |
| `test_load_preferences_full` | Fully populated JSON -> correct `AdminPreferences` fields |
| `test_apply_hard_filters_budget` | Event with price $60 is excluded when `budget_cap=50` |
| `test_apply_hard_filters_blackout` | Event on a blackout date is excluded |
| `test_apply_hard_filters_date_range` | Event outside date range is excluded |
| `test_compute_admin_score_full_match` | Event with all preferred vibe tags -> `1.0` |
| `test_compute_admin_score_partial_match` | Event with 1 of 3 preferred tags -> `~0.33` |
| `test_compute_admin_score_no_prefs` | No vibe tags in preferences -> `1.0` (neutral) |

### 5.5 Session Tests

**`tests/sessions/test_manager.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_create_session_returns_uuid` | Returns a valid UUID v4 string |
| `test_get_session_url` | URL format matches `{base_url}?session={uuid}` |
| `test_join_session_success` | Returns participant ID; participant appears in DB |
| `test_join_session_locked` | Raises an error when session status is `locked` |
| `test_join_session_expired` | Raises an error when `expires_at` is in the past |
| `test_join_session_duplicate_name` | Second join with the same name returns the existing participant ID (idempotent) |
| `test_lock_session` | Status transitions from `open` to `locked` |
| `test_archive_session` | Status transitions to `archived` |
| `test_is_session_valid_true` | Open, non-expired session returns `True` |
| `test_is_session_valid_false_archived` | Archived session returns `False` |
| `test_get_session_summary` | Returns correct counts for participants, votes, availability |

### 5.6 Utility Tests

**`tests/utils/test_invite_text.py`**

| Test | What It Verifies |
|------|-----------------|
| `test_generate_invite_includes_title` | Output contains the event title |
| `test_generate_invite_includes_date` | Output contains the formatted date |
| `test_generate_invite_includes_attendees` | Output lists all attendee names |
| `test_generate_invite_includes_url` | Output contains the event URL |
| `test_generate_invite_includes_session_url` | Output contains the session shareable link |
| `test_generate_invite_free_event` | Price display shows "Free" instead of "$0" |

---

## 6. Shared Fixtures (`tests/conftest.py`)

### 6.1 Database Fixtures

```python
@pytest.fixture
def sqlite_db(tmp_path):
    """In-memory SQLite DB with all migrations applied."""
    db_path = ":memory:"
    conn = sqlite3.connect(db_path)
    apply_all_migrations(conn)
    yield conn
    conn.close()

@pytest.fixture
def chroma_client():
    """Ephemeral ChromaDB client (in-memory, no persistence)."""
    import chromadb
    client = chromadb.Client()
    yield client
```

### 6.2 Sample Data Factories

```python
def make_event(**overrides) -> dict:
    """Return a valid event dict with sensible defaults."""
    defaults = {
        "title": "Test Event",
        "description": "A fun test event in NYC.",
        "date_start": "2026-03-15T19:00:00",
        "date_end": "2026-03-15T21:00:00",
        "location": "Central Park",
        "price_min": 0.0,
        "price_max": 0.0,
        "url": "https://example.com/event",
        "source": "nyc_open_data",
        "source_id": "test_001",
        "raw_json": "{}",
        "vibe_tags": '["outdoor", "free"]',
    }
    return {**defaults, **overrides}

def make_session(**overrides) -> dict:
    defaults = {
        "id": "test-session-uuid",
        "name": "Friday Plans",
        "created_by": "Alice",
        "admin_preferences_json": "{}",
        "status": "open",
        "expires_at": "2026-03-22T00:00:00",
    }
    return {**defaults, **overrides}

def make_participant(**overrides) -> dict:
    defaults = {
        "session_id": "test-session-uuid",
        "name": "Bob",
    }
    return {**defaults, **overrides}
```

### 6.3 OpenAI Mock

```python
@pytest.fixture
def mock_openai(mocker):
    """Mock OpenAI client for embeddings and chat."""
    mock_client = mocker.patch("src.rag.embedder.OpenAI")
    mock_client.return_value.embeddings.create.return_value.data = [
        mocker.Mock(embedding=[0.1] * 1536)
    ]
    mock_client.return_value.responses.create.return_value.output_text = (
        "Here are some great events..."
    )
    return mock_client
```

---

## 7. Mocking Strategy

| External Dependency | Mock Approach |
|--------------------|---------------|
| OpenAI Embeddings API | `unittest.mock.patch` on `OpenAI` client; return fixed 1536-dim vectors |
| OpenAI Chat API | `unittest.mock.patch` on `OpenAI` client; return canned response text |
| Socrata HTTP API | `responses` library to intercept `requests.get` calls to `data.cityofnewyork.us` |
| Web scraping HTTP | `responses` library to return canned HTML for target URLs |
| `datetime.now()` | `freezegun.freeze_time` decorator to pin the current time |
| ChromaDB | Use `chromadb.Client()` (ephemeral mode) -- no mock needed, real in-memory instance |
| SQLite | Use `:memory:` database -- no mock needed, real in-memory instance |

**Guiding principle:** Mock at the network boundary (HTTP calls, API clients). Use real implementations for in-process dependencies (SQLite, ChromaDB) to maximize test fidelity.

---

## 8. Running Tests

```bash
# Full suite with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Fast mode (fail on first error)
pytest tests/ -x -q

# Single module
pytest tests/engine/test_recommender.py -v

# With coverage enforcement
pytest tests/ --cov=src --cov-fail-under=60
```

---

## 9. Integration Tests

Integration tests verify cross-module behavior using real in-process dependencies.

### 9.1 Required integration suites

| Suite | What It Covers |
|------|-----------------|
| `tests/integration/test_session_flow.py` | End-to-end backend flow: create session -> join participants -> cast votes -> submit availability -> compute recommendations |
| `tests/integration/test_rag_pipeline.py` | Query embedding -> Chroma retrieval -> SQLite join -> summary generation contract |
| `tests/integration/test_persistence_consistency.py` | SQLite + Chroma consistency after ingest/update/delete paths |
| `tests/integration/test_locking_and_idempotency.py` | Concurrent/duplicate lock and duplicate join behavior is deterministic |

### 9.2 Integration environment

- Use SQLite with migrations applied (not mocked).
- Use ephemeral ChromaDB (not mocked).
- Mock only network boundaries (OpenAI, Socrata, external scraping HTTP).

---

## 10. Smoke and End-to-End Tests

A lightweight smoke suite must validate the critical user journey before release:

1. Create session.
2. Join session from share link.
3. Swipe Yes/Skip.
4. Submit availability.
5. View recommendations and generate invite text.

Implementation options:
- Preferred: Playwright browser tests against Streamlit app.
- Minimum fallback: API/module-level smoke tests that cover the same journey.

---

## 11. Release Criteria

A release is eligible only when all criteria pass:

- CI gates pass (`lint`, `typecheck`, `test`, secrets scan).
- Coverage threshold passes (`--cov-fail-under=60` minimum).
- Integration suite passes.
- Smoke/E2E suite passes for the critical journey.
- No unresolved critical test failures.
- Performance and security checks (Sections 13 and 14) pass for release scope.

---

## 12. Flaky Test Policy

- Tests must be deterministic: fixed time (`freezegun`), isolated fixtures, no shared mutable state.
- CI retry policy: at most 1 automatic retry for explicitly quarantined flaky tests.
- Any test failing in both attempts is a hard failure.
- Flaky tests must be tracked and fixed; quarantine is temporary and must be ticketed.

---

## 13. Security Tests

Required security-oriented tests include:

- Input validation tests for participant names and search queries.
- Session handling tests for expired/locked/invalid session IDs.
- Injection safety tests ensuring SQL operations remain parameterized.
- Secret-handling tests verifying keys are not emitted in logs/errors.
- Rate-limit behavior tests for public preview/session endpoints.

---

## 14. Performance Regression Tests

Required performance checks tied to NFRs:

- Retrieval latency benchmark for up to 5,000 events.
- Recommendation computation benchmark under expected participant/session load.
- Guardrail: fail performance test suite if latency regresses beyond agreed tolerance (default 20%).

Performance checks may run in a dedicated CI job or nightly schedule, but must run before production release.

---

## 15. Environment Parity

Test/runtime parity requirements:

- Run CI on Python 3.11 and 3.12.
- Use schema+migration path identical to runtime.
- Keep key env vars and feature flags aligned between test and deploy configs.
- Ensure the persistence mode under test matches the targeted deployment mode (ephemeral MVP vs durable production).

---

## 16. Regression Tracking

- Every production bug fix should include a regression test.
- Maintain a tagged regression subset (`pytest -m regression`) for rapid confidence checks.
- Smoke subset (`pytest -m smoke`) runs on every PR and before deploy.
