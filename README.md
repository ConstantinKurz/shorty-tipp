# Django TipApp - World Cup 2026 Tipping Game

A Django-based web application for running a World Cup 2026 prediction/tipping game.

## Overview

This application allows participants to:
- Predict match results
- Use jokers to double points
- Track scores and rankings
- Compete with friends in a private tipping competition

Game rules are documented in [`docs/rules/wm2026-rules.md`](docs/rules/wm2026-rules.md).

## Technology Stack

- **Language**: Python 3.12+
- **Web Framework**: Django 5.2 LTS
- **Database**: PostgreSQL 14+
- **Frontend**: Django Templates, HTMX, Tailwind CSS
- **Dependency Management**: uv
- **Code Quality**: ruff (linting/formatting), mypy (type checking)
- **Testing**: pytest, pytest-django

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management
- Docker and Docker Compose (for PostgreSQL)

## Local Development Setup

### 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv
```

### 2. Clone and Set Up the Project

```bash
git clone <repository-url>
cd django-tipapp
```

### 3. Create Virtual Environment

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 4. Install Dependencies

```bash
uv pip install "django>=5.2,<5.3" "psycopg2-binary>=2.9" pytest pytest-django pytest-cov ruff mypy django-stubs
```

Or use the Makefile (once project structure is complete):
```bash
make install
```

### 5. Set Up Environment Variables

Copy the example environment file and adjust as needed:

```bash
cp .env.example .env
```

Required environment variables:
- `SECRET_KEY`: Django secret key (use a secure random string in production)
- `DEBUG`: Set to `True` for development, `False` for production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DJANGO_SETTINGS_MODULE`: Set to `tipapp.settings.development` for local development
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: PostgreSQL connection details

### 6. Start PostgreSQL with Docker Compose

```bash
docker-compose up -d
```

This starts a PostgreSQL 16 container with:
- Database name: `tipapp`
- User: `tipapp`
- Password: `tipapp`
- Port: `5432`
- Persistent data volume

To stop the database:
```bash
docker-compose down
```

To remove the database and start fresh:
```bash
docker-compose down -v
```

### 7. Run Database Migrations

```bash
export DJANGO_SETTINGS_MODULE=tipapp.settings.development
python manage.py migrate
```

Or using the Makefile:
```bash
make migrate
```

### 8. Create a Superuser

For testing and development, create a superuser with these recommended credentials:

```bash
python manage.py createsuperuser
# Username: admin
# Email: admin@test.com
# Password: admin123
```

Or using the Makefile:
```bash
make createsuperuser
```

### 9. Run the Development Server

```bash
python manage.py runserver
```

Or using the Makefile:
```bash
make run
```

Access the application:
- Main site: http://localhost:8000/
- Admin interface: http://localhost:8000/admin/
- Login with the superuser credentials created above

## Project Structure

```
django-tipapp/
├── docs/                       # Documentation
│   └── rules/                  # Game rules
├── tipapp/                     # Main Django project
│   ├── settings/               # Environment-specific settings
│   │   ├── base.py            # Shared settings
│   │   ├── development.py     # Development settings
│   │   └── production.py      # Production settings
│   ├── urls.py                # URL configuration
│   ├── wsgi.py                # WSGI configuration
│   └── asgi.py                # ASGI configuration
├── users/                      # User authentication and management
├── matches/                    # Match and team management
├── predictions/                # User predictions and jokers
├── scoring/                    # Scoring engine and leaderboard
├── static/                     # Static files (CSS, JS, images)
├── templates/                  # HTML templates
├── .venv/                      # Virtual environment (not in git)
├── pyproject.toml             # Project metadata and dependencies
├── docker-compose.yml         # Docker Compose for PostgreSQL
├── Makefile                   # Development commands
├── .env.example               # Example environment variables
└── conftest.py                # Pytest fixtures
```

## Running Tests

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov
```

Or using the Makefile:
```bash
make test
```

## Code Quality

### Linting

Check code with ruff:
```bash
ruff check .
```

Or using the Makefile:
```bash
make lint
```

### Formatting

Format code with ruff:
```bash
ruff format .
```

Or using the Makefile:
```bash
make format
```

### Type Checking

Run mypy type checker:
```bash
mypy .
```

Or using the Makefile:
```bash
make typecheck
```

### Run All Checks

Run linting, formatting check, type checking, and tests:
```bash
make check
```

## Development Workflow

1. Create a new branch for your feature
2. Make your changes
3. Run `make check` to ensure code quality
4. Create migrations if models changed: `make makemigrations`
5. Run migrations: `make migrate`
6. Test your changes
7. Commit and push

## Test Data Seeding

**Note**: Comprehensive test data seeding (matches, predictions, ranking scenarios) will be implemented in a future change after the Match and Prediction models are created. For now, use the admin interface or Django shell to create test data manually.

The custom user model is ready for use:
- Superuser can be created with `make createsuperuser`
- pytest fixtures (`admin_user`, `regular_user`) are available for automated tests

## Contributing

This is a private tipping game application. See the game rules documentation in `docs/rules/wm2026-rules.md` for details on scoring, jokers, and ranking logic.

## License

Private project - not licensed for public use.
