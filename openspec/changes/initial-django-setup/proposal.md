## Why

This repository contains game rules and documentation for a World Cup 2026 tipping game, but no implementation exists yet. We need to establish the foundational Django project structure and development environment to enable incremental feature development. Starting with a solid technical foundation allows us to build match prediction, scoring, and ranking features systematically in subsequent changes.

## What Changes

- Initialize Django 5.2 LTS project with custom user model
- Set up PostgreSQL database configuration
- Create modular Django app structure (users, matches, predictions, scoring)
- Configure development environment with uv dependency management
- Implement Docker containerization for PostgreSQL and Django
- Set up testing infrastructure with pytest and pytest-django
- Configure code quality tools (ruff, mypy with django-stubs)
- Create basic project documentation and README
- Establish CI-ready project structure for future deployment

## Capabilities

### New Capabilities
- `project-structure`: Django project initialization, settings configuration, modular app organization, and base directory structure
- `database-configuration`: PostgreSQL setup, database connection configuration, and Docker Compose for local development
- `user-authentication`: Custom user model implementation following Django best practices, with basic authentication views
- `development-environment`: Dependency management with uv, development/production settings separation, environment variable configuration
- `testing-infrastructure`: pytest setup with pytest-django, test configuration, basic test utilities and fixtures
- `code-quality`: ruff for linting and formatting, mypy with django-stubs for type checking, pre-commit hooks configuration

### Modified Capabilities
<!-- No existing capabilities to modify -->

## Impact

- Creates complete project structure from scratch
- Establishes Python 3.12, Django 5.2, and PostgreSQL as the technology stack
- Defines Django apps: `users`, `matches`, `predictions`, `scoring` (empty initially)
- Introduces uv for dependency management instead of pip/poetry
- Requires Docker for local PostgreSQL development
- Sets coding standards and type-checking requirements for all future development
- No breaking changes (greenfield project)
