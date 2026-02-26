.PHONY: install install-dev lint format typecheck test test-fast integration smoke security-check ci run ingest clean

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

integration:
	pytest tests/integration/ -v

smoke:
	pytest -m smoke -v

security-check:
	detect-secrets-hook --baseline .secrets.baseline $$(git ls-files)

ci: lint typecheck test integration smoke security-check

run:
	streamlit run app.py

ingest:
	python -m src.ingestion.run_ingestion --force

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', '.mypy_cache', 'htmlcov')]"
