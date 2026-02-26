# YesCount -- Local CI PRD

> Sub-PRD of [PRD_MASTER.md](PRD_MASTER.md)

---

## 1. Overview

This document defines the local development workflow, CI tooling, and deployment pipeline for YesCount. The goal is fast feedback loops during development (lint, format, typecheck, test in under 60 seconds) and a reliable GitHub Actions workflow for automated checks on every push and pull request.

---

## 2. Dependency Management

### 2.1 `requirements.txt` (runtime)

Pinned versions for reproducibility:

```
streamlit>=1.45.0
openai>=1.70.0
chromadb>=0.6.0
requests>=2.32.0
beautifulsoup4>=4.12.0
python-dateutil>=2.9.0
pyyaml>=6.0.0
```

### 2.2 `requirements-dev.txt` (development + testing)

```
-r requirements.txt
pytest>=8.3.0
pytest-cov>=6.0.0
pytest-mock>=3.14.0
responses>=0.25.0
freezegun>=1.4.0
ruff>=0.9.0
mypy>=1.14.0
pre-commit>=4.0.0
detect-secrets>=1.5.0
```

### 2.3 Python Version

Minimum: **Python 3.11**. Tested on 3.11 and 3.12.

---

## 3. Makefile

All common tasks are accessible via `make` targets. The `Makefile` lives in the project root.

```makefile
.PHONY: install install-dev lint format typecheck test test-fast ci ingest run clean

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check --fix .

typecheck:
	mypy src/ --ignore-missing-imports

test:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=60

test-fast:
	pytest tests/ -x -q

ci: lint typecheck test

ingest:
	python -m src.ingestion.nyc_open_data
	python -m src.ingestion.web_scraper

run:
	streamlit run app.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	rm -rf .coverage htmlcov/
```

### Target Descriptions

| Target | Time | Description |
|--------|------|-------------|
| `make install` | ~15s | Install runtime dependencies |
| `make install-dev` | ~30s | Install all dependencies + set up pre-commit hooks |
| `make lint` | ~5s | Check code style and formatting without modifying files |
| `make format` | ~5s | Auto-format and auto-fix lint issues |
| `make typecheck` | ~10s | Run mypy static type analysis on `src/` |
| `make test` | ~30s | Full test suite with coverage report |
| `make test-fast` | ~10s | Fail-fast test run (stops on first failure) |
| `make ci` | ~45s | Lint + typecheck + test (same as GitHub Actions) |
| `make ingest` | ~60s | Run the event ingestion pipeline (NYC Open Data + scrapers) |
| `make run` | -- | Start the Streamlit dev server |
| `make clean` | ~2s | Remove cache directories and coverage artifacts |

---

## 4. Ruff Configuration

`ruff.toml` in the project root:

```toml
target-version = "py311"
line-length = 100

[lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "RUF",  # ruff-specific rules
]
ignore = [
    "E501",  # line too long (handled by formatter)
]

[lint.isort]
known-first-party = ["src"]

[format]
quote-style = "double"
indent-style = "space"
```

---

## 5. Mypy Configuration

`mypy.ini` in the project root:

```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
ignore_missing_imports = True

[mypy-tests.*]
disallow_untyped_defs = False
```

**Note:** `disallow_untyped_defs` is initially `False` to avoid blocking development. It will be tightened to `True` for `src/engine/` and `src/rag/` once the codebase stabilizes.

---

## 6. Pre-Commit Hooks

`.pre-commit-config.yaml` in the project root:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.0
    hooks:
      - id: mypy
        additional_dependencies: []
        args: [--ignore-missing-imports]
        pass_filenames: false
        entry: mypy src/

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: [--baseline, .secrets.baseline]

  - repo: local
    hooks:
      - id: pytest-fast
        name: pytest (fast)
        entry: pytest tests/ -x -q --no-header
        language: system
        pass_filenames: false
        always_run: true
```

### Hook Execution Order

1. **ruff (lint + fix)** -- auto-fixes trivial issues (import order, unused imports).
2. **ruff-format** -- ensures consistent formatting.
3. **mypy** -- catches type errors before commit.
4. **detect-secrets** -- prevents committing API keys or tokens.
5. **pytest (fast)** -- runs the test suite in fail-fast mode to catch regressions.

### First-Time Setup

```bash
make install-dev   # installs pre-commit and hooks
detect-secrets scan > .secrets.baseline   # initialize baseline
```

---

## 7. GitHub Actions Workflow

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  ci:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements-dev.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Lint
        run: make lint

      - name: Type check
        run: make typecheck

      - name: Test
        run: make test
        env:
          OPENAI_API_KEY: "sk-test-fake-key-for-ci" # pragma: allowlist secret
          NYC_OPEN_DATA_APP_TOKEN: "fake-token-for-ci"
```

### Workflow Details

| Aspect | Detail |
|--------|--------|
| Triggers | Push to `main`, PR targeting `main` |
| Matrix | Python 3.11 and 3.12 on `ubuntu-latest` |
| Caching | pip cache keyed on `requirements-dev.txt` hash |
| Env vars | Fake API keys so tests that mock external calls don't error on missing env vars |
| Steps | Install -> Lint -> Typecheck -> Test (sequential; fail-fast) |
| Runtime | ~2 minutes total |

