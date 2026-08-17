# Tasks: Scoring Reliability Fixes

## Task 1: Add get_current_champion_team() method for live scoring

### Goal
Enable leaderboard to show provisional champion bonus during live final.

### Scope
- Add `ScoringService.get_current_champion_team()` method
- Add `ScoringService.get_live_champion_bonus_for_user()` helper method
- Handle all final states: scheduled, live with leader, live with draw, finished

### Out of Scope
- Persisting live champion data (this is read-only calculation)
- Integrating with leaderboard view (separate task if needed)

### Acceptance Criteria
- [ ] Method returns None when final not started
- [ ] Method returns leading team when final is live and one team leads
- [ ] Method returns team with `is_champion=True` when final is live and drawn
- [ ] Method returns winning team when final is finished
- [ ] `get_live_champion_bonus_for_user()` calculates correct bonus (20/30)
- [ ] Has docstring explaining the logic

### Required Tests
- Test returns None for scheduled final
- Test returns home team when home leads during live final
- Test returns away team when away leads during live final
- Test returns is_champion team on draw during live final
- Test returns winning team after finished final
- Test get_live_champion_bonus_for_user returns correct points

---

## Task 2: Add champion_bonus_points field to User model

### Goal
Track champion prediction bonus points separately to enable idempotent scoring.

### Scope
- Add `champion_bonus_points` IntegerField to User model
- Create database migration
- Update UserAdmin to display the field (read-only)

### Out of Scope
- Backfilling existing data (separate task)
- Changing scoring logic (separate task)

### Acceptance Criteria
- [ ] `champion_bonus_points` field added to User model with default=0
- [ ] Field has help_text explaining its purpose
- [ ] Migration file created and tested
- [ ] UserAdmin shows field in readonly_fields
- [ ] UserAdmin fieldsets include the new field in Statistics section

### Required Tests
- Test field default value is 0
- Test field can be set and retrieved
- Test migration applies cleanly

---

## Task 3: Update score_champion_predictions() to be idempotent

### Goal
Prevent double-awarding of champion bonus points.

### Scope
- Update `ScoringService.score_champion_predictions()` to check `champion_bonus_points`
- Only award to users where `champion_bonus_points == 0`
- Set `champion_bonus_points` when awarding
- Update both fields atomically

### Out of Scope
- Backfilling existing data (separate task)
- Changing point values

### Acceptance Criteria
- [ ] Method filters users by `champion_bonus_points=0`
- [ ] Method sets `champion_bonus_points` to awarded amount
- [ ] Calling method twice has same result as once
- [ ] Users without correct prediction not affected
- [ ] Category A gets 20 points, Category B gets 30 points

### Required Tests
- Test first call awards points correctly
- Test second call doesn't add more points (idempotent)
- Test different categories award different amounts
- Test users with wrong prediction get nothing

---

## Task 4: Backfill champion_bonus_points for existing data

### Goal
Ensure existing users with champion predictions have correct tracking.

### Scope
- Create data migration or management command
- Find users who predicted correctly and have bonus in total
- Set their champion_bonus_points field
- Handle case where no champion is set yet

### Out of Scope
- Recalculating total_points (should already be correct)

### Acceptance Criteria
- [ ] Migration/command identifies users with correct champion prediction
- [ ] Sets champion_bonus_points to appropriate value (20 or 30)
- [ ] Handles case where tournament not yet finished
- [ ] Safe to run multiple times (idempotent)

### Required Tests
- Test backfill sets correct bonus amount
- Test backfill handles no champion case
- Test running twice doesn't break data

---

## Task 5: Create PredictionLimitService.is_match_locked() method

### Goal
Centralize locktime check to ensure consistent 3-minute buffer everywhere.

### Scope
- Add `LOCK_BUFFER_MINUTES = 3` constant to PredictionLimitService
- Add `is_match_locked(match, reference_time=None)` class method
- Method returns True when `now >= kickoff - 3 minutes`
- Accept optional reference_time parameter for testing

### Out of Scope
- Updating views to use this method (separate task)

### Acceptance Criteria
- [ ] `LOCK_BUFFER_MINUTES` constant defined as 3
- [ ] Method added to PredictionLimitService in `predictions/services.py`
- [ ] Returns True when `reference_time >= kickoff - 3 minutes`
- [ ] Returns False when `reference_time < kickoff - 3 minutes`
- [ ] Uses `timezone.now()` when reference_time not provided
- [ ] Has docstring explaining 3-minute buffer rule

### Required Tests
- Test returns True when 2 minutes before kickoff
- Test returns False when 4 minutes before kickoff
- Test boundary at exactly 3 minutes
- Test with explicit reference_time parameter

---

## Task 6: Update views to use centralized locktime check

### Goal
Replace all hardcoded locktime checks with the centralized method.

### Scope
- Update `PredictionListView.get_context_data()` (currently `kickoff <= now`)
- Update `_get_match_row_context()` (currently `kickoff - 3min`)
- Update `_get_match_predictions_form_context()`
- Update `PredictionSaveView.post()`
- Update `PredictionDeleteView.post()`
- Update `PredictionJokerView.post()`

### Out of Scope
- Changing lock behavior (just centralizing with 3-minute buffer)

### Acceptance Criteria
- [ ] All locktime checks in predictions/views.py use `PredictionLimitService.is_match_locked()`
- [ ] No direct `match.kickoff <= now` comparisons remain
- [ ] No `match.kickoff - timedelta(...)` comparisons remain
- [ ] 3-minute buffer consistently applied everywhere
- [ ] All existing view tests pass

### Required Tests
- Test PredictionListView shows correct lock state
- Test PredictionSaveView rejects saves at 2 minutes before kickoff
- Test PredictionSaveView allows saves at 4 minutes before kickoff
- Test consistency between initial render and HTMX row updates

---

## Task 7: Add integration tests

### Goal
Verify champion scoring and locktime work correctly end-to-end.

### Scope
- Test champion scoring idempotency
- Test locktime consistency across all views
- Test dynamic champion detection during live final

### Acceptance Criteria
- [ ] Integration test: score champion twice → verify no double points
- [ ] Integration test: locktime consistent between page load and HTMX
- [ ] Integration test: live champion bonus shown correctly during final
- [ ] All existing tests pass

### Required Tests
- Champion scoring idempotency test
- Locktime consistency test across view types
- Live champion detection during various final states
