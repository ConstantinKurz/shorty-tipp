# Proposal: Football-Data API Integration

## Summary

Build an API integration service that fetches match and team data from football-data.org, stores it in the database, and automatically calculates points when scores change. The service runs as a Django management command in a persistent while-loop.

## Problem

Currently, match results must be entered manually by admins. This creates delays in score updates and requires constant admin attention during live matches. Users cannot see real-time score changes or updated points during matches.

**Current workflow:**
1. Admin watches match
2. Admin manually enters goals in Django admin
3. ScoringService triggers on Match.save()
4. Users see updated scores on next page load

**Pain points:**
- Manual data entry is error-prone and time-consuming
- Delays between actual goals and system updates
- Admin must be available during all matches
- No automated live updates during matches

## Solution

Implement automatic match data synchronization via football-data.org API:

1. **API Client** (`matches/api_client.py`): HTTP client for football-data.org v4 API with rate limiting and error handling.

2. **Sync Services** (`matches/services.py`): Functions to sync teams and matches from API to database with upsert logic.

3. **Updater Command** (`matches/management/commands/update_matches.py`): Persistent while-loop that polls API, detects score changes, and triggers scoring.

**Key design decisions:**
- No Celery, Redis, or task queues - simple while-loop in management command
- No cronjobs - single long-running process
- Adaptive polling intervals (30s during live matches, 30min when idle)
- Graceful shutdown on SIGTERM/SIGINT
- Match ID maps directly to API Match ID (no external_id field)

## Non-Goals

- Docker/container deployment configuration
- WebSocket push notifications
- Historical data backfill
- Real-time push updates (polling is sufficient)
- Admin UI for API configuration

## Success Criteria

1. `python manage.py sync_teams` loads all WC teams into database
2. `python manage.py update_matches` runs persistently in while-loop
3. Polling interval adapts automatically based on match schedule
4. Points recalculate on every goal, not just at match end
5. `User.total_points` updates directly in database
6. Web server reads from database only, computes nothing
7. API errors are logged, loop continues
8. Process shuts down gracefully on SIGTERM
