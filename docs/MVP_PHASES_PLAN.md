# YesCount MVP Phases Plan

Owner: Product + Engineering  
Last updated: 2026-02-27

---

## 1) MVP Baseline Safety (Current Stable Version)

### What is the current MVP baseline?

The current known-good MVP baseline is locked and restorable:

- **Tag (immutable snapshot):** `mvp-stable-2026-02-27`
- **Backup branch:** `release/mvp-stable-2026-02-27`
- **Snapshot commit:** `013c8b1`

This baseline is the fallback point if future changes cause weekly ingestion, CI, or runtime issues.

### Baseline verification evidence (recorded)

The following validation evidence is tied to the MVP baseline window and can be reused as long as code is unchanged:

- **Commit at baseline:** `013c8b1`
- **CI status (latest relevant):**
  - `22504141061` (CI) -> success
  - `22503338246` (CI) -> success
- **Weekly ingestion status:**
  - `22503551651` (Weekly Ingestion) -> success
  - run log includes `run_status=success total_events=13949`
  - no `InFailedSqlTransaction` in latest successful run
- **Automated test evidence (local):**
  - full test suite: `77 passed`
  - ingestion-focused regressions: `11 passed`
  - smoke/readiness subset: `6 passed`
- **Manual functional evidence (MVP):**
  - create session -> vote -> availability -> results confirmed working in live app.

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
git checkout mvp-stable-2026-02-27
```

#### Option B: Restore `main` to baseline via revert-forward approach (recommended operationally)

1. Create a recovery branch from the baseline tag:

```powershell
git checkout -b recovery/from-mvp-stable mvp-stable-2026-02-27
git push -u origin recovery/from-mvp-stable
```

2. Open a PR from `recovery/from-mvp-stable` to `main`, review, and merge.

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

## 3) MVP Version 3.0 (Quality Expansion Plan)

### Goal

Build on MVP 2.0 and improve event quality further, while still keeping risk managed and reversible.

### Scope planned for MVP 3.0

In addition to MVP 2.0, implement:

1. **Curation + source-specific scraper improvements for SecretNYC**  
   (quick quality pass plus targeted extraction improvements).
2. **Aggressive non-event filtering** in curation.
3. **Use relaxed fill behavior (6B):** if quality filter is strict, allow controlled backfill to avoid empty experience.
4. **Apply category exclusions (7):** aggressively exclude non-event categories.
5. **Mandatory-source evaluation mode (9A):** test and report if mandatory sources are bot-blocked/noisy, then decide operational policy.
6. **NYC Open Data set to non-required (10B)** for runtime resilience.
7. **Placeholder design update (11B):** switch placeholders to palette aligned with `assets/YesCount_color_scheme.png`.
8. **Keep safe image fallback behavior (12 = yes).**
9. **Keep full-month calendar for all users (13 = yes).**
10. **Keep updated availability title text (14 = yes).**
11. **Run full verification suite (15B):** lint + mypy + full pytest + ingestion validation.

### MVP 3.0 risk notes

- Source-specific scraper tweaks are medium risk due to upstream HTML variability.
- Aggressive filtering can over-prune if not tuned.
- Mitigation: phased rollout and compare event output quality against MVP 2.0 before full rollout.

---

## 4) Release and Rollback Operating Rules

### Rule 1: Baseline always preserved

Do not move or retag `mvp-stable-2026-02-27`.

### Rule 2: Every phase deploy must be recoverable

For each new phase:

- Create a pre-phase checkpoint tag.
- Keep changes in a dedicated branch until verified.

### Rule 3: Do not run ingestion on unpushed code

Always commit + push before triggering Weekly Ingestion.

### Rule 4: If CI/ingestion fails, stabilize first

Prefer temporary source disabling/non-required handling over risky late-night architecture changes.

---

## 5) Suggested Execution Order From Here

1. Implement MVP 2.0 scoped changes (single commit).
2. Validate locally (lint/type/tests).
3. Push and deploy.
4. Run Weekly Ingestion manually.
5. Run Agent D signoff checklist.
6. Decide `GO` / `GO with conditions`.
7. Plan MVP 3.0 branch and begin staged implementation.

