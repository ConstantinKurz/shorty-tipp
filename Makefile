.PHONY: help install test lint format typecheck check clean run migrate makemigrations shell createsuperuser

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make test          - Run tests with pytest"
	@echo "  make lint          - Run ruff linting"
	@echo "  make format        - Format code with ruff"
	@echo "  make typecheck     - Run mypy type checking"
	@echo "  make check         - Run all checks (lint, format-check, typecheck, test)"
	@echo "  make clean         - Remove Python cache files"
	@echo "  make run           - Run development server"
	@echo "  make migrate       - Run database migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make shell         - Open Django shell"
	@echo "  make createsuperuser - Create a superuser"

install:
	uv pip install -e ".[dev,pdf]"

test:
	DJANGO_SETTINGS_MODULE=tipapp.settings.test python -m pytest -v

lint:
	ruff check .

format:
	ruff format .

format-check:
	ruff format --check .

typecheck:
	mypy .

check: lint format-check typecheck test
	@echo "All checks passed!"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

run:
	python manage.py runserver

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

shell:
	python manage.py shell

createsuperuser:
	python manage.py createsuperuser
