# Beginner Guide: Secrets Setup for YesCount

This guide shows exactly where to click and what to paste so your app can run in Streamlit Cloud and GitHub Actions.

Use this document whenever you redeploy or rotate keys.

## What To Do Next (Short Answer)

Yes, your understanding is correct.

Do this in order:
1. Create your GitHub repository and push your local app code.
2. Set all secrets in Streamlit Cloud and GitHub (steps in this guide).
3. Deploy/restart app.
4. Run one manual ingestion workflow in GitHub Actions.
5. Verify data persists after app restart (critical check for durable Postgres).
6. Perform manual product testing (create session -> join -> vote -> availability -> results).

If all checks pass, you are ready for normal usage and Friday scheduled ingestion.

## What "secret values" mean

A "secret" is a private value (API key/token) that should not be committed to code.

For this project, the important secrets are:
- `OPENAI_API_KEY`
- `NYC_OPEN_DATA_APP_TOKEN`
- `NYC_OPEN_DATA_DATASET_ID`
- `BASE_URL` (not strictly private, but required runtime config in Streamlit)
- `DATABASE_URL` (recommended now for durable PostgreSQL)

## Before You Start

You need:
- A GitHub account with access to your repository.
- A Streamlit Community Cloud account connected to your GitHub.
- An OpenAI API key.
- A NYC Open Data app token.
- The NYC Open Data dataset ID you want to ingest.
- A hosted PostgreSQL database and its connection URL (`DATABASE_URL`).

## Step 0: Create Hosted PostgreSQL (Durable Database)

If you do not already have Postgres, do this first.

### Recommended for beginners: Neon

Follow these exact steps:

1. Open: `https://neon.tech/`
2. Click **Start for free** (or sign in if you already have an account).
3. Click **Create project**.
4. Fill project setup:
   - Project name: e.g., `yescount-prod`
   - Region: choose one close to your users (if unsure, nearest US region is fine)
   - PostgreSQL version: keep default
5. Click **Create project**.
6. In Neon dashboard, open the created project.
7. Click **Connect** or **Connection details**.
8. Select **Connection string** / URI.
9. Copy the full URL.

It usually looks like:
- `postgresql://username:password@hostname:5432/dbname?sslmode=require`

Store this securely. This is your `DATABASE_URL`.

### If you use Supabase or Render instead

That is also okay. The requirement is the same:
- copy the full Postgres connection string (URI)
- use it as `DATABASE_URL`

Example format:
- `postgresql://username:password@hostname:5432/dbname`

Keep this safe. You will use it as `DATABASE_URL`.

Note:
- If your provider also gives `postgres://...`, that is also accepted by this app.
- Do not edit this URL manually unless your provider tells you to.
- Keep SSL in the URL if provider includes it (for Neon this is usually `?sslmode=require`).
- If password has special characters, always use the exact copy button value from provider.

## Step 1: Get `OPENAI_API_KEY`

1. Open: `https://platform.openai.com/`
2. Sign in.
3. Click your profile/avatar (top-right) -> API keys.
4. Click **Create new secret key**.
5. Copy the key immediately (it usually starts with `sk-`).
6. Save it in a temporary safe note for setup.

You will paste this later as:
- key name: `OPENAI_API_KEY`
- value: your full `sk-...` key

## Step 2: Get `NYC_OPEN_DATA_APP_TOKEN`

1. Open: `https://data.cityofnewyork.us/`
2. Sign in or create an account (Socrata account).
3. Open your account/profile menu and go to **Developer settings** (wording may vary).
4. Find **App Tokens** and create a new token.
5. Copy the token value.

You will paste this later as:
- key name: `NYC_OPEN_DATA_APP_TOKEN`
- value: your token string

## Step 3: Get `NYC_OPEN_DATA_DATASET_ID`

The dataset ID is the short identifier in a dataset URL (looks like `xxxx-xxxx`).

Example:
- Dataset URL format often includes `/resource/<dataset-id>.json`
- If URL has `/resource/abcd-1234.json`, dataset ID is `abcd-1234`

How to find:
1. Open the NYC dataset page you want to use.
2. Look for API endpoint or "SODA API" section.
3. Copy the ID portion only (e.g., `abcd-1234`).

You will paste this later as:
- key name: `NYC_OPEN_DATA_DATASET_ID`
- value: `abcd-1234` (example format)

## Step 4: Create GitHub Repository and Push Your Local Code

Streamlit Cloud deploys from GitHub, so this step must happen before Streamlit app creation.

### Part A: Create repository on GitHub website

1. Open: `https://github.com/`
2. Sign in.
3. Click `+` in the top-right corner -> **New repository**.
4. Set:
   - Repository name: e.g., `yescount`
   - Visibility: Public or Private (your choice)
5. Keep these options OFF/empty:
   - Add README: OFF
   - Add `.gitignore`: No `.gitignore`
   - Add license: No license
6. Click **Create repository**.

### Part B: Push your local project from PowerShell

