# Recall Improvement Program (Planning Only)

Owner: Product + Engineering  
Status: Planning approved, execution deferred  
Last updated: 2026-03-02

---

## 1) Purpose

This document defines a comprehensive, execution-ready plan to improve event retrieval quality and recall without implementing code yet.

It is designed so implementation can begin directly from this plan in the next session.

---

## 2) Problem Overview

The current pipeline still produces wrong or noisy results because event detection is mostly heuristic and date handling can promote ambiguous records into valid-looking events.

### Confirmed current-state issues (latest code review)

1. **Scraped invalid dates can be coerced to current timestamp** in ingestion, which makes ambiguous/non-event content look upcoming.
2. **Swipe selection path is SQL + curation driven**, and does not consistently use the semantic retrieval path for card selection.
3. **Non-event filtering is keyword-based**, not semantic; false positives remain when text contains date/location but is not a concrete event.
4. **No robust JSON-LD/schema.org Event-first extraction** is in place, so structured high-confidence event parsing is underused.
5. **Vector retrieval lacks explicit score thresholding** in final selection flow, allowing weak matches to survive.
6. **LLM text generation can polish weak candidates** because generation is not fully grounded to canonical verified fields.

### Why wrong results happen

- Pipeline currently accepts noisy candidates too early.
- Date confidence and provenance are not first-class gates.
- Semantic "is this truly an event?" validation happens too late or not at all in deterministic gating.
- Presentation quality can hide retrieval quality problems.

---

## 3) Desired Solution State

### Business-level target

- Users see high-quality NYC events with stable feed volume and materially fewer false positives.
- Event date shown is the event date from semantic meaning, never article publish date fallback.
- A+ sources remain primary truth; Eventbrite and Ticketmaster NYC-hosted events are added as API-first supplemental boost sources.

### Policy targets (confirmed)

- In-person NYC events only.
- Free and paid events allowed.
- Ticketed/registerable events only.
- Exclude editorial/news mentions unless they contain a concrete listing.
- Date must come from event semantics (not article metadata date).

---

## 4) Guiding Principles

1. **Verify before rank**: semantic and deterministic gates before retrieval/ranking.
2. **Structured-first extraction**: JSON-LD/Event schema first, HTML fallback second.
3. **Provenance everywhere**: every surfaced card carries source and evidence metadata.
4. **Separation of concerns**: candidate extraction, event validation, retrieval, and generation are independently observable.
5. **Safe rollout**: phase gates, measurable checkpoints, and rollback paths for each milestone.

---

## 5) Multi-Faceted Execution Plan

## Milestone M1: Stabilize Inputs and Diagnostics

### Scope

- Remove date coercion behavior that turns unknown scraped dates into "now".
- Add provenance for extraction/date decisions.
- Add visibility on why items are accepted/rejected.

### Implementation outcomes

- `event_date_source`, `date_confidence`, `date_evidence`, `extraction_method` fields captured.
- Ingestion summary includes counts by reject reason and source.
- Swipe diagnostics expose stage counts: total candidates -> curated -> date-window -> final 30.

### Test points

- Unit tests for invalid date handling (no fallback-to-now for scraped unknown date).
- Ingestion test confirms reject/quarantine path for unclear date records.
- Logging validation test confirms reason-code counters are emitted.

### Exit criteria

- No ambiguous scraped date is silently promoted to current date.
- Operators can trace exactly why each candidate was dropped or surfaced.

---

## Milestone M2: Semantic Event Validation Layer

### Scope

- Add LLM semantic validator with strict JSON output schema.
- Enforce deterministic quality gates after semantic classification.

### Implementation outcomes

- Candidate classification fields: `is_event`, `confidence`, `event_type`, `event_date`, `venue`, `ticket_signal`, `evidence_spans`.
- Deterministic policy gates enforce NYC in-person + ticket/register + valid event date.
- Lifecycle state introduced: `candidate`, `verified`, `rejected_non_event`, `expired`.

### Test points

- Gold-set evaluation on labeled examples (event vs non-event).
- Contract tests for LLM output schema compliance.
- Regression tests for known false positives (editorials/listicles/news items).

### Exit criteria

- Non-event false positives reduced materially on validation set.
- Every `verified` event has evidence-backed event date and ticket/register signal.

---

## Milestone M3: Retrieval and Ranking Hardening

### Scope

- Introduce thresholded retrieval and confidence-aware reranking.
- Make verified-event filtering mandatory in card selection.