### Required CI Gates for Merge

The following checks are required (blocking) before merge to `main`:

1. `make lint`
2. `make typecheck`
3. `make test` (includes `--cov-fail-under=60`)
4. Integration tests (`pytest tests/integration/ -v`)
5. Smoke tests (`pytest -m smoke -v`)
6. No secret leaks from `detect-secrets`
- `detect-secrets` may run as pre-commit and/or dedicated CI step, but release must enforce it.

If any required gate fails, the PR is not mergeable.

---

## 8. Project File Layout (Complete)

```
yescount/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .pre-commit-config.yaml
├── .secrets.baseline
├── .env.example
├── .gitignore
├── Makefile
├── ruff.toml
├── mypy.ini
├── requirements.txt
├── requirements-dev.txt
├── app.py                      # Streamlit entry point
├── config/
│   ├── scraper_sites.yaml      # Web scraper site configs
│   └── vibe_tags.yaml          # Curated vibe tag vocabulary
├── data/                       # gitignored; created at runtime
│   ├── yescount.db
│   └── chroma/
├── docs/
│   ├── PRD_MASTER.md
│   ├── PRD_DATA_MODEL.md
│   ├── PRD_BACKEND.md
│   ├── PRD_FRONTEND.md
│   ├── PRD_UNIT_TESTS.md
│   └── PRD_LOCAL_CI.md
├── migrations/
│   ├── 001_create_events.py
│   ├── 002_create_sessions.py
│   ├── 003_create_participants.py
│   ├── 004_create_votes.py
│   └── 005_create_availability_slots.py
├── src/
│   ├── __init__.py
│   ├── ingestion/
│   ├── db/
│   ├── rag/
│   ├── engine/
│   ├── sessions/
│   └── utils/
└── tests/
    ├── conftest.py
    ├── ingestion/
    ├── db/
    ├── rag/
    ├── engine/
    ├── sessions/
    └── utils/
```

### `.gitignore` Additions

```
data/
*.db
.env
__pycache__/
.pytest_cache/
.mypy_cache/
.coverage
htmlcov/
.secrets.baseline
```

---

## 9. `.env.example`

```
OPENAI_API_KEY=sk-your-key-here
NYC_OPEN_DATA_APP_TOKEN=your-socrata-token-here
SQLITE_DB_PATH=data/yescount.db
CHROMA_PERSIST_DIR=data/chroma/
SESSION_EXPIRY_DAYS=7
LOG_LEVEL=INFO
BASE_URL=http://localhost:8501
```

---

## 10. Deployment (Streamlit Community Cloud)

### 10.1 Prerequisites

- GitHub repository is public (or connected to Streamlit Cloud).
- `requirements.txt` is at the project root.
- `app.py` is at the project root.

### 10.2 Streamlit Cloud Configuration

In the Streamlit Cloud dashboard:
- **Repository**: `github.com/<user>/yescount`
- **Branch**: `main`
- **Main file path**: `app.py`
- **Python version**: 3.11

### 10.3 Secrets Management

Streamlit Cloud secrets are set via the dashboard UI (Settings > Secrets) in TOML format:

```toml
OPENAI_API_KEY = "sk-..." # pragma: allowlist secret
NYC_OPEN_DATA_APP_TOKEN = "..."
```

Accessed in code via `st.secrets["OPENAI_API_KEY"]` with a fallback to `os.getenv()` for local development:

```python
api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
```

### 10.4 Data Persistence

SQLite and ChromaDB data live on ephemeral disk on Streamlit Cloud. Data is lost on app restarts. Options for persistence:
- **Acceptable for MVP**: Re-run ingestion on app startup (adds ~30s cold start).
- **Required before production**: Migrate to durable storage (hosted SQL + durable vector store, or equivalent).

### 10.5 Startup Validation and Health Checks

The app must perform startup validation and expose health signals:

- Validate required secrets/env vars at startup (`OPENAI_API_KEY`, `NYC_OPEN_DATA_APP_TOKEN`, `BASE_URL`).
- Validate DB/vector store initialization before serving user traffic.
- Expose health check routes/handlers for:
  - **Liveness:** process is running.
  - **Readiness:** app can read/write required dependencies.

Deploy is considered failed if readiness does not pass after rollout.

### 10.6 Deployment Rollback Procedure

If post-deploy checks fail:

1. Roll back to the previous known-good app revision.
2. If schema/data changes were included, apply migration rollback (`down`) or restore from latest pre-deploy backup.
3. Re-run smoke checks (create session -> join -> vote -> availability -> recommendations).
4. Keep release closed until all checks are green.

### 10.7 Release Checklist

Before production deploy approval:

1. CI gates (lint/typecheck/unit/integration/smoke/coverage) are green.
2. Startup validation and readiness checks pass in target environment.
3. Migration rollback path and backup restore path are confirmed.
4. Security and performance checks have no release-blocking failures.
