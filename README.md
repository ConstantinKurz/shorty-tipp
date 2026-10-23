# Django TipApp - World Cup 2026 Tipping Game

A Django-based web application for running a World Cup 2026 prediction/tipping game.

## Overview

This application allows participants to:
- Predict match results
- Use jokers to multiply points in rounds that allow them
- Pick a champion for a bonus
- Track scores and rankings
- Compete with friends in a private tipping competition

The tournament format (rounds, multipliers, joker limits, prediction limits) is configuration
in the database, not code — see [Tournament Configuration](#tournament-configuration).

Game rules are documented in [`docs/rules/wm2026-rules.md`](docs/rules/wm2026-rules.md).

System architecture, data model, HTMX patterns, and known issues are documented in
[`docs/project/architecture.md`](docs/project/architecture.md).

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
uv pip install -e ".[dev,pdf]"
```

The `pdf` extra installs `reportlab`, which is required for the leaderboard PDF export.

Or use the Makefile:
```bash
make install
```

### 5. Set Up Environment Variables

Copy the example environment file and adjust as needed:

```bash
cp .env.example .env
```

`.env` is loaded by `manage.py` only. A WSGI server started through `tipapp/wsgi.py` does not
read it — provide the variables through the process environment there.

Required environment variables:
- `SECRET_KEY`: Django secret key (use a secure random string in production)
- `DEBUG`: Set to `True` for development, `False` for production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DJANGO_SETTINGS_MODULE`: Set to `tipapp.settings.development` for local development
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: PostgreSQL connection details

Optional, feature-specific:
- `FOOTBALL_DATA_API_KEY`, `FOOTBALL_DATA_BASE_URL`: result import (see
  [Football-Data.org API Integration](#football-dataorg-api-integration))
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_HOST_USER`,
  `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `LEADERBOARD_ADMIN_EMAIL`: outgoing mail;
  `EMAIL_BACKEND` additionally switches the backend in development settings (see
  [Email Notifications](#email-notifications))

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

## Tournament Configuration

The tournament format is data, not code. A `Tournament` row holds the API competition code, the
API season and the prediction lock buffer; one `Round` row per round holds its label, order, score
multiplier, joker count, joker multiplier, joker pool, prediction limit, final flag and API stage.
Exactly one tournament is active at a time.

A fresh database is seeded with the 2026 World Cup ("WM 2026", slug `wm-2026`). Everything about
it is editable under **Matches → Tournaments** in the admin.

### Creating a tournament

```bash
python manage.py create_tournament \
  --preset em24 --name "EM 2028" --slug em-2028 --competition EC --activate
```

Available presets:

| Preset | Rounds |
|---|---|
| `wm48` | group, r32, r16, qf, sf, 3rd, final (the 2026 World Cup) |
| `wm32` | group, r16, qf, sf, 3rd, final |
| `em24` | group, r16, qf, sf, final (no round of 32, no third-place match) |

Omit `--preset` to create a tournament with no rounds and fill them in through the admin inline.
The admin add form offers the same presets through a dropdown.

> The `em24` preset's `api_stage` values are **unverified** against the live football-data.org
> `EC` competition. Confirm them before the first sync.

### Switching to another tournament

> **Warning:** switching destroys all predictions, points, rankings and champion picks of the
> previous tournament. This is intended — the application holds exactly one tournament at a time
> and keeps no history. Take a database dump first if you want to keep the old standings.

```bash
# 1. Drop and recreate the database
dropdb tipapp && createdb tipapp

# 2. Apply migrations (this seeds the 2026 World Cup)
python manage.py migrate

# 3. Recreate an administrator
python manage.py createsuperuser

# 4. Create and activate the new tournament
python manage.py create_tournament \
  --preset em24 --name "EM 2028" --slug em-2028 --competition EC --activate

# 5. Import teams and matches
python manage.py sync_teams
python manage.py update_matches --once
```

Finally, set each team's `champion_points` under **Matches → Teams**. Teams left at `0` award no
champion bonus; the tournament change form warns how many are still unset.

If round configuration changes after matches have been scored, run the **Recalculate scores**
action on the tournament in the admin (or `python manage.py recalculate_scores`).

## Football-Data.org API Integration

The application can automatically sync match results from the [football-data.org](https://www.football-data.org/) API, eliminating the need for manual match result entry.

### API Setup

1. **Get an API Key**

   Register for a free account at [football-data.org](https://www.football-data.org/) and obtain an API key from your dashboard.

2. **Configure Environment Variables**

   Add the following to your `.env` file:

   ```bash
   FOOTBALL_DATA_API_KEY=your-api-key-here
   FOOTBALL_DATA_BASE_URL=https://api.football-data.org/v4
   ```

   The `FOOTBALL_DATA_BASE_URL` is optional and defaults to `https://api.football-data.org/v4`.

3. **Sync Teams**

   Before the tournament starts, sync all participating teams:

   ```bash
   python manage.py sync_teams
   ```

   This creates Team records from the competition configured on the **active tournament**
   (`Tournament.api_competition_code`). To sync a different tournament, name it by slug:

   ```bash
   python manage.py sync_teams --tournament=em-2028
   ```

4. **Run the Match Updater**

   Start the continuous match updater process:

   ```bash
   python manage.py update_matches
   ```

   It also defaults to the active tournament and accepts `--tournament=<slug>`.

   A match whose API `stage` matches no `Round.api_stage` of the tournament aborts the sync with
   an error naming the stage. Fix the round configuration in the admin and run the command again.

   This command:
   - Runs in a persistent while-loop
   - Polls the API at adaptive intervals based on match schedule
   - Automatically detects goal changes and triggers scoring
   - Handles errors gracefully and continues running
   - Shuts down gracefully on SIGTERM/SIGINT

   **Adaptive Polling Intervals** (`_calculate_sleep_interval()`):
   - **A match has status `live`**: 10 seconds
   - **Match in the active window** (kickoff −3h to +30min, status scheduled or live): 30 seconds
   - **Next match starting < 30 minutes**: 1 minute
   - **Next match starting 30min - 2h**: 5 minutes
   - **Next match starting > 2 hours**: 10 minutes
   - **No upcoming matches**: 30 minutes

### API Rate Limits

The free tier allows **10 requests per minute**. The client implements:
- Exponential backoff on 5xx errors (max 3 retries)
- Retry-After header respect for 429 rate limit responses
- Adaptive polling to minimize API calls during idle periods

### Deployment Considerations

In production, run `update_matches` as a background service:

**Using systemd (Linux):**

```ini
[Unit]
Description=Django TipApp Match Updater
After=network.target

[Service]
Type=simple
User=tipapp
WorkingDirectory=/path/to/django-tipapp
Environment="DJANGO_SETTINGS_MODULE=tipapp.settings.production"
Environment="FOOTBALL_DATA_API_KEY=your-key"
ExecStart=/path/to/django-tipapp/.venv/bin/python manage.py update_matches
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Using Docker:**

Add a service to `docker-compose.yml`:

```yaml
services:
  updater:
    build: .
    command: python manage.py update_matches
    environment:
      - DJANGO_SETTINGS_MODULE=tipapp.settings.production
      - FOOTBALL_DATA_API_KEY=${FOOTBALL_DATA_API_KEY}
    depends_on:
      - db
    restart: unless-stopped
```

### Troubleshooting

**Problem:** `FootballDataAPIError: Request failed after 3 attempts`

**Possible causes:**
- Network connectivity issues
- API service outage
- Invalid API key

**Solution:**
- Check network connectivity
- Verify API key in `.env` file
- Check API status at [football-data.org](https://www.football-data.org/)
- Review logs for specific error messages

---

**Problem:** Rate limit errors (429)

**Solution:**
- The client automatically handles rate limits by respecting `Retry-After` headers
- If you're running multiple instances, ensure only one updater is active
- Consider upgrading to a paid plan for higher rate limits

---

**Problem:** Teams or matches not syncing

**Possible causes:**
- Teams must be synced before matches
- API may not have data for future tournaments yet
- Incorrect competition code

**Solution:**
- Run `sync_teams` first
- Verify the competition code on the active tournament (`WC` for the World Cup)
- Check API response in logs for data availability

---

**Problem:** Scoring not triggered after match updates

**Possible causes:**
- No change to a scoring-relevant field (`goals_home`, `goals_away`, `winner`, `status`)
- Match status not properly mapped
- Database constraint issues
- A scoring run failed and was rolled back

**Solution:**
- Check logs for "goals_changed" flag in sync results
- Verify match results in Django admin
- Run `python manage.py check` for configuration issues
- Run `python manage.py repair_scoring --check` to detect matches whose predictions were
  never scored, then `python manage.py repair_scoring` to score them (idempotent, exits
  non-zero when work remains or a repair failed)

## Email Notifications

The app sends mail through the standard Django email backend:

- **Password reset** — sent by the Django auth views.
- **Daily leaderboard report** — sent to `LEADERBOARD_ADMIN_EMAIL`, built from the **newest
  `LeaderboardSnapshot`** (not the live ranking) and enriched with each user's predictions.
- **Daily prediction reminder** — sent to every active, non-staff user who has no prediction
  for a `scheduled` match starting within the next 24 hours. Users without an email address
  are skipped.

Templates live in `notifications/templates/notifications/emails/` (HTML plus plain-text
variant for each mail), the logic in `notifications/services.py` (`EmailService`).

### Configuration

```bash
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-user
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=noreply@shortytipp.de
LEADERBOARD_ADMIN_EMAIL=admin@example.com
```

Backend per settings module:

| Settings module | Backend |
|---|---|
| `tipapp.settings.development` | Console by default; override with `EMAIL_BACKEND` (e.g. `django.core.mail.backends.smtp.EmailBackend`) to send real mail |
| `tipapp.settings.test` | `locmem` — never sends |
| `tipapp.settings.production` | Django's default SMTP backend, configured through the `EMAIL_*` variables above (`EMAIL_BACKEND` is not read here) |

Verify a real SMTP setup with:

```bash
python manage.py test_email --leaderboard
python manage.py test_email --reminder=<username>
```

### Running the Notification Daemon

```bash
python manage.py notification_daemon
```

Options:

| Option | Default | Description |
|---|---|---|
| `--interval` | 3600 | Seconds between checks |
| `--leaderboard-hour` | 20 | Hour (0-23) for the leaderboard report |
| `--reminder-hour` | 10 | Hour (0-23) for prediction reminders |
| `--once` | – | Run a single iteration and exit (for testing) |

The daemon sends each mail at most once per calendar day, triggers as soon as the configured
hour has passed, and shuts down gracefully on SIGTERM/SIGINT.

> The "already sent today" state is kept **in memory only**. A restart can re-send a mail that
> was already sent the same day, and a failed send is logged but never retried.

The leaderboard mail needs a snapshot. Create one before the configured hour, e.g. daily via
cron or the admin action:

```bash
python manage.py create_snapshot daily
```

In production, run the daemon as a service next to `update_matches`:

```yaml
services:
  notifier:
    build: .
    command: python manage.py notification_daemon
    environment:
      - DJANGO_SETTINGS_MODULE=tipapp.settings.production
      - EMAIL_HOST=${EMAIL_HOST}
      - EMAIL_PORT=${EMAIL_PORT}
      - EMAIL_USE_TLS=${EMAIL_USE_TLS}
      - EMAIL_HOST_USER=${EMAIL_HOST_USER}
      - EMAIL_HOST_PASSWORD=${EMAIL_HOST_PASSWORD}
      - DEFAULT_FROM_EMAIL=${DEFAULT_FROM_EMAIL}
      - LEADERBOARD_ADMIN_EMAIL=${LEADERBOARD_ADMIN_EMAIL}
    depends_on:
      - db
    restart: unless-stopped
```

### Email Troubleshooting

**Problem:** No mail arrives

**Solution:**
- Check `EMAIL_BACKEND` — development defaults to the console backend, tests to `locmem`
- Verify `EMAIL_HOST`/`EMAIL_PORT`/credentials with `python manage.py test_email --leaderboard`
- Leaderboard mail: is `LEADERBOARD_ADMIN_EMAIL` set and does a snapshot exist?
- Reminder mail: does the user have an email address, is the user active and non-staff, and is
  there an unpredicted `scheduled` match within 24 hours?
- Check the logs — send failures are logged and swallowed, never retried

## Project Structure

```
django-tipapp/
├── docs/                       # Documentation
│   ├── project/                # Architecture and decision records
│   └── rules/                  # Game rules
├── openspec/                   # OpenSpec changes and specs
├── tipapp/                     # Main Django project
│   ├── settings/               # Environment-specific settings
│   │   ├── base.py            # Shared settings
│   │   ├── development.py     # Development settings
│   │   └── production.py      # Production settings
│   ├── urls.py                # URL configuration
│   ├── views.py               # Home and ranking views
│   └── wsgi.py                # WSGI configuration
├── core/                       # Shared ranking algorithm
├── users/                      # User authentication and management
├── matches/                    # Tournament, round, team and match management
├── predictions/                # User predictions and jokers
├── scoring/                    # Scoring engine and leaderboard
├── notifications/              # Email service, notification daemon, mail templates
├── static/                     # Static files (CSS, JS, images)
├── templates/                  # HTML templates
├── scripts/                    # Helper scripts
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
  - Jokers distributed per rules (0 in group, 3 in R32, 3 in R16, 2 in QF, 2 in SF/3rd/Final)
- **~24 finished matches** with calculated scores

The command assumes the seeded `wm48` round configuration (round codes `group`, `r32`, `r16`,
`qf`, `sf`, `3rd`, `final`) on the active tournament.

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
- **Stage filter**: Filter by tournament round — the tabs come from the rounds configured on
  the active tournament, not from a hardcoded list
- **Auto-scroll**: Page automatically scrolls to the nearest upcoming match
- **Live updates**: HTMX polling every 15 seconds while a match is running, every 60 seconds
  otherwise; the interval is adjusted live via the `HX-Trigger` response header
- **Joker management**: Toggle jokers where the round allows it (within `Round.joker_count`,
  shared across rounds in the same joker pool)

## Admin Features

Staff users have access to the following admin features:

### Navigation
- **Admin Link**: Staff users see an "Admin" link in the main navbar for quick access to Django admin

### Leaderboard Exports

#### Via Django Admin Actions
Navigate to Admin → Scoring → Leaderboard Snapshots:
- **Create daily snapshot from current leaderboard**: Snapshot the current leaderboard (same as
  `python manage.py create_snapshot daily`)
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