### Implementation outcomes

- Hybrid retrieval (lexical + vector) with score thresholds.
- Metadata filters: only `verified` + non-expired by default.
- Rerank formula combines relevance, confidence, date-fit, freshness, and source trust tier.
- `app.py` selection flow consistently consumes hardened retrieval output.

### Test points

- Retrieval quality tests (precision@30, nDCG proxy, bad-result suppression rate).
- A/B replay against current baseline with same ingestion snapshot.
- Failover tests for vector outage (SQLite fallback remains deterministic).

### Exit criteria

- Top 30 feed quality improves against baseline in blinded review.
- Weak semantic matches are consistently filtered before UI.

---

## Milestone M4: Grounded Generation and UX Explainability

### Scope

- Restrict LLM title/summary generation to canonical verified fields.
- Add optional explainability indicators for admins/operators.

### Implementation outcomes

- Generation prompt/policy disallows adding facts absent in canonical event record.
- Low-confidence items use deterministic non-LLM fallback copy.
- Explainability mode shows source, confidence band, and date provenance.

### Test points

- Prompt regression tests for hallucination suppression.
- Snapshot tests on summary format and fact fidelity.
- Manual QA pass in swipe/results on 30-card set.

### Exit criteria

- Generated copy does not introduce unsupported factual claims.
- Users/admins can inspect why a card appeared.

---

## Milestone M5: Eventbrite + Ticketmaster NYC Boost Sources (API-First)

### Scope

- Integrate Eventbrite and Ticketmaster ingestion adapters as supplemental NYC source channels.

### Implementation outcomes

- API-first source connectors with source-specific normalization.
- Deduping against A+ sources (title/date/venue/url fingerprint + fuzzy checks).
- Trust weighting that keeps A+ sources primary.

### Test points

- Connector integration tests (auth, pagination, rate-limit behavior).
- NYC-only filter validation.
- Dedup quality checks on mixed source runs.

### Exit criteria

- Supplemental recall improves without degrading precision of top 30.
- Duplicate event rate remains within agreed threshold.

---

## 6) Cross-Cutting Testing and Quality Framework

### A. Dataset and Evaluation Harness

- Build and maintain a labeled replay set:
  - true event listings,
  - non-event editorials/news/listicles,
  - edge cases (recurring events, ranges, ambiguous dates).
- Evaluate per milestone on the same fixed dataset.

### B. Core Metrics

- `precision_at_30` (primary surface metric).
- `false_positive_rate` (non-event in top 30).
- `date_correctness_rate` (event-date fidelity).
- `verified_coverage` (share of surfaced events with full evidence).
- `duplicate_rate` across all sources.

### C. Operational Metrics

- Per-source extraction yield and verification pass rate.
- Reject reasons distribution.
- LLM validator abstain/retry rate and schema-failure rate.
- Generation fallback rate.

### D. Release Gates

- Gate 1: tests green (lint/type/pytest + retrieval/evaluation suite).
- Gate 2: manual QA path (`create -> swipe -> availability -> results`) green.
- Gate 3: ingestion run quality report meets threshold.
- Gate 4: rollback steps verified before merge/deploy.

---

## 7) Risks and Mitigations

1. **Over-filtering reduces feed volume**  
   Mitigation: calibrated thresholds + controlled fallback strategy and explicit minimum feed-size policy.

2. **Source HTML/API changes break extraction**  
   Mitigation: source adapters + monitoring + fail-open strategy only for non-critical sources.

3. **LLM variance in semantic classifier**  
   Mitigation: strict JSON schema, deterministic post-gates, and conservative confidence thresholds.

4. **Latency/cost growth**  
   Mitigation: batch classification, caching, and two-pass validation only for borderline candidates.

---

## 8) Execution Readiness Checklist (For Tomorrow)

Before starting implementation, confirm:

1. Branching strategy and checkpoint tags are prepared.
2. Milestone order accepted (M1 -> M2 -> M3 -> M4 -> M5).
3. Evaluation thresholds are finalized (minimum precision/date correctness targets).
4. Source policy confirmed (A+ primary, Eventbrite/Ticketmaster supplemental boost).
5. Regression dataset location and owners are assigned.

---

## 9) Out of Scope for This Planning Document

- No code implementation.
- No database migration execution.
- No deployment changes.
- No CI/workflow modifications.

This document is planning-only and intentionally non-executable until explicitly authorized.
