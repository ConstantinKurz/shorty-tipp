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

For development and testing, use the management command to create comprehensive Shortytipp test data:

```bash
python manage.py create_wm2026_testdata --clear
```

This creates:
- **48 real teams** from Shortytipp (12 groups × 4 teams, Groups A-L)
- **104 matches** (72 group stage + 32 knockout: 16 R32 + 8 R16 + 4 QF + 2 SF + 1 3rd + 1 Final)
- **8 test users** (`tipper1` through `tipper8`, password: `testpass123`)
- **~65 predictions per user** following all game rules:
  - 36 group stage predictions per user (randomly selected from 72)
  - Jokers distributed per rules (0 in group, 3 in R32, 3 in R16, 2 in QF, 2 in SF/Final)
- **~24 finished matches** with calculated scores

### Command Options

| Option | Description |
|--------|-------------|
| `--clear` | Delete all existing test data before creating new data |
| `--users N` | Number of test users to create (default: 8, max: 20) |

### Example Usage

```bash
# Create default test data (8 users)
python manage.py create_wm2026_testdata --clear

# Create test data with 5 users
python manage.py create_wm2026_testdata --clear --users 5
```

### Test User Credentials

All test users have the password `testpass123`:
- `tipper1` - Optimistic prediction pattern (high scores)
- `tipper2` - Pessimistic pattern (low scores)
- `tipper3` - Chaotic pattern (random)
- `tipper4` - Realistic pattern (balanced)
- `tipper5` - Home-team bias
- `tipper6-8` - Mixed patterns

**Note**: This command is for development/testing only. Do not run on production.

## Predictions Page Features

The predictions page (`/predictions/`) includes:

- **Single scrollable list**: All matches displayed chronologically
- **Stage filter**: Filter by tournament round (Group, R32, R16, QF, SF, Final)
- **Auto-scroll**: Page automatically scrolls to the nearest upcoming match
- **Live updates**: Match results update every 60 seconds via HTMX polling
- **Joker management**: Toggle jokers on knockout matches (within limits)

## Admin Features

Staff users have access to the following admin features:

### Navigation
- **Admin Link**: Staff users see an "Admin" link in the main navbar for quick access to Django admin

### Leaderboard Exports

#### Via Django Admin Actions
Navigate to Admin → Scoring → Leaderboard Snapshots:
- **Export selected snapshots to CSV**: Basic export of selected snapshots
- **Export detailed leaderboard with predictions to CSV**: Full export with per-match prediction details

#### Manual Download View (Staff Only)
Download current leaderboard without creating a snapshot:
- **Basic export**: `/scoring/admin/download-leaderboard/`
- **Detailed export**: `/scoring/admin/download-leaderboard/?detailed=true`

### Leaderboard Snapshots
Snapshot types available:
- **Daily**: Regular point-in-time snapshot
- **Final**: End-of-tournament snapshot

*Note: Weekly snapshots have been removed.*

### Champion Prediction Management
When staff change a user's predicted champion via the admin panel, rankings are automatically recalculated to reflect any champion bonus point changes.

## Contributing

This is a private tipping game application. See the game rules documentation in `docs/rules/wm2026-rules.md` for details on scoring, jokers, and ranking logic.

## License

Private project - not licensed for public use.