Open PowerShell in:
- `C:\Users\evida\OneDrive\Desktop\ai_app`

Run commands one by one:

```powershell
git init
git add .
git commit -m "Initial YesCount app setup"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

Replace:
- `<your-username>` with your GitHub username
- `<your-repo-name>` with your repository name

### If commit fails (first-time git identity setup)

Run:

```powershell
git config --global user.name "Your Name"
git config --global user.email "your-github-email@example.com"
```

Then retry:

```powershell
git commit -m "Initial YesCount app setup"
git push -u origin main
```

### Confirm success

Refresh your GitHub repo page. You should see files like:
- `app.py`
- `src/`
- `docs/`
- `.github/workflows/`

## Step 5: Set Secrets in Streamlit Cloud (App Runtime)

This is required for your live app to work.

1. Open: `https://share.streamlit.io/`
2. Sign in.
3. Open your app dashboard.
4. Click your app.
5. Click **Settings** (gear icon).
6. Click **Secrets**.
7. Paste this block, replacing placeholder values:

```toml
OPENAI_API_KEY = "sk-your-real-openai-key"
NYC_OPEN_DATA_APP_TOKEN = "your-nyc-open-data-token"
NYC_OPEN_DATA_DATASET_ID = "abcd-1234"
BASE_URL = "https://your-app-name.streamlit.app"
DATABASE_URL = "postgresql://user:password@host:5432/dbname"

SCRAPER_SITES_CONFIG_PATH = "config/scraper_sites.yaml"
INGESTION_AUTO_REFRESH = "false"
INGESTION_MAX_STALENESS_HOURS = "192"
INGESTION_REQUIRED_SOURCES_STRICT = "true"
```

8. Click **Save**.
9. Restart/redeploy app from Streamlit UI.

How to replace values:
- `sk-your-real-openai-key` -> the exact key from Step 1.
- `your-nyc-open-data-token` -> the exact token from Step 2.
- `abcd-1234` -> dataset ID from Step 3.
- `https://your-app-name.streamlit.app` -> your real deployed app URL.
- `postgresql://user:password@host:5432/dbname` -> full Postgres connection string from your DB provider.

Beginner tip:
- If your password contains special characters and your provider gives you an encoded URL, always use the exact URL from provider copy button.

### Exact copy/paste template (safe version)

If you get formatting issues, clear the box and paste this exact block first:

```toml
OPENAI_API_KEY = "YOUR_OPENAI_KEY"
NYC_OPEN_DATA_APP_TOKEN = "YOUR_NYC_APP_TOKEN"
NYC_OPEN_DATA_DATASET_ID = "tvpp-9vvx"
BASE_URL = "https://yescount-nyc.streamlit.app"
DATABASE_URL = "YOUR_NEON_DATABASE_URL"

SCRAPER_SITES_CONFIG_PATH = "config/scraper_sites.yaml"
INGESTION_AUTO_REFRESH = "false"
INGESTION_MAX_STALENESS_HOURS = "192"
INGESTION_REQUIRED_SOURCES_STRICT = "true"
```

Then replace only values inside quotes.

Placement note:
- Paste `INGESTION_AUTO_REFRESH = "false"` in the same secrets block as the other keys.
- It can be anywhere in the block (top, middle, or end), as long as it is one full line in `KEY = "value"` format.

Why we set this to false now:
- On first deployment, automatic startup ingestion can make the app appear blank while long ingestion runs.
- With `false`, app UI loads quickly.
- You will refresh data via manual/scheduled GitHub workflow instead.

### If Streamlit shows: "Invalid format: please enter valid TOML"

This is usually a syntax typo. Fix with this checklist:
- Remove everything and re-paste the template above.
- Make sure every line looks exactly like `KEY = "value"`.
- Use normal double quotes (`"`), not smart quotes (`“ ”`).
- Do not include markdown backticks or comments in the secrets box.
- Keep `DATABASE_URL` on one single line.
- Ensure there are no missing closing quotes.

## Step 6: Set Secrets in GitHub Actions (Weekly Friday Workflow)

This is required for the scheduled ingestion workflow. Weekly ingestion uses the same durable storage as the app, so it needs `DATABASE_URL` and `BASE_URL`.

1. Open your repository on GitHub.
2. Click **Settings** (repo settings, not profile settings).
3. In left sidebar: **Secrets and variables** -> **Actions**.
4. Click **New repository secret** and add each:

### Secret A
- Name: `OPENAI_API_KEY`
- Secret: your real OpenAI key (`sk-...`)

### Secret B
- Name: `NYC_OPEN_DATA_APP_TOKEN`
- Secret: your NYC app token

### Secret C
- Name: `NYC_OPEN_DATA_DATASET_ID`
- Secret: your dataset ID (e.g., `abcd-1234`)

### Secret D (required for durable storage)
- Name: `DATABASE_URL`
- Secret: full PostgreSQL connection URL (same as Streamlit)

### Secret E
- Name: `BASE_URL`
- Secret: your deployed app URL (e.g., `https://your-app.streamlit.app`)

