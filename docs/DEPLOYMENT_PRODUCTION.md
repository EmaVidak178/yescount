# YesCount Production Deployment Plan

## Goal

Move from MVP deployment (ephemeral local disk on Streamlit Cloud) to reliable user-facing deployment with durable storage, enforced quality gates, and rollback safety.

## Canonical Strategy Reference

- Current operating model is hybrid (Track A ingestion + durable Postgres SQL + local Chroma vectors).
- See `docs/HYBRID_STRATEGY_HISTORY_AND_GUIDE.md` for the latest strategy and rationale.

## 1) Reliability Baseline (must pass before release)

1. CI gates are green on every PR:
   - lint
   - typecheck
   - unit tests + coverage
   - integration tests
   - smoke tests
   - secrets scan (currently non-blocking; CI uses fake keys, real keys in secrets only)
2. Startup validation passes in target environment.
3. Readiness reports all required dependencies as ready.
4. Critical journey smoke test passes after deploy.

## 2) Durable Storage Architecture

### Current production stack (shipped)

- **PostgreSQL**: Hosted Postgres via `DATABASE_URL` for sessions, votes, events, ingestion runs.
- **Chroma**: Local (`data/chroma/`) for vector embeddings; remains on app instance disk.
- **Sources**: 6 website sources in `config/scraper_sites.yaml` (secretnyc, timeout_newyork, hiddennyc, untappedcities, anisah_immersive, fever_newyork).
- Ingestion runs out-of-band via weekly Friday GitHub Actions workflow.

### Future improvements

- Migrate Chroma to managed vector storage for durability across restarts.

## 3) Recommended Rollout Phases

### Phase A - Hardening on current stack

- Keep current app behavior but enforce CI/quality gates.
- Validate startup/readiness dependencies.
- Add release checklist and smoke-test discipline.

### Phase B - Durable data migration

1. Provision managed PostgreSQL.
2. Add SQL migration path from SQLite schema to PostgreSQL.
3. Backfill existing event/session data.
4. Provision durable vector store.
5. Re-index embeddings from canonical event records.
6. Run parity checks: counts, random record sampling, search quality spot checks.

### Phase C - Controlled launch

1. Deploy to staging with production-like infra.
2. Run integration + smoke suites against staging.
3. Start beta with a limited user cohort.
4. Monitor error rate, latency, and data integrity metrics.
5. Promote to production when SLOs are stable for at least 48 hours.

## 4) Backup and Rollback

- Pre-deploy snapshot required before schema or data changes.
- Keep previous release artifact available for immediate rollback.
- If post-deploy readiness fails:
  1. roll back app revision,
  2. restore latest DB snapshot if needed,
  3. re-run smoke journey before reopening access.

## 5) Operations Checklist

### Pre-deploy

- `make ci`
- verify Streamlit secrets are present
- verify `BASE_URL` is production URL (not localhost)
- confirm backup/snapshot completed

### Post-deploy

- [ ] Check readiness/liveness output.
- [ ] Run manual Weekly Ingestion workflow in GitHub Actions; confirm success.
- [ ] Durability: create session, add vote, restart app; confirm data persists.
- [ ] End-to-end: create -> join -> vote -> availability -> recommendations.
- [ ] Verify session links and invite text in real browser.
- [ ] Inspect logs for errors during first user sessions.

## 6) User-Facing Readiness Exit Criteria

The release is user-facing ready only when:

- all CI gates are enforced and passing,
- durable persistence is in place for session/relational data (Postgres),
- vector retrieval is either durable or explicitly accepted as temporary local risk,
- rollback has been tested successfully,
- staged beta traffic has no critical defects.
