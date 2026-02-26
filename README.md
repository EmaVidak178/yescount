# YesCount

YesCount is a Streamlit app for planning group outings with event discovery, swipe voting, availability matching, and recommendation ranking.

## Local setup

1. Create a virtual environment and activate it.
2. Install dependencies:
   - `pip install -r requirements-dev.txt`
3. Copy `.env.example` to `.env` and set required values:
   - `OPENAI_API_KEY`
   - `NYC_OPEN_DATA_APP_TOKEN`
   - `NYC_OPEN_DATA_DATASET_ID`
   - `BASE_URL`
   - Optional for durable SQL now: `DATABASE_URL` (PostgreSQL)

## Run locally

- `make run`

## Quality gates

- `make lint`
- `make typecheck`
- `make test`
- `make integration`
- `make smoke`
- `make security-check`
- `make ci` (runs all of the above)

## Deploy

### Streamlit Cloud (MVP)

1. Push repository to GitHub.
2. Connect the repo in Streamlit Community Cloud.
3. Set app secrets in Streamlit:
   - `OPENAI_API_KEY`
   - `NYC_OPEN_DATA_APP_TOKEN`
   - `NYC_OPEN_DATA_DATASET_ID`
   - Optional but recommended now: `DATABASE_URL` (PostgreSQL)
4. Set `BASE_URL` to the deployed app URL.
5. Validate the critical journey after deploy.

### Production reliability

See `docs/DEPLOYMENT_PRODUCTION.md` for durable storage migration, rollback, and staged rollout requirements.
For beginner-friendly secret setup instructions, see `docs/BEGINNER_SECRETS_SETUP.md`.
