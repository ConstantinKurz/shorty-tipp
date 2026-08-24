# Design: Stored Global Rank for Performance

## Overview

This change adds a `global_rank` field to the User model, updated via signal after match scoring. The ranking calculation logic remains in `RankingService` but results are persisted for fast retrieval.

---

## 1. User Model Extension

### Location
[users/models.py](users/models.py)

### Changes

```python
class User(AbstractUser):
    # Existing fields...
    
    global_rank: models.IntegerField = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Current global leaderboard rank (Olympic-style, updated after each match result)"
    )
```

### Migration

New migration `0003_add_global_rank.py`:
- Add `global_rank` field (nullable initially)
- Add database index on `global_rank`

### Rationale

- `null=True`: Allows unranked users (e.g., new users, inactive accounts)
- `db_index=True`: Fast `ORDER BY global_rank` queries
- No default value: Ranks must be explicitly computed, not assumed

---

## 2. Rank Update Service

### Location
[scoring/ranking_service.py](scoring/ranking_service.py)

### New Method

```python
@staticmethod
@transaction.atomic
def update_all_user_ranks() -> int:
    """
    Calculate Olympic-style ranking and persist to User.global_rank.
    
    Uses the same tiebreaker logic as get_current_leaderboard():
    1. Total points (higher is better)
    2. Exact match count (higher is better)  
    3. Jokers used (fewer is better)
    
    Returns:
        Number of users updated
    """
    from users.models import User
    
    # Get all active users sorted by ranking criteria
    users = list(
        User.objects.filter(is_active=True)
        .select_for_update()
        .order_by("-total_points", "-exact_match_count", "jokers_used")
    )
    
    if not users:
        return 0
    
    # Apply Olympic ranking
    current_rank = 1
    users_at_rank = 0
    prev_user = None
    
    for user in users:
        if prev_user is not None:
            same_rank = (
                user.total_points == prev_user.total_points
                and user.exact_match_count == prev_user.exact_match_count
                and user.jokers_used == prev_user.jokers_used
            )
            if not same_rank:
                current_rank += users_at_rank
                users_at_rank = 1
            else:
                users_at_rank += 1
        else:
            users_at_rank = 1
        
        user.global_rank = current_rank
        prev_user = user
    
    # Bulk update all ranks
    User.objects.bulk_update(users, ["global_rank"])
    
    return len(users)
```

### Design Decisions

1. **`select_for_update()`**: Prevents concurrent rank updates from creating inconsistent state
2. **`bulk_update()`**: Single query to update all users instead of N individual saves
3. **Same tiebreaker logic**: Reuses existing Olympic ranking rules from `_calculate_rank_numbers()`
4. **Returns count**: Useful for logging and verification

---

## 3. Signal Integration

### Location
[scoring/signals.py](scoring/signals.py)

### Modified Receiver

```python
@receiver(match_result_entered)
def score_predictions_on_result(sender, match, **kwargs):
    """
    Score all predictions when a match result is entered.
    After scoring, update all global ranks.
    """
    try:
        scored_count = ScoringService.score_all_predictions_for_match(match)
        logger.info(
            "Scored %d predictions for match %s",
            scored_count,
            match,
        )
        
        # Update global ranks after scoring
        rank_count = RankingService.update_all_user_ranks()
        logger.info(
            "Updated global ranks for %d users",
            rank_count,
        )
    except Exception:
        logger.exception(
            "Error scoring predictions for match %s",
            match,
        )
```

### Rationale

- Ranks update immediately after scoring, not as separate signal
- Single atomic operation ensures consistency
- Failure in rank update is logged but doesn't block scoring

---

## 4. View Simplification

### Affected Views

| View | File | Change |
|------|------|--------|
| Ranking page | [scoring/views.py](scoring/views.py) | Use `ORDER BY global_rank` |
| Home page | [tipapp/views.py](tipapp/views.py) | Use `ORDER BY global_rank` for top-N |
| User profile | [users/views.py](users/views.py) | Display `user.global_rank` directly |

### get_current_leaderboard() Changes

The method can be simplified when `global_rank` is populated:

```python
@staticmethod
def get_current_leaderboard() -> list[dict]:
    """
    Generate the current leaderboard with rankings.
    
    Uses stored global_rank for efficiency. Falls back to dynamic
    calculation if ranks are not populated.
    """
    users = UserModel.objects.filter(
        is_active=True,
        global_rank__isnull=False
    ).order_by("global_rank")
    
    if not users.exists():
        # Fallback: Calculate dynamically if no ranks stored
        return RankingService._get_leaderboard_dynamic()
    
    return [
        {
            "rank": user.global_rank,
            "user_id": user.pk,
            "username": user.username,
            "total_points": user.total_points,
            "exact_match_count": user.exact_match_count,
            "jokers_used": user.jokers_used,
        }
        for user in users
    ]
```

### Round-Filtered Leaderboard

`get_leaderboard_up_to_round()` remains unchanged — it calculates filtered rankings on-the-fly since they depend on round selection and aren't frequently accessed.

---

## 5. Management Command

### Location
[users/management/commands/seed_global_ranks.py](users/management/commands/seed_global_ranks.py)

### Purpose
- Initial population after migration
- Recovery from data corruption
- Manual re-sync if needed

### Implementation

```python
from django.core.management.base import BaseCommand
from scoring.ranking_service import RankingService


class Command(BaseCommand):
    help = "Calculate and store global ranks for all active users"

    def handle(self, *args, **options):
        self.stdout.write("Calculating global ranks...")
        
        count = RankingService.update_all_user_ranks()
        
        self.stdout.write(
            self.style.SUCCESS(f"Updated global ranks for {count} users")
        )
```

---

## 6. Data Flow

```
Match Result Entered
        │
        ▼
┌───────────────────┐
│  match_result_    │
│  entered signal   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ ScoringService.   │
│ score_all_        │
│ predictions_for_  │
│ match()           │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ RankingService.   │
│ update_all_user_  │
│ ranks()           │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ User.global_rank  │
│ updated for all   │
│ active users      │
└───────────────────┘
```

---

## 7. Backward Compatibility

### Transition Strategy

1. Migration adds nullable `global_rank` field
2. `get_current_leaderboard()` checks if ranks exist, falls back to dynamic calculation
3. Run `seed_global_ranks` command post-migration
4. Views continue working before and after seeding

### API Compatibility

- `get_current_leaderboard()` returns same dict structure
- `get_leaderboard_up_to_round()` unchanged
- Existing tests should pass without modification

---

## 8. Test Strategy

### New Test Cases

| Test | Purpose |
|------|---------|
| `test_update_all_user_ranks_basic` | Ranks assigned correctly for sorted users |
| `test_update_all_user_ranks_olympic_ties` | Shared ranks for tied users, gaps after ties |
| `test_update_all_user_ranks_after_scoring` | Ranks update after match result signal |
| `test_update_all_user_ranks_empty_users` | Handles no active users gracefully |
| `test_global_rank_index_used` | Verify ORDER BY uses index (explain query) |
| `test_seed_global_ranks_command` | Management command runs successfully |

### Existing Test Compatibility

All existing `test_ranking_service.py` tests should pass — they verify the output structure, not internal implementation.
