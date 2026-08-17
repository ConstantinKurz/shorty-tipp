# Proposal: Scoring Reliability Fixes

## Summary

Fix three scoring reliability issues: enable live champion bonus points during the final, prevent double-awarding of champion bonus points, and fix inconsistent locktime behavior.

## Problem

### 1. Champion Points Only Shown After Final Ends

**Location**: [scoring/services.py](scoring/services.py#L371-L422)

Currently, champion bonus points are only awarded when the final match is `finished`. During the final, users don't see their potential champion bonus even when their team is winning.

**Desired behavior**:
- **Final live & Team führt** → Users who predicted the leading team see champion bonus points
- **Final live & Unentschieden** → Users who predicted the team with `is_champion=True` see bonus (because penalty shootouts don't count for results)
- **Final finished** → Final result determines champion (or `is_champion` flag if draw)

**Impact**: During the most exciting part of the tournament, users can't see their potential champion bonus.

### 2. Champion Prediction Scoring Can Double-Award Points

**Location**: [scoring/services.py](scoring/services.py#L371-L422)

The `score_champion_predictions()` method adds champion bonus points to users' `total_points` using:

```python
users_to_award.update(total_points=F("total_points") + champion_points)
```

There is no tracking of whether the champion bonus was already awarded. If called multiple times (e.g., admin saves the final match twice, management command run repeatedly), points are added again.

**Impact**: Incorrect leaderboard rankings due to inflated point totals.

### 3. Locktime Check Inconsistency

**Locations**: 
- `PredictionListView.get_context_data()`: `is_locked = match.kickoff <= now`
- `_get_match_row_context()`: `is_locked = match.kickoff - timedelta(minutes=3) <= now`

The correct rule is: **predictions close 3 minutes before kickoff**. However, `PredictionListView` uses `kickoff <= now` (no buffer), while `_get_match_row_context()` correctly uses the 3-minute buffer.

**Impact**: Confusing UX and potential for late predictions in the 3-minute window.

## Solution

### 1. Dynamic Champion Bonus During Final

Create `ScoringService.get_current_champion_team()` method that:
- Returns the leading team during a live final
- Returns the `is_champion=True` team on a draw (live or finished)
- Returns the winning team when final is finished

This enables live leaderboards to show champion bonus dynamically without persisting it until the final ends.

### 2. Track Champion Bonus to Prevent Double-Award

- Add `champion_bonus_points` field to `User` model to track awarded bonus
- `score_champion_predictions()` checks if bonus already awarded before adding
- Bonus is stored separately so recalculation is straightforward

### 3. Centralize Locktime Calculation (3 Minutes Before Kickoff)

- Create `PredictionLimitService.is_match_locked(match, now)` method
- Define single source of truth: **lock = kickoff - 3 minutes**
- Update all views to use this method

## Non-Goals

- Database-level constraints (Django architecture already prevents direct DB access from clients)
- Changing the scoring algorithm or point values
- Real-time lock countdown UI

## Success Criteria

### Dynamic Champion Bonus
- [ ] `get_current_champion_team()` returns leading team during live final
- [ ] Returns `is_champion=True` team on draw
- [ ] Leaderboard shows live champion bonus during final

### Champion Bonus Tracking
- [ ] `User.champion_bonus_points` field tracks awarded bonus
- [ ] Calling `score_champion_predictions()` twice has same result as once
- [ ] Admin can see champion bonus in user detail

### Locktime Consistency
- [ ] Single `is_match_locked()` function used everywhere
- [ ] 3-minute buffer enforced consistently
- [ ] Tests verify consistent lock behavior

## Risks

### Low Risk: Migration Required
Adding `champion_bonus_points` field requires a migration. Existing users with champion predictions need backfill logic.

## Dependencies

None. All changes are internal to existing modules.
