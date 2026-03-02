# YesCount Rollback Reference (Beginner Friendly)

Owner: Product + Engineering  
Last updated: 2026-03-02

---

## What this document is for

Use this page as a quick safety map when you need to restore a known-good version.

If anything breaks (deployment issue, ingestion issue, unexpected app behavior), you can recover from one of the saved versions below.

---

## Key safety versions

### Current primary rollback target (recommended first)

- **Version name:** MVP 1.1 recall-safe baseline
- **Tag (fixed snapshot):** `mvp-v1.1-recall-stable-2026-03-02`
- **Safety branch (backup pointer):** `release/mvp-v1.1-recall-stable-2026-03-02`
- **Use this when:** you want stable behavior with recall recovery (broader event availability + ingestion safety protections).

### Historical rollback target

- **Version name:** MVP 1.0 baseline
- **Tag (fixed snapshot):** `mvp-stable-2026-02-27`
- **Safety branch (backup pointer):** `release/mvp-stable-2026-02-27`
- **Use this when:** you need to compare against the earlier baseline or intentionally revert to pre-MVP-1.1 behavior.

---

## Beginner explanation: tags, branches, and rollback

### What is a branch?

A branch is a moving line of development.  
Think of it like a named work lane. Every new commit moves that branch forward.

### What is a tag?

A tag is a fixed bookmark to one exact commit.  
Think of it like a permanent pin in history. It does not move unless someone manually retags it (which we do not do for safety tags).

### What is rollback?

Rollback means returning your app code to a previous known-good snapshot.

Important: in normal team workflows, rollback is usually done by creating a recovery branch from a tag and opening a PR into `main`. That keeps history clean and auditable.

---

## Fast commands you can copy

### 1) See available safety tags

```powershell
git fetch origin --tags
git tag --list "mvp*"
```

### 2) Test a version locally (safe read-only check)

```powershell
git fetch origin --tags
git checkout mvp-v1.1-recall-stable-2026-03-02
```

### 3) Prepare a real rollback branch to restore `main`

```powershell
git fetch origin --tags
git checkout -b recovery/from-mvp-v1.1 mvp-v1.1-recall-stable-2026-03-02
git push -u origin recovery/from-mvp-v1.1
```

Then open a PR from `recovery/from-mvp-v1.1` to `main` and merge after review.

### 4) Restore historical MVP 1.0 instead

```powershell
git fetch origin --tags
git checkout -b recovery/from-mvp-v1.0 mvp-stable-2026-02-27
git push -u origin recovery/from-mvp-v1.0
```

---

## Safety rules

- Do not delete or move these safety tags.
- Always commit and push before triggering Weekly Ingestion.
- If CI or ingestion fails, stabilize first (do not stack risky changes).
- Prefer PR-based rollback over force-reset.

---

## Related docs

- `docs/MVP_PHASES_PLAN.md`
- `docs/DEPLOYMENT_PRODUCTION.md`
- `docs/AGENT_D_FINAL_SIGNOFF_CHECKLIST.md`
