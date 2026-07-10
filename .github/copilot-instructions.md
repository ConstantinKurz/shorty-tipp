# GitHub Copilot Instructions

This repository contains a Django-based football prediction app for the 2026 World Cup tipping game.

The project follows a lightweight spec-driven development workflow using OpenSpec.

Copilot must not implement features directly from vague chat prompts. Always use the repository documentation, OpenSpec files and documented game rules as the source of truth.

---

## Core Technologies

- **Language**: Python 3.12
- **Web Framework**: Django 5.2 LTS
- **Database**: PostgreSQL
- **Frontend**: Django Templates, HTMX, Tailwind CSS
- **Forms**: Django Forms
- **Authentication**: Django authentication system with a custom user model from the start
- **Dependency Management**: `uv`
- **Linting and Formatting**: `ruff`
- **Typing**: `mypy`, `django-stubs`
- **Testing**: `pytest`, `pytest-django`
- **Configuration**: environment variables, no hardcoded secrets
- **Deployment Target**: Docker, optionally Azure DevOps Pipelines
- **Spec Workflow**: OpenSpec

Do not introduce additional frameworks, frontend SPAs, REST APIs, Celery, Redis, GraphQL or external services unless explicitly required by an OpenSpec change.

---

## Source of Truth

Before proposing, planning, implementing or reviewing changes, use these files as project context:

- `openspec/specs/`
- `openspec/changes/`
- `docs/rules/wm2026-rules.md`
- `docs/project/decisions.md`
- `README.md`

The original PDF is the authoritative source for the game rules.

`docs/rules/wm2026-rules.md` is the working Markdown version of those rules and must be used for implementation and tests.

If the Markdown rules are missing, incomplete or unclear, stop and ask for clarification before implementing game logic.

Do not silently reinterpret game rules.

---

## Required Workflow

Always work in venv create one if not present.

Always follow this order:

1. Read the relevant OpenSpec change.
2. Read `proposal.md`, `design.md`, `tasks.md` and affected specs.
3. Read `docs/rules/wm2026-rules.md` if the task touches game behavior.
4. Identify the active task.
5. If the task is unclear, stop and ask for clarification.
6. Implement only the selected task.
7. Add or update tests.
8. Update documentation if behavior changed.
9. Summarize changed files, tests and open follow-ups.

Do not implement multiple tasks at once unless explicitly instructed.

Do not change unrelated files.

---

## Product Boundaries

Build a web-based World Cup prediction game where participants can:

- log in
- manage their profile
- enter and edit predictions
- set allowed jokers
- view matches
- view scores and rankings
- view what oother users have tipped
- allow admins to manage matches, results and users
- built at the a small forum where tippers can communicate

Keep the product simple and server-rendered.

Prefer Django templates with small HTMX enhancements over a complex frontend architecture.

Do not build a public betting, payment or gambling platform.

Do not add real-money workflows.

---

## Django Architecture

Use a modular Django app structure.

Keep business logic out of templates and views.

Put scoring and ranking logic into dedicated services.

Views should orchestrate requests, forms and templates. They should not contain complex domain logic.

Models should define data structure and simple invariants, not large workflows.

---

## Database Rules

Use PostgreSQL as the primary database.

Use Django migrations for all schema changes.

Prefer explicit database constraints where useful.

All date and time fields must be timezone-aware.

Do not store calculated leaderboard snapshots unless there is a documented performance reason.

Do not add raw SQL unless necessary and documented in `docs/project/decisions.md`.

---

## Code Style and Quality

Follow existing naming conventions and project structure.

Use type hints for all function signatures.

Write Google-style docstrings for public classes, public functions and non-trivial domain services.

Use clear, maintainable code.

Use `ruff` for formatting and linting.

Use `mypy` with `django-stubs` for type checking.

Do not introduce new dependencies without documenting the reason in `docs/project/decisions.md`.

Always prefer existing functions, components and services from the workspace before creating new ones.

---

## Testing Rules

Use `pytest` and `pytest-django`.

Add tests for every new business rule.

Business-critical logic must be tested at service level.

Permission-sensitive behavior must be tested with view or integration tests.

Tests should be deterministic and must not depend on the current real-world date or time.

When implementing game logic, derive test cases from `docs/rules/wm2026-rules.md`.

---

## Security Rules

Do not expose secrets.

Do not hardcode credentials.

Use environment variables for configuration.

Validate all user input through Django forms or model validation.

Users may only create, update or delete their own predictions.

Admin-only operations must require staff permissions.

Do not rely on frontend checks for authorization or lock-time behavior.

Avoid logging personal data or sensitive values.

---

## UI Guidelines

Prefer simple Django templates.

Use HTMX only for small progressive enhancements.

Use Tailwind CSS for styling.

Keep templates readable.

Avoid complex logic in templates.

The UI should prioritize clarity over visual complexity.

---

## OpenSpec Rules

For every new feature or behavior change, create or update an OpenSpec change before implementing code.

A change should contain:

- `proposal.md`
- `design.md`
- `tasks.md`
- affected specs

Tasks must be small and independently reviewable.

Each task must include:

- goal
- scope
- out of scope
- acceptance criteria
- required tests

If requirements change, update OpenSpec first, then code.

When a change is fully implemented and reviewed, archive it using the OpenSpec workflow.

---

## Review Rules

When reviewing code, check:

- Are all acceptance criteria fulfilled?
- Are relevant tests present?
- Does game behavior match `docs/rules/wm2026-rules.md`?
- Are permission checks enforced server-side?
- Are database constraints appropriate?
- Are migrations correct?
- Were unrelated files changed?
- Does the implementation follow the documented architecture?
- Does documentation need to be updated?

Return review results as:

- Passed criteria
- Failed criteria
- Risks
- Required follow-up tasks
- Suggested next task

Do not modify code during review unless explicitly asked.