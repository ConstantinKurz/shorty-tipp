# Tasks: Football-Data API Integration

## Task 1: Create API Client

### Goal
Create an HTTP client for the football-data.org v4 API with authentication, rate limiting compliance, and retry logic.

### Scope
- Create new file `matches/api_client.py`
- Implement `FootballDataClient` class
- Add `get_teams(competition: str)` method for `/competitions/{code}/teams`
- Add `get_matches(competition: str)` method for `/competitions/{code}/matches`
- Read API key from `FOOTBALL_DATA_API_KEY` environment variable
- Add `X-Auth-Token` header to all requests
- Implement retry with exponential backoff for 429/5xx errors
- Respect `Retry-After` header on rate limit responses
- Add type hints and docstrings
- Add settings for `FOOTBALL_DATA_API_KEY` and `FOOTBALL_DATA_BASE_URL` in `settings/base.py`

### Out of Scope
- Sync services (Task 2)
- Management commands (Tasks 3-4)
- Model changes (Task 5)
- Caching of API responses

### Acceptance Criteria
- File `matches/api_client.py` exists
- `FootballDataClient` class is importable
- `get_teams()` returns list of team dicts from API
- `get_matches()` returns list of match dicts from API
- API key is read from environment variable
- Requests include `X-Auth-Token` header
- 429 responses trigger retry after `Retry-After` seconds
- 5xx responses trigger exponential backoff (max 3 retries)
- All methods have type hints and docstrings
- Code passes mypy and ruff

### Required Tests
- Unit test: `test_api_client_sends_auth_header()` - Mock requests, verify header
- Unit test: `test_api_client_retries_on_429()` - Mock 429, verify retry
- Unit test: `test_api_client_retries_on_500()` - Mock 500, verify backoff
- Unit test: `test_api_client_respects_retry_after_header()` - Verify timing
- Unit test: `test_api_client_raises_after_max_retries()` - Verify exception after 3 retries

---

## Task 2: Add External ID Field to Match Model

### Goal
Add an `external_id` field to the Match model to store the API match ID without changing the existing primary key structure.

### Scope
- Add `external_id = models.IntegerField(unique=True, null=True, blank=True)` to Match model
- Add help text explaining it stores the football-data.org API match ID
- Create migration
- Add index for efficient lookups by external_id

### Out of Scope
- Changing the primary key
- Data migration for existing matches
- API client or sync services

### Acceptance Criteria
- Match model has `external_id` field
- Field is unique but nullable
- Field has appropriate help text
- Migration file created
- Migration applies cleanly to test database
- Code passes mypy and ruff

### Required Tests
- Model test: `test_match_external_id_field_exists()` - Verify field definition
- Model test: `test_match_external_id_unique_constraint()` - Verify uniqueness enforcement
- Model test: `test_match_external_id_nullable()` - Verify null is allowed

---

## Task 3: Create Sync Services

### Goal
Create service functions to sync teams and matches from the football-data.org API to the database.

### Scope
- Add sync functions to `matches/services.py` (create file if needed)
- Implement `sync_teams_from_api()`:
  - Fetch teams via `FootballDataClient.get_teams()`
  - Upsert by `fifa_code` (API `tla` field)
  - Return tuple of (created_count, updated_count)
- Implement `sync_matches_from_api()`:
  - Fetch matches via `FootballDataClient.get_matches()`
  - Upsert by `external_id` (API match id)
  - Map API status to Django status (SCHEDULED/TIMED→scheduled, IN_PLAY/PAUSED→live, FINISHED→finished)
  - Map API stage to Django round (GROUP_STAGE→group, etc.)
  - Track goal changes for each match
  - Return list of `MatchSyncResult` dataclass with match and `goals_changed` flag
- Add type hints and docstrings
- Handle missing team references gracefully (log warning, skip match)

### Out of Scope
- Management commands (Tasks 4-5)
- Calling ScoringService (done in Task 5)
- API client implementation (Task 1)

### Acceptance Criteria
- `sync_teams_from_api()` function exists and works
- `sync_matches_from_api()` function exists and works
- Teams are upserted by `fifa_code`
- Matches are upserted by `external_id`
- Status mapping follows design doc table
- Round mapping follows design doc table
- Goal changes are detected and flagged
- Missing teams are logged and skipped
- All functions have type hints and docstrings
- Code passes mypy and ruff

### Required Tests
- Unit test: `test_sync_teams_creates_new_teams()` - Mock API, verify Team creation
- Unit test: `test_sync_teams_updates_existing_teams()` - Verify update by fifa_code
- Unit test: `test_sync_matches_creates_new_matches()` - Mock API, verify Match creation
- Unit test: `test_sync_matches_updates_existing_matches()` - Verify update by external_id
- Unit test: `test_sync_matches_detects_goal_changes()` - Verify goals_changed flag
- Unit test: `test_sync_matches_status_mapping()` - Verify all status transitions
- Unit test: `test_sync_matches_round_mapping()` - Verify all round mappings
- Unit test: `test_sync_matches_skips_missing_teams()` - Verify graceful handling

