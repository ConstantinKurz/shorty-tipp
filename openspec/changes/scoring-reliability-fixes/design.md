# Design: Scoring Reliability Fixes

## Overview

This change improves scoring reliability through three targeted fixes:
1. Enable live champion bonus points during the final
2. Track champion bonus points to prevent double-awarding
3. Centralize locktime calculation (3 minutes before kickoff)

All changes follow existing Django patterns and maintain backward compatibility.

## Architecture

### Component Overview

```
Scoring Reliability Fixes
├── Dynamic Champion Detection
│   └── scoring/services.py: Add get_current_champion_team() method
├── Champion Bonus Tracking
│   ├── users/models.py: Add champion_bonus_points field
│   ├── users/migrations: Add field migration
│   ├── users/admin.py: Display field in admin
│   └── scoring/services.py: Update scoring to be idempotent
└── Locktime Centralization
    ├── predictions/services.py: Add is_match_locked() method
    └── predictions/views.py: Update all checks to use centralized method
```

---

## Implementation Details

### 1. Dynamic Champion Detection During Final

**File**: `scoring/services.py`

Add method to determine current champion based on final match state:

```python
@staticmethod
def get_current_champion_team() -> "Team | None":
    """
    Get the current champion team based on final match state.
    
    Logic:
    - Final not started: None
    - Final live & one team leading: leading team is provisional champion
    - Final live & draw: team with is_champion=True (set by admin for penalty winner)
    - Final finished & one team won: winning team
    - Final finished & draw: team with is_champion=True
    
    Returns:
        Team instance or None if no champion can be determined
    """
    from matches.models import Match as MatchModel
    from matches.models import Team as TeamModel

    # Find the final match
    final_match = MatchModel.objects.filter(round="final").first()
    if not final_match:
        return None
    
    # Final not started yet
    if final_match.status == "scheduled":
        return None
    
    # Final has goals recorded
    if final_match.goals_home is not None and final_match.goals_away is not None:
        home_goals = final_match.goals_home
        away_goals = final_match.goals_away
        
        if home_goals > away_goals:
            # Home team is leading/won
            return final_match.team_home
        elif away_goals > home_goals:
            # Away team is leading/won
            return final_match.team_away
        else:
            # Draw - use is_champion flag (penalty shootout winner)
            try:
                return TeamModel.objects.get(is_champion=True)
            except (TeamModel.DoesNotExist, TeamModel.MultipleObjectsReturned):
                return None
    
    return None


@staticmethod
def get_live_champion_bonus_for_user(user: "User") -> int:
    """
    Calculate live champion bonus points for a user.
    
    Used for live leaderboard display during the final.
    Does NOT persist - call get_current_champion_team() to determine champion.
    
    Args:
        user: User to calculate bonus for
        
    Returns:
        Bonus points (20 or 30) if user predicted current champion, 0 otherwise
    """
    champion = ScoringService.get_current_champion_team()
    if champion is None:
        return 0
    
    if user.predicted_champion_id != champion.pk:
        return 0
    
    return ScoringService.calculate_champion_points(champion)
```

**Usage in RankingService**: The leaderboard can use `get_live_champion_bonus_for_user()` to show provisional champion points during the final without persisting them.

---

### 2. Champion Bonus Tracking

**File**: `users/models.py`

Add field to track awarded champion bonus:

```python
class User(AbstractUser):
    # ... existing fields ...

    champion_bonus_points: models.IntegerField = models.IntegerField(
        default=0,
        help_text="Champion prediction bonus points (20 for category A, 30 for category B, 0 if not awarded)"
    )
```

**File**: `users/admin.py`

Update admin to show field:

```python
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Add to readonly_fields
    readonly_fields = ["total_points", "exact_match_count", "jokers_used", "champion_bonus_points"]
    
    # Update fieldsets to include in Statistics section
    fieldsets = BaseUserAdmin.fieldsets + (
        # ...
        (
            "Statistics (read-only, calculated by scoring service)",
            {
                "fields": ("total_points", "exact_match_count", "jokers_used", "champion_bonus_points"),
            },
        ),
    )
```

**File**: `scoring/services.py`

Update `score_champion_predictions()` to be idempotent:

```python
@staticmethod
@transaction.atomic
def score_champion_predictions() -> int:
    """
    Score champion predictions after tournament ends.
    
    Idempotent: calling multiple times has the same effect as calling once.
    Only awards to users where champion_bonus_points == 0.
    """
    from matches.models import Match as MatchModel
    from matches.models import Team as TeamModel
    from users.models import User as UserModel

    # Find the champion team
    try:
        champion = TeamModel.objects.get(is_champion=True)
    except TeamModel.DoesNotExist:
        return 0
    except TeamModel.MultipleObjectsReturned:
        return 0

    # Check if final match is finished
    final_match = MatchModel.objects.filter(
        round="final", status="finished"
    ).first()
    if not final_match:
        return 0

    # Calculate points based on champion's odds category
    champion_points = ScoringService.calculate_champion_points(champion)
    if champion_points == 0:
        return 0

    # Award points only to users who:
    # 1. Predicted this champion
    # 2. Haven't already received the bonus (champion_bonus_points == 0)
    users_to_award = UserModel.objects.filter(
        predicted_champion=champion,
        champion_bonus_points=0,  # Not already awarded
    )

    count = users_to_award.update(
        champion_bonus_points=champion_points,
        total_points=F("total_points") + champion_points,
    )

    return count
```