5. Save each secret.

## Step 7: Confirm Friday Workflow Exists and Is Enabled

1. In GitHub repo, click **Actions**.
2. Open workflow named **Weekly Ingestion**.
3. Verify it has:
   - scheduled trigger (Friday)
   - manual trigger (`workflow_dispatch`)
4. For first launch, click **Run workflow** once manually to verify.

Important for current setup:
- Because `INGESTION_AUTO_REFRESH` is set to `"false"`, run this workflow manually after deploy so the app has fresh ingested data.

## Step 8: Local Sanity Test (Optional but Recommended)

This confirms your code still works before/after cloud deployment.

1. In your local project, set env vars (PowerShell example):
   - `$env:DATABASE_URL="postgresql://..."`
   - `$env:OPENAI_API_KEY="sk-..."`
   - `$env:NYC_OPEN_DATA_APP_TOKEN="..."`
   - `$env:NYC_OPEN_DATA_DATASET_ID="abcd-1234"`
   - `$env:BASE_URL="http://localhost:8501"`
2. Run tests:
   - `python -m pytest tests -q`
3. Start app:
   - `streamlit run app.py`
4. Open app locally and verify it starts without validation errors.

## Step 9: First-Launch Verification Checklist (Cloud)

After deployment:
1. Open the app URL.
2. Confirm there is no startup validation error.
3. Confirm you can reach landing page and swipe flow.
4. Check for warnings:
   - if ingestion warning appears, inspect logs and workflow run output.
5. In app behavior, ensure events load and search works.

## Post-Deploy Verification & Rollback Checklist

Use this after each deploy or when troubleshooting.

**Verify (do in order):**
- [ ] App loads at production URL without startup errors.
- [ ] Manual Weekly Ingestion workflow run succeeds in GitHub Actions.
- [ ] Durability check: create session, add vote, restart app, confirm data persists.
- [ ] End-to-end: create session -> join -> vote -> availability -> results.

**If something breaks (rollback):**
1. In Streamlit Cloud: **Settings** -> **Redeploy** -> pick previous revision if available.
2. If data looks wrong: restore DB snapshot from your provider (Neon/Supabase/Render).
3. Re-run verification checklist before reopening.

## Step 10: Critical Durability Check (New and Important)

This confirms Postgres is actually storing persistent data.

1. In the app:
   - create a session
   - add at least one vote
   - add at least one availability slot
2. Restart app from Streamlit Cloud (or wait for app restart).
3. Re-open the same session link.
4. Confirm the session, votes, and availability are still present.

If data is missing after restart:
- likely `DATABASE_URL` is missing/incorrect in Streamlit secrets.
- re-check Step 5 and redeploy.

## Step 11: Ready For Manual Testing

You are ready for full manual testing when all are true:
- App starts without startup/readiness errors.
- Manual workflow run succeeds in GitHub Actions.
- Critical durability check passes.
- Swipe/search/recommendations are functional.

## Common Mistakes and Fixes

- Missing quotes in Streamlit Secrets TOML:
  - Keep strings quoted, e.g., `"value"`.
- Wrong GitHub settings page:
  - Use repository `Settings -> Secrets and variables -> Actions`.
- Dataset ID copied incorrectly:
  - Must be short ID like `abcd-1234`, not full URL.
- OpenAI key trimmed accidentally:
  - Paste full key exactly; no extra spaces/newlines.
- BASE_URL left as localhost:
  - Use your real deployed Streamlit URL.
- DATABASE_URL missing in Streamlit:
  - App may fall back to local SQLite and lose data on restart.
- Wrong database URL:
  - Must start with `postgresql://` or `postgres://`.
- Running Friday workflow but expecting Streamlit to share local files:
  - Local files are not shared across platforms. Durable SQL avoids this for core app data.

## Security Hygiene

- Never commit keys into `.py`, `.md`, `.yml`, or `.env.example`.
- Rotate keys if accidentally exposed.
- Prefer separate tokens/keys for dev vs production.

**CI secrets-scan:** Currently non-blocking (`continue-on-error: true`). Rationale: CI uses fake keys for tests; real keys live only in Streamlit/GitHub secrets. Scan may flag test fixtures—we keep it as a warning, not a gate.

## Quick Reference (Names Only)

- `OPENAI_API_KEY`
- `NYC_OPEN_DATA_APP_TOKEN`
- `NYC_OPEN_DATA_DATASET_ID`
- `BASE_URL`
- `DATABASE_URL`

## Quick "Am I Done?" Checklist

- [ ] Streamlit secrets saved (including `DATABASE_URL`, `BASE_URL`).
- [ ] GitHub Actions secrets saved (including `DATABASE_URL`, `BASE_URL` for weekly ingestion).
- [ ] App redeployed successfully.
- [ ] Manual Weekly Ingestion workflow run once.
- [ ] Durability check passed (data survives restart).
- [ ] Manual end-to-end app testing started.
