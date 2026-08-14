# Design: Football-Data API Integration

## Overview

Implement automatic match data synchronization via football-data.org API. Two processes share the same database: the Updater writes match results and triggers scoring, the Django web server reads scores and rankings.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            UPDATER (Management Command)                     │
│                                                                             │
│  while True:                                                                │
│      1. API abrufen: GET /v4/competitions/WC/matches                       │
│      2. Für jedes Match mit Tor-Änderung:                                  │
│         - Match.goals_home/away updaten                                    │
│         - ScoringService.score_all_predictions_for_match() aufrufen        │
│         - → schreibt User.total_points in DB                               │
│      3. Adaptiv schlafen (siehe Polling-Intervalle)                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ writes
                                    ▼
                         ┌─────────────────────┐
                         │    PostgreSQL DB    │
                         │  Match.goals_*      │
                         │  User.total_points  │
                         └─────────────────────┘
                                    │
                                    │ reads
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DJANGO WEB SERVER                                │
│                                                                             │
│  HTMX-Poll GET /ranking-updates/:                                          │
│      → RankingService.get_current_leaderboard()                            │
│      → SELECT * FROM users ORDER BY total_points DESC                      │
│      → Return HTML                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Both processes use the same Django code and database. The Updater writes, the web server reads.

## Component Design

### 1. API Client (`matches/api_client.py`)

**Responsibilities:**
- HTTP client for football-data.org v4 API
- Authentication via `X-Auth-Token` header
- Rate limiting compliance (10 requests/minute on free tier)
- Retry with exponential backoff on 429/5xx errors

**Configuration:**
- `FOOTBALL_DATA_API_KEY`: Environment variable for API token
- Base URL: `https://api.football-data.org/v4`

**Key Methods:**
```python
class FootballDataClient:
    def __init__(self, api_key: str | None = None):
        """Initialize client with API key from env if not provided."""

    def get_teams(self, competition: str = "WC") -> list[dict]:
        """GET /competitions/{competition}/teams"""

    def get_matches(self, competition: str = "WC") -> list[dict]:
        """GET /competitions/{competition}/matches"""
```

**Error Handling:**
- 429 (Rate Limit): Retry after `Retry-After` header or 60s default
- 5xx (Server Error): Exponential backoff, max 3 retries
- Network errors: Log and raise for caller to handle

### 2. Match Sync Services (`matches/services.py`)

**`sync_teams_from_api()`**

Syncs teams from API to database:
1. Fetch teams via `FootballDataClient.get_teams()`
2. For each team: upsert by `fifa_code` (API `tla` field)
3. Update name if changed
4. Return count of created/updated teams

**`sync_matches_from_api()`**

Syncs matches from API to database:
1. Fetch matches via `FootballDataClient.get_matches()`
2. For each match:
   - Map API ID directly to Django Match.id
   - Upsert with kickoff, teams, round, status, goals
   - Detect if goals changed since last sync
3. Return list of matches with goal changes

**Status Mapping:**
| API Status | Django Status |
|------------|---------------|
| `SCHEDULED`, `TIMED` | `scheduled` |
| `IN_PLAY`, `PAUSED` | `live` |
| `FINISHED` | `finished` |

**Round Mapping:**
| API Stage | Django Round |
|-----------|--------------|
| `GROUP_STAGE` | `group` |
| `ROUND_OF_32` | `r32` |
| `ROUND_OF_16` | `r16` |
| `QUARTER_FINALS` | `qf` |
| `SEMI_FINALS` | `sf` |
| `THIRD_PLACE` | `3rd` |
| `FINAL` | `final` |

### 3. Updater Command (`matches/management/commands/update_matches.py`)