---

### 3. Locktime Centralization (3 Minutes Before Kickoff)

**File**: `predictions/services.py`

Add centralized locktime check:

```python
from datetime import timedelta
from django.utils import timezone

from matches.models import Match


class PredictionLimitService:
    # ... existing constants ...
    
    # Lock buffer: predictions close 3 minutes before kickoff
    LOCK_BUFFER_MINUTES: int = 3

    @classmethod
    def is_match_locked(cls, match: Match, reference_time: timezone.datetime | None = None) -> bool:
        """
        Check if a match is locked for predictions.
        
        A match is locked 3 minutes before kickoff (LOCK_BUFFER_MINUTES).
        
        Args:
            match: Match to check
            reference_time: Time to compare against (default: now)
            
        Returns:
            True if match is locked (now >= kickoff - 3 minutes)
        """
        if reference_time is None:
            reference_time = timezone.now()
        lock_time = match.kickoff - timedelta(minutes=cls.LOCK_BUFFER_MINUTES)
        return reference_time >= lock_time
```

**File**: `predictions/views.py`

Update ALL locktime checks to use the centralized method:

```python
# In PredictionListView.get_context_data():
is_locked = PredictionLimitService.is_match_locked(match)

# In _get_match_row_context():
is_locked = PredictionLimitService.is_match_locked(match)

# In _get_match_predictions_form_context():
is_locked = PredictionLimitService.is_match_locked(match)

# In PredictionSaveView.post():
if PredictionLimitService.is_match_locked(match):
    return render(request, "predictions/prediction_error.html", 
                  {"error": "Spiel startet in weniger als 3 Minuten. Tipp nicht mehr möglich."}, 
                  status=400)

# In PredictionDeleteView.post():
if PredictionLimitService.is_match_locked(match):
    return render(...)

# In PredictionJokerView.post():
if PredictionLimitService.is_match_locked(match):
    return render(...)
```

---

## Testing Strategy

### Unit Tests

1. **Champion Bonus Tracking**
   - Test first award sets `champion_bonus_points` and updates `total_points`
   - Test second call doesn't add points again (idempotent)
   - Test different category bonuses (A=20, B=30)

2. **Locktime Centralization**
   - Test `is_match_locked()` returns True when `now >= kickoff - 3min`
   - Test `is_match_locked()` returns False when `now < kickoff - 3min`
   - Test boundary case at exactly 3 minutes

### Integration Tests

1. **End-to-end**
   - Score champion twice, verify no double points
   - Verify locktime consistent between page load and HTMX updates

---

## Migration Plan

1. Add `champion_bonus_points` field (database migration)
2. Backfill existing champion bonuses (if tournament already has champion)
3. Deploy code changes
4. Verify scoring works correctly
            
            # Check group stage jokers (should be 0)
            group_jokers = MatchPrediction.objects.filter(
                user=user,
                match__round='group',
                joker_active=True,
            ).count()
            if group_jokers > 0:
                violations.append(
                    f"User {user.username}: {group_jokers} jokers in group stage (not allowed)"
                )
            
            # Check group stage prediction limit
            group_predictions = MatchPrediction.objects.filter(
                user=user,
                match__round='group',
            ).count()
            if group_predictions > 36:
                violations.append(
                    f"User {user.username}: {group_predictions} group predictions (limit: 36)"
                )
        
        if violations:
            self.stdout.write(self.style.ERROR(f"Found {len(violations)} violations:"))
            for v in violations:
                self.stdout.write(self.style.WARNING(f"  - {v}"))
        else:
            self.stdout.write(self.style.SUCCESS("No violations found."))
```

---

## Testing Strategy

### Unit Tests

1. **Champion Bonus Tracking**
   - Test first award sets `champion_bonus_points` and updates `total_points`
   - Test second call doesn't add points again (idempotent)
   - Test different category bonuses (A=20, B=30)

2. **Locktime Centralization**
   - Test `is_match_locked()` returns True when `now >= kickoff - 3min`
   - Test `is_match_locked()` returns False when `now < kickoff - 3min`
   - Test boundary case at exactly 3 minutes

3. **Model Validation**
   - Test `clean()` raises ValidationError for locked match
   - Test `clean()` raises ValidationError for joker limit exceeded
   - Test `clean()` raises ValidationError for group stage joker
   - Test `clean()` raises ValidationError for group stage limit exceeded

### Integration Tests

1. **Database Trigger**
   - Test raw SQL INSERT with valid joker succeeds
   - Test raw SQL INSERT violating joker limit fails with exception
   - Test raw SQL UPDATE setting joker on group match fails

2. **End-to-end**
   - Score champion twice, verify no double points
   - Create predictions via different paths, verify all respect locktime

---

## Migration Plan

1. Add `champion_bonus_points` field (database migration)
2. Backfill existing champion bonuses
3. Add PostgreSQL trigger for joker limits
4. Deploy code changes
5. Run `audit_predictions` to verify data integrity

---

## Security Considerations

- Database trigger prevents bypassing application layer
- Model `clean()` provides defense-in-depth
- Locktime enforced at both application and trigger level
- Audit command allows detection of any past violations
