# Tasks: Scoring Reliability Improvements

## Task 1: Fix Champion Bonus in recalculate_user_score()

**Priority**: HIGH  
**Estimated Time**: 15 min  
**Dependencies**: None

### Goal
Fix the bug where `recalculate_user_score()` overwrites champion bonus points.

### Scope
- `scoring/ranking_service.py` - line 229

### Implementation
1. Change `user.total_points = total_points` to `user.total_points = total_points + user.champion_bonus_points`

### Out of Scope
- Changing how champion bonus is calculated
- Modifying other scoring methods

### Acceptance Criteria
- [x] `recalculate_user_score()` preserves champion bonus in total_points
- [x] Test: user with champion_bonus_points=20 and match points=6 has total_points=26 after recalculate
- [x] Existing tests pass

### Tests Required
- `test_recalculate_user_score_preserves_champion_bonus`

---

## Task 2: Fix Match Updater Active Window

**Priority**: HIGH  
**Estimated Time**: 30 min  
**Dependencies**: None

### Goal
Fix polling gap where matches with `kickoff < now` and `status="scheduled"` are missed.

### Scope
- `matches/management/commands/update_matches.py` - `_calculate_sleep_interval()`

### Implementation
1. Add constants: `ACTIVE_WINDOW_BEFORE = timedelta(minutes=30)`, `ACTIVE_WINDOW_AFTER = timedelta(hours=3)`
2. Add active window check before next_match lookup
3. Poll frequently (30s) if any match is in active window and not finished

### Out of Scope
- Changing polling intervals for non-active periods
- Adding jitter to intervals

### Acceptance Criteria
- [x] Match with `kickoff = now - 1 min` and `status="scheduled"` triggers 30s polling
- [x] Finished matches don't trigger active window polling
- [x] Normal adaptive polling works outside active window
- [x] Existing tests pass

### Tests Required
- `test_active_window_match_after_kickoff_not_live`
- `test_active_window_excludes_finished_matches`
- `test_active_window_before_kickoff`

---

## Task 3: Reject Invalid Round Codes

**Priority**: MEDIUM  
**Estimated Time**: 20 min  
**Dependencies**: None

### Goal
Replace silent fallback with explicit error for unknown round codes.

### Scope
- `scoring/match_scoring.py` - `_get_round_multiplier()`
- `scoring/services.py` - `_get_round_multiplier()` (if exists separately)

### Implementation
1. Add `VALID_ROUNDS = frozenset({"group", "r32", "r16", "qf", "sf", "3rd", "final"})`
2. Check if `match_round in VALID_ROUNDS` before lookup
3. Raise `ValueError` with clear message if not valid
4. Remove `.get()` fallback

### Out of Scope
- Changing round codes or multipliers
- Adding new rounds

### Acceptance Criteria
- [x] Unknown round code raises `ValueError`
- [x] All valid rounds return correct multipliers
- [x] Error message lists valid rounds
- [x] Existing tests pass

### Tests Required
- `test_invalid_round_code_raises_error`
- `test_all_valid_round_codes_return_correct_multipliers`

---

## Task 4: Add Scoring Aggregate Tests

**Priority**: MEDIUM  
**Estimated Time**: 45 min  
**Dependencies**: Task 1 (for champion bonus test)

### Goal
Add comprehensive test coverage for scoring aggregate edge cases.

### Scope
- New file: `scoring/tests/test_scoring_aggregates.py`

### Implementation
Create tests for:
1. First scoring: 0 → 6 points
2. Unchanged rescoring: 6 → 6 (delta 0)
3. Changed result: 6 → 3 points
4. Non-exact → exact transition
5. Exact → non-exact transition
6. Joker first scored: jokers_used +1
7. Joker rescored: jokers_used unchanged
8. Champion bonus preserved in recalculate

### Out of Scope
- Testing scoring algorithm correctness (covered elsewhere)
- Performance testing

### Acceptance Criteria
- [x] All 8 edge cases have passing tests
- [x] Tests verify User model aggregates, not just prediction.points_earned
- [x] Tests are deterministic (no real-time dependencies)

### Tests Required
- `test_first_scoring_increments_total_points`
- `test_unchanged_rescoring_no_delta`
- `test_changed_result_decrements_points`
- `test_non_exact_to_exact_increments_count`
- `test_exact_to_non_exact_decrements_count`
- `test_joker_first_scored_increments_jokers_used`
- `test_joker_rescored_unchanged`
- `test_champion_bonus_invariant`

---

## Task 5: Remove Unused exists() Query

**Priority**: LOW  
**Estimated Time**: 10 min  
**Dependencies**: None

### Goal
Remove unnecessary database query that wastes a round trip.