**Main Loop:**
```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        self.running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        while self.running:
            try:
                changed_matches = sync_matches_from_api()

                for match in changed_matches:
                    if match.goals_changed:
                        ScoringService.score_all_predictions_for_match(match)

                    if match.status == 'finished' and match.round == 'final':
                        ScoringService.score_champion_predictions()

                interval = self._calculate_sleep_interval()
                time.sleep(interval)

            except Exception as e:
                logger.error(f"Update failed: {e}")
                time.sleep(60)

    def _shutdown(self, signum, frame):
        self.running = False
```

**Adaptive Polling Intervals:**
| Situation | Interval |
|-----------|----------|
| No match today | 30 minutes |
| Next match > 2 hours | 10 minutes |
| Next match 30min – 2h | 5 minutes |
| Next match < 30min | 1 minute |
| Live match (`IN_PLAY`, `PAUSED`) | 30 seconds |

**Interval Calculation:**
```python
def _calculate_sleep_interval(self) -> int:
    now = timezone.now()

    # Check for live matches
    if Match.objects.filter(status='live').exists():
        return 30  # 30 seconds

    # Find next scheduled match
    next_match = Match.objects.filter(
        kickoff__gt=now,
        status='scheduled'
    ).order_by('kickoff').first()

    if not next_match:
        return 1800  # 30 minutes

    time_until = (next_match.kickoff - now).total_seconds()

    if time_until < 1800:  # < 30 min
        return 60  # 1 minute
    elif time_until < 7200:  # < 2 hours
        return 300  # 5 minutes
    else:
        return 600  # 10 minutes
```

### 4. Sync Teams Command (`matches/management/commands/sync_teams.py`)

One-shot command to sync teams before tournament:
```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        created, updated = sync_teams_from_api()
        self.stdout.write(f"Teams synced: {created} created, {updated} updated")
```

### 5. Model Changes

**Match Model:**

The existing Match model uses auto-generated integer IDs. We need to either:

**Option A (Recommended):** Add `external_id` field for API Match ID
```python
external_id: models.IntegerField = models.IntegerField(
    unique=True,
    null=True,
    blank=True,
    help_text="Match ID from football-data.org API"
)
```

**Option B:** Use API Match ID as primary key (requires data migration)

Recommendation: Option A is safer, preserves existing data, and allows gradual migration.

**Team Model:**

No changes required. `fifa_code` already exists and maps to API `tla` field.

## Scoring Flow

When the Updater detects a goal change:

1. `sync_matches_from_api()` returns list of matches with `goals_changed=True`
2. For each changed match, call `ScoringService.score_all_predictions_for_match(match)`
3. This calls `ScoringService.score_prediction()` for each user's prediction
4. `score_prediction()` atomically updates:
   - `MatchPrediction.points_earned`
   - `MatchPrediction.is_exact_match`
   - `User.total_points` (via F() expression)
   - `User.exact_match_count` (via F() expression)
   - `User.jokers_used` (via F() expression)

**Result:** Ranking is live-updated after every goal. No additional computation needed by web server.

## Error Handling

| Error | Handling |
|-------|----------|
| API rate limit (429) | Retry after `Retry-After` header value |
| API server error (5xx) | Exponential backoff, max 3 retries |
| Network timeout | Log error, continue loop, retry on next interval |
| Invalid API response | Log warning, skip affected match, continue |
| Database error | Log error, raise (let process manager restart) |
| Missing team reference | Log warning, skip match (team not in competition) |

## Configuration

**Environment Variables:**
| Variable | Required | Description |
|----------|----------|-------------|
| `FOOTBALL_DATA_API_KEY` | Yes | API token for football-data.org |

**Settings:**
```python
# settings/base.py
FOOTBALL_DATA_API_KEY = env("FOOTBALL_DATA_API_KEY", default="")
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"
```

## Testing Strategy

1. **Unit Tests:**
   - API client with mocked responses
   - Status and round mapping functions
   - Polling interval calculation
   - Goal change detection logic

2. **Integration Tests:**
   - Sync services with test database
   - Score calculation after sync
   - User.total_points update verification

3. **Manual Testing:**
   - Test with real API (development key)
   - Verify graceful shutdown
   - Test rate limit handling
