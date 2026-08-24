# Proposal: Scoring Reliability Improvements

## Summary

Fix six scoring and match update reliability issues identified during code review:
1. Champion bonus lost in `recalculate_user_score()`
2. Match updater polling gap around kickoff
3. Silent fallback for invalid round codes
4. Missing/incomplete scoring aggregate tests
5. Unnecessary database query in `score_prediction()`
6. Missing winner field from API for knockout matches

## Problems

### 1. Champion Bonus Lost in `recalculate_user_score()`

**Location**: [scoring/ranking_service.py](scoring/ranking_service.py#L229)

The method calculates total_points from match predictions but overwrites champion_bonus:
```python
user.total_points = total_points  # WRONG: loses champion_bonus_points
```

User.total_points is defined as "Cached total points from all scored predictions **(including champion bonus)**".

**Invariant violated**:
```python
user.total_points == sum(scored_prediction.points_earned) + user.champion_bonus_points
```

**Impact**: If `recalculate_user_score()` runs after champion bonus is awarded, the bonus is lost.

### 2. Match Updater Polling Gap Around Kickoff

**Location**: [matches/management/commands/update_matches.py](matches/management/commands/update_matches.py#L124-L129)

Current logic:
```python
if Match.objects.filter(status="live").exists():
    return 30  # Poll frequently
next_match = Match.objects.filter(kickoff__gt=now, status="scheduled")...
```

**Problem**: If kickoff has passed but API still reports "scheduled":
- kickoff = 20:00, now = 20:01, status = "scheduled"
- Match is neither "live" nor `kickoff__gt=now`
- Match falls into slow polling (10 min) instead of frequent polling

**Impact**: Delayed result updates during the most critical time.

### 3. Silent Fallback for Invalid Round Codes

**Location**: [scoring/match_scoring.py](scoring/match_scoring.py#L191)

```python
return ScoringService.ROUND_MULTIPLIERS.get(match_round, 1)  # Silent fallback!
```

Valid rounds: `group`, `r32`, `r16`, `qf`, `sf`, `3rd`, `final`

**Impact**: An unknown round (typo, API change) silently gets multiplier 1, potentially awarding incorrect points without any error.

### 4. Missing Scoring Aggregate Tests

The User model has intentionally persisted aggregates for leaderboard performance:
- `total_points`
- `exact_match_count`
- `jokers_used`
- `champion_bonus_points`

Several edge cases lack test coverage:
- Rescoring unchanged prediction (delta should be 0)
- Result changes (6 → 3 points)
- exact → non-exact transitions
- Joker not double-counted on rescore
- Champion bonus preserved in `recalculate_user_score()`

### 5. Unnecessary Database Query

**Location**: [scoring/match_scoring.py](scoring/match_scoring.py#L294)

```python
MatchPredictionModel.objects.filter(user=user).exists()  # Ensure user relationship
```

Return value is unused. Comment says "ensure user relationship" but this doesn't enforce anything.

### 6. Missing Winner Field from API

**Location**: [matches/services.py](matches/services.py#L208-L212)

football-data.org API provides a `winner` field (`HOME_TEAM`, `AWAY_TEAM`, `DRAW`, null) but we ignore it:
```python
score = match_data.get("score", {})
full_time = score.get("fullTime", {})
goals_home = full_time.get("home")
goals_away = full_time.get("away")
# winner field NOT extracted
```

**Impact**: For knockout matches with penalty shootouts, `fullTime` shows e.g. 1-1 but `winner` correctly indicates the actual winner. Without this, champion determination relies solely on manual `is_champion` flag.

## Solution

### 1. Fix Champion Bonus Preservation

Change [scoring/ranking_service.py](scoring/ranking_service.py#L229):
```python
user.total_points = total_points + user.champion_bonus_points
```

### 2. Fix Match Updater Active Window

Implement "active match window" logic:
- Consider match active from `kickoff - 30 min` until `kickoff + 3 hours`
- Poll frequently (30s) during active window regardless of status
- Adaptive intervals outside active window

### 3. Reject Invalid Round Codes

Replace fallback with explicit validation:
```python
if match_round not in ScoringService.ROUND_MULTIPLIERS:
    raise ValueError(f"Unknown round: {match_round}")
return ScoringService.ROUND_MULTIPLIERS[match_round]
```

### 4. Add Comprehensive Scoring Tests

Add test cases for:
- First scoring (0 → 6)
- Unchanged rescoring (6 → 6, delta 0)
- Changed result (6 → 3, total_points -3)
- Exact match transitions
- Joker edge cases
- Champion bonus invariant

### 5. Remove Unused Query

Delete the unused `exists()` call and its import if no longer needed.

### 6. Add Winner Field to Match Model

- Add `winner` CharField to Match model (nullable)
- Parse and store `winner` from API response
- Use for champion scoring on final match (especially DRAW handling)

## Non-Goals

- Redesigning the scoring architecture
- Adding Redis, Celery, or other infrastructure
- Changing point values or multipliers
- WebSocket/SSE for real-time updates

## Success Criteria

- [ ] `recalculate_user_score()` preserves champion bonus
- [ ] Match updater polls frequently during active window
- [ ] Invalid round codes raise clear errors
- [ ] All scoring aggregate edge cases tested
- [ ] Unused exists() query removed
- [ ] Winner field stored from API for all matches