### Scope
- `scoring/match_scoring.py` - line 294
- `scoring/services.py` - line 330 (if similar)

### Implementation
1. Delete line: `MatchPredictionModel.objects.filter(user=user).exists()`
2. Remove unused import if applicable

### Out of Scope
- Any other database query optimization

### Acceptance Criteria
- [x] Line removed from match_scoring.py
- [x] Line removed from services.py (if present)
- [x] All tests pass
- [x] No unused imports

### Tests Required
- Existing tests should pass (no new tests needed)

---

## Task 6: Add Winner Field to Match Model

**Priority**: MEDIUM  
**Estimated Time**: 30 min  
**Dependencies**: None

### Goal
Store API winner field for knockout match handling.

### Scope
- `matches/models.py` - Match model
- `matches/migrations/` - new migration

### Implementation
1. Add WINNER_CHOICES to Match model
2. Add `winner` CharField (nullable)
3. Create migration

### Out of Scope
- Using winner field in champion scoring (Task 8)
- Backfilling existing matches
- Removing `Team.is_champion` field (follow-up cleanup)

### Acceptance Criteria
- [x] `winner` field added to Match model
- [x] Field is nullable and blank
- [x] Choices: home, away, draw
- [x] Migration created and applies cleanly
- [x] All tests pass

### Tests Required
- `test_match_winner_field_nullable`
- `test_match_winner_choices_valid`

---

## Task 7: Parse Winner from API

**Priority**: MEDIUM  
**Estimated Time**: 20 min  
**Dependencies**: Task 6

### Goal
Extract and store winner field from football-data.org API response.

### Scope
- `matches/services.py` - `_sync_match()`

### Implementation
1. Add `API_WINNER_MAP = {"HOME_TEAM": "home", "AWAY_TEAM": "away", "DRAW": "draw"}`
2. Extract winner from `match_data.get("score", {}).get("winner")`
3. Map API value to model value
4. Include in `update_or_create` defaults

### Out of Scope
- Using winner for scoring logic (Task 8)
- Handling API edge cases beyond mapping

### Acceptance Criteria
- [x] API winner field extracted and mapped
- [x] Winner stored in Match model
- [x] Unknown API values result in None (not error)
- [x] Existing sync tests pass

### Tests Required
- `test_sync_match_stores_winner_home_team`
- `test_sync_match_stores_winner_away_team`
- `test_sync_match_stores_winner_draw`
- `test_sync_match_winner_null_for_scheduled`

---

## Task 8: Update Champion Scoring to Use Winner Field

**Priority**: MEDIUM  
**Estimated Time**: 15 min  
**Dependencies**: Task 6, Task 7

### Goal
Replace `Team.is_champion` lookup with `Match.winner` field for penalty shootout case.

### Scope
- `scoring/champion_scoring.py` - `get_current_champion_team()` else branch only
- `scoring/tests/test_champion_scoring.py`

### Implementation
1. Keep existing goal-based logic unchanged (live scoring still works via goals)
2. Replace only the else branch (draw/penalty case):
   ```python
   # OLD:
   return TeamModel.objects.get(is_champion=True)
   
   # NEW:
   if final_match.winner == "home":
       return final_match.team_home
   elif final_match.winner == "away":
       return final_match.team_away
   return None
   ```
3. Update tests to use winner field

### Out of Scope
- Removing `Team.is_champion` field (follow-up cleanup)
- Changing goal-based live scoring logic

### Acceptance Criteria
- [x] Penalty shootout uses `Match.winner` instead of `Team.is_champion`
- [x] Live scoring still works via goals (home_goals > away_goals etc.)
- [x] All champion scoring tests pass

### Tests Required
- `test_champion_from_winner_home`
- `test_champion_from_winner_away`
- `test_champion_penalty_shootout_winner_correct`
- `test_no_champion_if_final_not_finished`

---

## Summary

| Task | Priority | Est. Time | Dependencies |
|------|----------|-----------|--------------|
| 1. Champion bonus fix | HIGH | 15 min | None |
| 2. Active window fix | HIGH | 30 min | None |
| 3. Round validation | MEDIUM | 20 min | None |
| 4. Aggregate tests | MEDIUM | 45 min | Task 1 |
| 5. Remove exists() | LOW | 10 min | None |
| 6. Winner field model | MEDIUM | 30 min | None |
| 7. Parse winner API | MEDIUM | 20 min | Task 6 |
| 8. Champion scoring | MEDIUM | 15 min | Task 6, 7 |

**Total estimated time**: ~3 hours

**Recommended order**: 1 → 2 → 5 → 3 → 6 → 7 → 8 → 4
