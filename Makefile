.PHONY: install dev test lint format

install:
	pip install -e ".[dev]"

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format .

run-ui:
	streamlit run streamlit_app.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache
