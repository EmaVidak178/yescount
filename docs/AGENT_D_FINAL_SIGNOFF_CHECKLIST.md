# Agent D Final Signoff Checklist

Use this checklist only after Agent A/B/C fixes are merged and a fresh manual ingestion run has completed.

## Goal

Provide a clear go/no-go decision for public sharing.

## Inputs Required

- Latest commit SHA deployed to Streamlit.
- Latest manual Weekly Ingestion run URL and status.
- Streamlit logs snapshot for the latest run window.
- Manual tester notes/screenshots from end-to-end flow.

## Blocking Criteria (must pass)

1. **Runtime health**
   - [ ] No startup validation errors.
   - [ ] Readiness passes (database ready).
   - [ ] No recurring `Traceback`/critical errors in logs.

2. **Data freshness + ingestion**
   - [ ] Latest manual ingestion run is green.
   - [ ] No ingestion transaction-aborted failure (`InFailedSqlTransaction`) in latest run.
   - [ ] Event cards reflect post-ingestion data refresh.

3. **Durability**
   - [ ] Create session -> vote -> restart app -> data persists.
   - [ ] Session links remain valid after restart.

4. **End-to-end product flow**
   - [ ] Create -> join -> vote -> availability -> results works without blocking defects.
   - [ ] Results page renders without TypeError/runtime crash.

5. **Event card quality**
   - [ ] No generic roundup/listicle title shown as a standalone event card.
   - [ ] Date labels are event-specific when clear, otherwise `Multiple dates`.
   - [ ] LLM-generated titles/summaries are readable and relevant.
   - [ ] Card vote control label shows `Yes! Count me in!`.

6. **UI acceptance**
   - [ ] Top banner is full-width on all pages.
   - [ ] Landing hero size is visually acceptable.
   - [ ] Masonry card layout (Option C) renders correctly.
   - [ ] Missing-image cards show styled fallback placeholder (Option E).

## Non-Blocking Observations (log only)

- Minor copy/style nits that do not break flow.
- Occasional source-level weak event descriptions from upstream sites.
- Chroma degraded warnings when core flow remains available.

## Decision Template

- **GO**: All blocking criteria pass.
- **GO with conditions**: One or more low-risk issues accepted with explicit follow-up owner/date.
- **NO-GO**: Any blocking criterion fails.

## Agent D Output Format

1. Decision: `GO` / `GO with conditions` / `NO-GO`
2. Blocking findings (if any), ordered by severity.
3. Evidence summary:
   - commit SHA
   - ingestion run status
   - key screenshots/log snippets
4. Required follow-up actions with owners and due date.
