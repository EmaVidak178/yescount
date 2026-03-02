# YesCount MVP Phases Plan

Owner: Product + Engineering  
Last updated: 2026-03-02

---

## 1) MVP Baseline Safety (Current Stable Version)

### What is the current MVP baseline?

The current known-good MVP baseline is locked and restorable:

- **Tag (immutable snapshot):** `mvp-v1.1-recall-stable-2026-03-02`
- **Backup branch:** `release/mvp-v1.1-recall-stable-2026-03-02`
- **Snapshot commit:** resolved by the tag pointer (authoritative)
- **Docs-only checkpoint tag (planning-only):** `docs-checkpoint-2026-03-02` (does not change runtime/ingestion behavior)

Historical MVP rollback is also preserved:

- **MVP 1.0 tag:** `mvp-stable-2026-02-27`
- **MVP 1.0 backup branch:** `release/mvp-stable-2026-02-27`

This MVP 1.1 baseline is the primary fallback point if future changes cause weekly ingestion, CI, or runtime issues.

### Baseline verification evidence (recorded)

The following validation evidence is tied to the MVP baseline windows and can be reused as long as code is unchanged:

- **MVP 1.0 baseline commit:** `013c8b1`
- **MVP 1.0 CI status (latest relevant):**
  - `22504141061` (CI) -> success
  - `22503338246` (CI) -> success
- **MVP 1.0 Weekly ingestion status:**
  - `22503551651` (Weekly Ingestion) -> success
  - run log includes `run_status=success total_events=13949`
  - no `InFailedSqlTransaction` in latest successful run
- **MVP 1.1 baseline commit:** `8c250e7`
- **MVP 1.1 code safety checks completed before tagging:**
  - forced local ingestion completed successfully (`run_status=degraded` only due to local NYC Open Data config)
  - local event volume check showed recovered scraped recall in the 30-day window
  - ingestion regression tests: `tests/ingestion/test_run_ingestion.py` -> `7 passed`
- **Automated test evidence (historical full-suite):**
  - full test suite: `77 passed`
  - ingestion-focused regressions: `11 passed`
  - smoke/readiness subset: `6 passed`
- **Manual functional evidence (MVP):**
  - create session -> vote -> availability -> results confirmed working in live app.

### MVP 1.1 deployment log (2026-03-02)

- **Release state:** GREEN / successful deployment declared.
- **Code baseline in production:** `8c250e7` (`mvp-v1.1-recall-stable-2026-03-02`).
- **Weekly ingestion verification (GitHub Actions):**
  - run id `22558364297` -> `success`
  - `run_status=success total_events=16212`
  - scraped source outcomes included: `secretnyc=15`, `timeout_newyork=76`, `untappedcities=22`, `fever_newyork=3`
  - `hiddennyc` reported partial (`no events extracted`) and `anisah_immersive` remained intentionally disabled.
- **Manual online verification (Streamlit):**
  - reboot + full click-through test completed successfully
  - organizer and participant core journey confirmed working (`create -> swipe -> availability -> results`)
  - no blocker issues reported.

Operational conclusion: MVP 1.1 is approved as current live baseline for user access.

### Agent D test policy for baseline

For this exact MVP baseline, if **no code changes** are made after snapshot:

- Do **not** rerun full automated test suites just for repetition.
- Reuse the existing validation evidence above for Agent D signoff.
- Capture only lightweight operational evidence if needed (for example, latest app log snapshot).

Full Agent D re-testing is required again after any code change (for example MVP 2.0, MVP 3.0).

### Why this matters

- Protects launch stability.
- Enables fast rollback with minimal downtime.
- Prevents losing a validated working state.

### How to recover to MVP baseline if something breaks

#### Option A: Fast local rollback for emergency test

```powershell
git fetch origin --tags
git checkout mvp-v1.1-recall-stable-2026-03-02
```

#### Option B: Restore `main` to baseline via revert-forward approach (recommended operationally)

1. Create a recovery branch from the baseline tag:

```powershell
git checkout -b recovery/from-mvp-v1.1 mvp-v1.1-recall-stable-2026-03-02
git push -u origin recovery/from-mvp-v1.1
```

If you intentionally want to recover to historical MVP 1.0 instead:

```powershell
git checkout -b recovery/from-mvp-v1.0 mvp-stable-2026-02-27
git push -u origin recovery/from-mvp-v1.0
```

2. Open a PR from the chosen recovery branch to `main`, review, and merge.

#### Option C: Force-reset branch (only with explicit approval)

This is higher risk and should only be used intentionally with explicit owner approval.

---

## 2) MVP Version 2.0 (Low-Risk Upgrade Plan)

### Goal

Ship a safe incremental upgrade in **one commit**, with no ingestion-core refactor and no risky architecture changes.

### Scope locked for MVP 2.0

Apply only these changes:

1. **Remove date display on event cards**.
2. **Card content simplified to title + summary only**.
3. **Curation: quick quality improvements only** (no deep scraper overhaul yet).
4. **If a mandatory source is bot-blocked/noisy: disable source for MVP stability** (temporary operational mitigation allowed).
5. **Keep NYC Open Data setting as-is**.
6. **Keep existing gradient placeholders**.
7. **Ensure image fallback behavior is reliable** (if missing/unusable image, show placeholder cleanly).
8. **Fix calendar to show full month for all users** (not just organizer path).
9. **Change availability title text to:** `Click on evenings when you're available!`

Filter quality intent for this phase:

- MVP 1.0 is broad and not sensitive enough to separate true events from noisy/ad-style content.
- MVP 2.0 will add moderate conditions for high-quality event recognition and additional filtering of ad-style listings, while avoiding over-restriction.