---

## Task 4: Create Sync Teams Command

### Goal
Create a Django management command to sync teams from the football-data.org API.

### Scope
- Create `matches/management/commands/sync_teams.py`
- Call `sync_teams_from_api()` from Task 3
- Output counts of created and updated teams
- Add `--competition` option (default: WC)

### Out of Scope
- Sync matches (Task 5)
- API client implementation (Task 1)
- Sync service implementation (Task 3)

### Acceptance Criteria
- Command `python manage.py sync_teams` works
- Outputs created/updated team counts
- `--competition` option is available
- Default competition is WC
- API errors result in non-zero exit code
- Code passes mypy and ruff

### Required Tests
- Command test: `test_sync_teams_command_runs()` - Mock API, verify execution
- Command test: `test_sync_teams_command_output()` - Verify stdout message
- Command test: `test_sync_teams_command_competition_option()` - Verify option handling

---

## Task 5: Create Update Matches Command

### Goal
Create a Django management command that runs in a persistent while-loop, syncs matches from the API, and triggers scoring when goals change.

### Scope
- Create `matches/management/commands/update_matches.py`
- Implement main while-loop
- Call `sync_matches_from_api()` on each iteration
- For each match with `goals_changed=True`:
  - Call `ScoringService.score_all_predictions_for_match(match)`
- For final match when finished:
  - Call `ScoringService.score_champion_predictions()`
- Implement adaptive polling intervals per design doc
- Handle SIGTERM/SIGINT for graceful shutdown
- Log each iteration with interval and match counts
- Add `--once` flag for single iteration (testing)
- Error handling: log exception, sleep 60s, continue loop

### Out of Scope
- API client implementation (Task 1)
- Sync service implementation (Task 3)
- ScoringService changes (already exists)

### Acceptance Criteria
- Command `python manage.py update_matches` starts and runs
- Loop continues until SIGTERM/SIGINT
- Scoring triggered on goal changes
- Champion scoring triggered after final match finishes
- Polling interval adapts to match schedule (see design doc table)
- Graceful shutdown completes current iteration
- Errors are logged and loop continues
- `--once` flag runs single iteration and exits
- All intervals match design doc specifications
- Code passes mypy and ruff

### Required Tests
- Command test: `test_update_matches_once_flag()` - Verify single iteration mode
- Unit test: `test_calculate_sleep_interval_live_match()` - Returns 30s
- Unit test: `test_calculate_sleep_interval_no_matches()` - Returns 1800s
- Unit test: `test_calculate_sleep_interval_match_soon()` - Returns 60s for <30min
- Unit test: `test_calculate_sleep_interval_match_in_2h()` - Returns 300s
- Unit test: `test_calculate_sleep_interval_match_later()` - Returns 600s
- Integration test: `test_update_matches_triggers_scoring()` - Mock API with goal change, verify score_all_predictions called
- Integration test: `test_update_matches_triggers_champion_scoring()` - Mock final match finished, verify champion scoring called
- Unit test: `test_update_matches_continues_after_error()` - Verify error handling

---

## Task 6: End-to-End Integration Test

### Goal
Create an integration test that verifies the full flow: API sync → goal change detection → scoring → user points update.

### Scope
- Create test in `matches/tests/test_api_integration.py`
- Set up test data: users, teams, matches, predictions
- Mock API response with updated goals
- Run `sync_matches_from_api()` and trigger scoring
- Verify `MatchPrediction.points_earned` is calculated
- Verify `User.total_points` is updated
- Verify multiple predictions for same match are all scored

### Out of Scope
- Real API calls (use mocks)
- Management command testing (covered in Tasks 4-5)
- UI testing

### Acceptance Criteria
- Integration test exists and passes
- Test covers full flow from API response to user points
- Uses realistic test data structure
- Verifies all user predictions are scored
- Verifies User.total_points reflects sum of all predictions
- Code passes mypy and ruff

### Required Tests
- Integration test: `test_full_sync_and_scoring_flow()` - End-to-end verification
- Integration test: `test_multiple_users_scored_for_same_match()` - Verify all users affected
- Integration test: `test_incremental_goal_updates()` - Simulate 0:0 → 1:0 → 1:1 sequence

---

## Task 7: Documentation

### Goal
Document the API integration setup, configuration, and operations.

### Scope
- Add section to README.md for API configuration
- Document environment variables required
- Document management commands and their options
- Add troubleshooting section for common API errors
- Document deployment considerations (running updater process)

### Out of Scope
- Code implementation
- Inline code documentation (covered in other tasks)
- User-facing documentation

### Acceptance Criteria
- README includes API setup section
- Environment variables are documented
- Command usage examples are provided
- Rate limit considerations are explained
- Deployment notes for running updater process
- Troubleshooting section exists

### Required Tests
- None (documentation task)
