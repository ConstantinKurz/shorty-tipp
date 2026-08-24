# Design: Scoring Reliability Improvements

## Overview

This change addresses six reliability issues with minimal code changes, preserving the current architecture.

---

## 1. Champion Bonus Preservation in `recalculate_user_score()`

### Current Code

```python
# scoring/ranking_service.py line 229
user.total_points = total_points
user.exact_match_count = exact_match_count
user.jokers_used = jokers_used
user.save(update_fields=["total_points", "exact_match_count", "jokers_used"])
```

### Fixed Code

```python
# scoring/ranking_service.py line 229
user.total_points = total_points + user.champion_bonus_points
user.exact_match_count = exact_match_count
user.jokers_used = jokers_used
user.save(update_fields=["total_points", "exact_match_count", "jokers_used"])
```

### Test Case

```python
def test_recalculate_user_score_preserves_champion_bonus(db):
    """recalculate_user_score() must preserve champion_bonus_points in total_points."""
    user = User.objects.create_user(username="test", password="test")
    user.champion_bonus_points = 20
    user.total_points = 26  # 6 from match + 20 champion
    user.save()
    
    # Create a scored prediction worth 6 points
    match = create_finished_match(goals_home=2, goals_away=1)
    prediction = MatchPrediction.objects.create(
        user=user, match=match,
        predicted_home=2, predicted_away=1,
        points_earned=6, is_exact_match=True
    )
    
    RankingService.recalculate_user_score(user)
    user.refresh_from_db()
    
    assert user.total_points == 26  # 6 + 20, NOT just 6
```

---

## 2. Match Updater Active Window

### Current Logic

```python
def _calculate_sleep_interval(self) -> int:
    now = timezone.now()
    
    if Match.objects.filter(status="live").exists():
        return 30
    
    next_match = Match.objects.filter(kickoff__gt=now, status="scheduled").order_by("kickoff").first()
    # ... adaptive intervals based on time until kickoff
```

### Fixed Logic

```python
ACTIVE_WINDOW_BEFORE = timedelta(minutes=30)
ACTIVE_WINDOW_AFTER = timedelta(hours=3)

def _calculate_sleep_interval(self) -> int:
    now = timezone.now()
    
    # Check for live matches
    if Match.objects.filter(status="live").exists():
        return 10
    
    # Check for matches in active window (kickoff passed but not finished)
    active_window_start = now - ACTIVE_WINDOW_AFTER
    active_window_end = now + ACTIVE_WINDOW_BEFORE
    
    has_active_window_match = Match.objects.filter(
        kickoff__gte=active_window_start,
        kickoff__lte=active_window_end,
        status__in=["scheduled", "live"],
    ).exists()
    
    if has_active_window_match:
        return 30  # Poll frequently during active window
    
    # Find next upcoming match
    next_match = Match.objects.filter(
        kickoff__gt=now,
        status="scheduled"
    ).order_by("kickoff").first()
    
    if not next_match:
        return 1800  # 30 minutes
    
    time_until = (next_match.kickoff - now).total_seconds()
    
    if time_until < 1800:  # < 30 minutes
        return 60
    elif time_until < 7200:  # < 2 hours  
        return 300
    else:
        return 600
```

### Test Cases

```python
def test_active_window_match_after_kickoff_not_live(db):
    """Match with kickoff passed but status still scheduled should trigger fast polling."""
    # kickoff was 1 minute ago, status still "scheduled"
    Match.objects.create(
        kickoff=timezone.now() - timedelta(minutes=1),
        status="scheduled",
        ...
    )
    
    interval = command._calculate_sleep_interval()
    assert interval == 30

def test_active_window_excludes_finished_matches(db):
    """Finished matches should not trigger active window polling."""
    Match.objects.create(
        kickoff=timezone.now() - timedelta(hours=1),
        status="finished",
        ...
    )
    
    interval = command._calculate_sleep_interval()
    assert interval != 30  # Should use normal slow interval
```

---

## 3. Invalid Round Code Validation

### Current Code

```python
# scoring/match_scoring.py line 191
return ScoringService.ROUND_MULTIPLIERS.get(match_round, 1)
```

### Fixed Code

```python
# scoring/match_scoring.py
VALID_ROUNDS = frozenset({"group", "r32", "r16", "qf", "sf", "3rd", "final"})

@staticmethod
def _get_round_multiplier(match_round: str) -> int:
    if match_round not in ScoringService.VALID_ROUNDS:
        raise ValueError(
            f"Unknown round '{match_round}'. "
            f"Valid rounds: {', '.join(sorted(ScoringService.VALID_ROUNDS))}"
        )
    return ScoringService.ROUND_MULTIPLIERS[match_round]
```

### Test Case

```python
def test_invalid_round_code_raises_error():
    """Unknown round codes must raise ValueError, not silently default to 1."""
    with pytest.raises(ValueError, match="Unknown round 'playoffs'"):
        ScoringService._get_round_multiplier("playoffs")

def test_valid_round_codes():
    """All valid round codes return correct multipliers."""
    assert ScoringService._get_round_multiplier("group") == 1
    assert ScoringService._get_round_multiplier("r16") == 2
    assert ScoringService._get_round_multiplier("final") == 3
```

---

## 4. Scoring Aggregate Test Matrix

