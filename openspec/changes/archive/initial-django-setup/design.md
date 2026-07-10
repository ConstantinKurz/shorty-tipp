## Context

This is a greenfield Django project for a World Cup 2026 tipping game. The game rules are documented in `docs/rules/wm2026-rules.md`, but no implementation code exists yet. The project requires:
- Multi-user support with authentication
- Complex scoring logic with jokers and multipliers  
- Match and prediction management
- Leaderboard calculations

The technology stack is specified in `.github/copilot-instructions.md`: Python 3.12, Django 5.2 LTS, PostgreSQL, HTMX, Tailwind CSS, with uv for dependency management.

## Goals / Non-Goals

**Goals:**
- Establish a solid Django project foundation that supports incremental feature development
- Configure PostgreSQL with Docker for consistent local development
- Implement custom user model from the start (cannot be changed easily later)
- Set up modern Python tooling (uv, ruff, mypy) for code quality
- Create modular Django app structure that separates concerns
- Enable type-safe development with mypy and django-stubs

**Non-Goals:**
- Implementing game logic (scoring, jokers, predictions) - handled in subsequent changes
- Building frontend UI beyond basic templates
- Setting up production deployment infrastructure
- Creating CI/CD pipelines (structure only)

## Decisions

### 1. Custom User Model from Start

**Decision:** Implement a custom user model (`users.User`) extending `AbstractUser` in the initial setup.

**Rationale:** Django strongly recommends this even if not immediately customizing fields. Changing user models after migrations is extremely difficult. We anticipate needing additional user fields (e.g., display name, payment status) for the tipping game.

**Alternatives considered:**
- Use Django's default User model: Rejected because future changes would require complex migrations and data migration
- Use `AbstractBaseUser`: Rejected as overkill - we want Django's built-in user functionality

### 2. Modular Django App Structure

**Decision:** Create separate apps for distinct domains:
- `users`: Authentication, user management
- `matches`: Match data, teams, tournament structure
- `predictions`: User predictions, joker management
- `scoring`: Scoring engine, leaderboard calculations

**Rationale:** Separates concerns and allows parallel development. Each app has clear boundaries matching the game rules domains.

**Alternatives considered:**
- Single monolithic app: Rejected - would become unmaintainable as features grow
- More granular apps (e.g., separate jokers app): Rejected - premature at this stage

### 3. Dependency Management with uv

**Decision:** Use `uv` instead of pip, poetry, or pipenv.

**Rationale:** 
- Specified in copilot-instructions.md as project requirement
- Significantly faster than pip/poetry
- Compatible with requirements.txt and pyproject.toml standards
- Provides virtual environment management

**Alternatives considered:**
- poetry: More mature but slower, requires poetry.lock
- pip + venv: Too manual for modern projects

### 4. PostgreSQL via Docker Compose

**Decision:** Require Docker Compose for local PostgreSQL database.

**Rationale:**
- Ensures consistent database version across all developers
- Isolates database from system installations
- Matches production deployment approach
- Specified in project requirements

**Alternatives considered:**
- SQLite for development: Rejected - PostgreSQL-specific features may be needed, migrations should match production
- Local PostgreSQL install: Rejected - version inconsistencies across developers

### 5. Settings Configuration

**Decision:** Split settings into `settings/base.py`, `settings/development.py`, `settings/production.py` with environment variable configuration.

**Rationale:**
- Separates environment-specific configuration
- Prevents accidental production setting leaks
- Follows Django best practices
- Supports future deployment to Azure

**Alternatives considered:**
- Single settings.py with if/else: Rejected - harder to maintain and test
- django-environ library: Rejected - adds unnecessary dependency, stdlib is sufficient

### 6. Type Checking with mypy

**Decision:** Configure mypy with django-stubs from the start, enforcing type hints on all new code.

**Rationale:**
- Catches errors before runtime, especially in complex scoring logic
- Improves code documentation and IDE support
- Specified in project requirements

**Trade-off:** Initial development slower due to type annotations, but reduces bugs long-term.

### 7. Testing with pytest

**Decision:** Use pytest + pytest-django instead of Django's default unittest.

**Rationale:**
- More Pythonic syntax (plain assert vs self.assertEqual)
- Better fixtures and parametrization
- Specified in project requirements
- Better integration with modern testing tools

**Alternatives considered:**
- Django's unittest: Rejected - less ergonomic than pytest

## Risks / Trade-offs

**Risk:** Developers unfamiliar with uv may face onboarding friction  
**Mitigation:** Include clear setup instructions in README with common commands

**Risk:** Docker requirement increases local setup complexity  
**Mitigation:** Provide docker-compose.yml with single-command startup, document prerequisites

**Risk:** Over-engineering with empty Django apps before features exist  
**Mitigation:** Apps contain minimal structure (models.py, views.py) but no complex logic yet. They provide namespaces for future development.

**Risk:** Type checking may slow initial development  
**Mitigation:** Start with strict mypy config but allow gradual adoption. Focus on typing business logic (scoring) more strictly than boilerplate.

**Trade-off:** PostgreSQL requirement prevents casual contributors without Docker from running the project  
**Acceptance:** This is acceptable for a private tipping game, not an open-source project expecting many contributors

## Migration Plan

N/A - This is initial setup with no existing system to migrate from.

## Test Data Strategy

**For Initial Setup:**
- Manual superuser creation via `python manage.py createsuperuser`
- Recommended credentials for development: admin / admin@test.com / admin123
- pytest fixtures for automated testing (admin_user, regular_user)

**Future Test Data Seeding:**
Test data seeding for matches, predictions, and rankings will be implemented in a separate change after core models exist. This approach:
- Avoids building seeding infrastructure before having models to seed
- Allows seeding logic to evolve with feature development
- Keeps initial setup focused and minimal

The seeding command (planned for later) will create:
- Admin user (if not exists)
- Sample tournament teams
- Mix of completed and upcoming matches
- Sample predictions from multiple users
- Test data representing various scoring scenarios

## Open Questions

None - all technical decisions finalized for initial setup scope.