### Implementation constraints

- Single implementation commit for all MVP 2.0 code changes.
- No schema migrations.
- No ingestion transaction model changes.
- No broad pipeline redesign.

### Recommended safety checks for MVP 2.0

Before merge:

- Run lint + typecheck + tests.
- Run targeted UI/manual check:
  - create -> swipe -> availability -> results -> lock.
- Run one manual Weekly Ingestion after deploy.

After merge/deploy:

- Hard refresh app and verify cards/calendar/results.
- Confirm no critical logs/tracebacks.
- Keep baseline tag unchanged for rollback.

---

## 3) MVP Version 1.1 (Recall Recovery Patch)

### Goal

Restore practical event recall volume without reintroducing Postgres timestamp-ingestion failures.

### Why this patch is needed

- Current ingestion hardening correctly prevents timestamp crashes.
- However, many scraped rows with invalid/unclear dates are skipped, reducing website event recall too far.
- Result: swipe can show very few (or zero) events in session range despite successful ingestion.

### MVP 1.1 approach (approved)

1. Keep MVP 2.0 UI changes (date hidden on cards, title+summary focus, calendar updates).
2. Keep ingestion crash protections.
3. For scraped rows only, if `date_start` is invalid/missing, coerce to a safe fallback ISO timestamp during ingestion.
4. Continue logging these coerced rows for traceability.
5. Do not display date on event cards in UI.

### Risk profile

- Lower risk than reverting ingestion guardrails entirely.
- Restores recall while preserving database write safety.
- May include some noisy cards (known temporary tradeoff) until MVP 3.0 curation/source tuning.

### Phase positioning

- MVP 1.1 is the current stable recall-protection baseline.
- It intentionally accepts broader retrieval than strict-quality mode.
- Quality tightening continues in MVP 2.0 and ranking optimization in MVP 3.0.

---

## 4) MVP Version 3.0 (Recall + Quality Program)

### Goal

Build on MVP 2.0 with a structured retrieval-quality program that improves top-30 precision, date correctness, and stable recall while preserving rollback safety.

### Authoritative planning doc for MVP 3.0

MVP 3.0 execution is now governed by:

- `docs/RECALL_IMPROVEMENT.md` (planning-only, implementation-ready roadmap)

That document defines the full problem statement, target architecture, milestones, testing points, risk controls, and release gates.

### MVP 3.0 scope (aligned to RECALL_IMPROVEMENT.md)

In addition to MVP 2.0, MVP 3.0 is executed as five milestones:

1. **M1: Input stabilization + diagnostics**
   - remove invalid scraped date fallback-to-now behavior
   - add date/extraction provenance fields and stage-level diagnostics
2. **M2: Semantic event validation**
   - LLM semantic validator + deterministic policy gates
   - enforce in-person NYC + ticket/register signal + semantic event date policy
3. **M3: Retrieval/ranking hardening**
   - thresholded hybrid retrieval
   - verified-event filtering and confidence-aware reranking
4. **M4: Grounded generation + explainability**
   - constrain summaries to canonical verified fields
   - add operator explainability indicators
5. **M5: Supplemental boost sources**
   - API-first Eventbrite and Ticketmaster NYC ingestion adapters
   - dedupe and trust-weighting without overriding A+ source primacy

### Confirmed policy constraints for MVP 3.0

- Keep A+ sources as primary source-of-truth set.
- Add Eventbrite and Ticketmaster as optional supplemental boost sources.
- Event inclusion policy:
  - in-person NYC only
  - free and paid allowed
  - ticketed/registerable only
  - exclude editorial/news mentions without concrete listing data
- Date policy:
  - event date must come from semantic event meaning
  - do not use article publish date fallback for surfaced cards

### MVP 3.0 risk notes

- Over-filtering risk can reduce feed volume if thresholds are too strict.
- Source/API changes can break extraction adapters unexpectedly.
- Semantic validator variance can create instability if confidence gates are not calibrated.
- Mitigation is milestone gating, replay-dataset regression checks, and explicit before/after evaluation against MVP 2.0 baseline.

---

## 5) Release and Rollback Operating Rules

### Rule 1: Baseline always preserved

Do not move or retag `mvp-v1.1-recall-stable-2026-03-02` or `mvp-stable-2026-02-27`.

### Rule 2: Every phase deploy must be recoverable

For each new phase:

- Create a pre-phase checkpoint tag.
- Keep changes in a dedicated branch until verified.

### Rule 3: Do not run ingestion on unpushed code

Always commit + push before triggering Weekly Ingestion.

### Rule 4: If CI/ingestion fails, stabilize first

Prefer temporary source disabling/non-required handling over risky late-night architecture changes.

---

## 6) Suggested Execution Order From Here

1. Confirm current Weekly Ingestion result for MVP 1.1 code and capture run ID.
2. Reboot app and run manual flow check (create -> swipe -> availability -> results).
3. If pass, mark MVP 1.1 as production-stable checkpoint in deployment notes.
4. Finalize MVP 2.0 validation status (if pending) and keep rollback tags unchanged.
5. Open `docs/RECALL_IMPROVEMENT.md` as the implementation playbook for MVP 3.0.
6. Execute MVP 3.0 in milestone order only: `M1 -> M2 -> M3 -> M4 -> M5`.
7. After each milestone:
   - run defined tests and quality checks from `docs/RECALL_IMPROVEMENT.md`
   - record before/after metrics and release-gate evidence
8. Run Agent D signoff checklist after MVP 3.0 milestone completion.
9. Decide `GO` / `GO with conditions` based on measured quality gates, not intuition.