### Test Cases to Add

| Scenario | Before | After | Expected Change |
|----------|--------|-------|-----------------|
| First scoring | 0 pts | 6 pts | total_points +6 |
| Unchanged rescore | 6 pts | 6 pts | delta 0 |
| Changed result | 6 pts | 3 pts | total_points -3 |
| Non-exact → exact | - | exact | exact_match_count +1 |
| Exact → non-exact | exact | - | exact_match_count -1 |
| Joker first scored | - | - | jokers_used +1 |
| Joker rescored | joker | joker | jokers_used unchanged |
| Champion bonus | 6 + 20 | - | total_points == 26 |

### Test Location

Add to `scoring/tests/test_scoring_aggregates.py` (new file) or extend `scoring/tests/test_integration.py`.

---

## 5. Remove Unused exists() Query

### Current Code

```python
# scoring/match_scoring.py line 294
MatchPredictionModel.objects.filter(user=user).exists()  # Ensure user relationship

UserModel.objects.filter(pk=user.pk).update(...)
```

### Fixed Code

```python
# scoring/match_scoring.py - line 294 removed
# Just keep the update:
UserModel.objects.filter(pk=user.pk).update(...)
```

---

## 6. Winner Field for Match Model

### Model Change

```python
# matches/models.py - Match model
WINNER_CHOICES = [
    ('home', 'Home Team'),
    ('away', 'Away Team'),
    ('draw', 'Draw'),
]

winner: models.CharField = models.CharField(
    max_length=10,
    choices=WINNER_CHOICES,
    null=True,
    blank=True,
    help_text="Match winner from API. For knockout matches with penalties, this shows the actual winner (home/away), while goals_home/goals_away contain the score before penalties."
)
```

### API Mapping

```python
# matches/services.py
API_WINNER_MAP = {
    "HOME_TEAM": "home",
    "AWAY_TEAM": "away",
    "DRAW": "draw",
}

def _sync_match(match_data: dict[str, Any]) -> MatchSyncResult | None:
    # ... existing code ...
    
    # Extract winner - for penalty shootouts, this is the actual winner
    # while fullTime score remains the pre-penalty result
    winner_api = match_data.get("score", {}).get("winner")
    winner = API_WINNER_MAP.get(winner_api)  # None if not in map
    
    match, created = Match.objects.update_or_create(
        external_id=external_id,
        defaults={
            # ... existing fields ...
            "winner": winner,
        },
    )
```

### Migration

```python
# matches/migrations/0005_match_winner.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('matches', '0004_match_external_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='winner',
            field=models.CharField(
                blank=True,
                choices=[('home', 'Home Team'), ('away', 'Away Team'), ('draw', 'Draw')],
                help_text="Match winner from API (home/away/draw). Null for scheduled matches.",
                max_length=10,
                null=True,
            ),
        ),
    ]
```

### Usage in Champion Scoring

Keep existing live goal-based logic. Only change: use `winner` field instead of `is_champion` for penalty shootout case.

**Important**: For knockout matches with penalty shootout:
- `goals_home` / `goals_away` = Score after extra time (e.g., 1-1)
- `winner` = Actual match winner (e.g., "home" if home team won on penalties)

```python
# scoring/champion_scoring.py - get_current_champion_team()
# Only the else branch changes - rest stays identical

if final_match.goals_home is not None and final_match.goals_away is not None:
    home_goals = final_match.goals_home
    away_goals = final_match.goals_away

    if home_goals > away_goals:
        # Home team is leading/won - UNCHANGED
        return final_match.team_home
    elif away_goals > home_goals:
        # Away team is leading/won - UNCHANGED
        return final_match.team_away
    else:
        # Draw - use winner field (penalty shootout winner)
        # CHANGED: was is_champion, now winner field
        if final_match.winner == "home":
            return final_match.team_home
        elif final_match.winner == "away":
            return final_match.team_away
        return None
```

**Note**: `Team.is_champion` field becomes obsolete and can be removed in a follow-up cleanup.

---

## Files Changed

| File | Change |
|------|--------|
| `scoring/ranking_service.py` | Fix champion bonus preservation |
| `matches/management/commands/update_matches.py` | Active window logic |
| `scoring/match_scoring.py` | Round validation, remove exists() |
| `scoring/services.py` | Round validation (if separate) |
| `matches/models.py` | Add winner field |
| `matches/services.py` | Parse winner from API |
| `matches/migrations/0005_match_winner.py` | New migration |
| `scoring/champion_scoring.py` | Use winner field instead of is_champion |
| `scoring/tests/test_scoring_aggregates.py` | New test file |
| `matches/tests/test_update_matches_command.py` | Active window tests |
| `scoring/tests/test_match_scoring.py` | Round validation tests |
| `scoring/tests/test_champion_scoring.py` | Update tests to use winner field |

### Follow-up Cleanup (separate change)

| File | Change |
|------|--------|
| `matches/models.py` | Remove `Team.is_champion` field |
| `matches/migrations/` | Migration to remove is_champion |

---

## Rollback Plan

All changes are additive or simple fixes:
1. Winner field: nullable, won't break existing code
2. Active window: fallback to existing behavior if removed
3. Round validation: can revert to `.get()` fallback
4. Tests: can be removed without breaking production

No complex migrations or data transformations required.
