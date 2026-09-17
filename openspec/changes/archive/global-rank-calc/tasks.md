# Tasks: Stored Global Rank for Performance

## Task 1: Add global_rank Field to User Model

**Priority**: HIGH  
**Estimated Time**: 15 min  
**Dependencies**: None

### Goal
Add `global_rank` IntegerField to User model with database index.

### Scope
- [users/models.py](users/models.py) - Add field definition
- [users/migrations/](users/migrations/) - Create migration

### Implementation

1. Add field to User model:
   ```python
   global_rank: models.IntegerField = models.IntegerField(
       null=True,
       blank=True,
       db_index=True,
       help_text="Current global leaderboard rank (Olympic-style, updated after each match result)"
   )
   ```

2. Generate migration:
   ```bash
   python manage.py makemigrations users --name add_global_rank
   ```

3. Apply migration:
   ```bash
   python manage.py migrate users
   ```

### Out of Scope
- Populating rank values (Task 5)
- View changes (Task 4)

### Acceptance Criteria
- [x] `global_rank` field exists on User model
- [x] Field is nullable and indexed
- [x] Migration runs without errors
- [x] Existing tests pass

### Tests Required
- No new tests (migration tested by running it)

---

## Task 2: Implement update_all_user_ranks() Method

**Priority**: HIGH  
**Estimated Time**: 30 min  
**Dependencies**: Task 1

### Goal
Add method to calculate Olympic-style ranking and persist to `User.global_rank`.

### Scope
- [scoring/ranking_service.py](scoring/ranking_service.py) - Add `update_all_user_ranks()` method

### Implementation

Add to `RankingService`:

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
    users = list(
        UserModel.objects.filter(is_active=True)
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
    
    UserModel.objects.bulk_update(users, ["global_rank"])
    
    return len(users)
```

### Out of Scope
- Signal integration (Task 3)
- View changes (Task 4)

### Acceptance Criteria
- [x] Method calculates ranks using existing tiebreaker logic
- [x] Olympic ties handled correctly (shared rank, gap after)
- [x] All active users updated in single transaction
- [x] Inactive users excluded
- [x] Method returns count of users updated

### Tests Required
- `test_update_all_user_ranks_basic`
- `test_update_all_user_ranks_olympic_ties`
- `test_update_all_user_ranks_empty_users`
- `test_update_all_user_ranks_excludes_inactive`

---

## Task 3: Integrate Rank Update in Scoring Signal

**Priority**: HIGH  
**Estimated Time**: 15 min  
**Dependencies**: Task 2

### Goal
Call `update_all_user_ranks()` after match scoring completes.

### Scope
- [scoring/signals.py](scoring/signals.py) - Modify `score_predictions_on_result` receiver

### Implementation

Update the existing signal receiver:

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

Add import at top:
```python
from scoring.ranking_service import RankingService
```

### Out of Scope
- Changing scoring logic
- Handling champion bonus signal separately

### Acceptance Criteria
- [x] Ranks update after every match result
- [x] Rank update logged
- [x] Errors caught and logged without blocking
- [x] Existing scoring behavior unchanged

### Tests Required
- `test_ranks_update_after_match_result`
- `test_ranks_correct_after_multiple_match_results`

---

## Task 4: Simplify Global Leaderboard Views

**Priority**: MEDIUM  
**Estimated Time**: 30 min  
**Dependencies**: Task 2, Task 3

### Goal
Update `get_current_leaderboard()` to use stored `global_rank` instead of computing ranks.

### Scope
- [scoring/ranking_service.py](scoring/ranking_service.py) - Modify `get_current_leaderboard()`

### Implementation

Replace current implementation:

```python
@staticmethod
def get_current_leaderboard() -> list[dict]:
    """
    Generate the current leaderboard with rankings.
    
    Uses stored global_rank for efficiency. Falls back to dynamic
    calculation if ranks are not populated.
    """
    # Check if ranks are populated
    has_ranks = UserModel.objects.filter(
        is_active=True,
        global_rank__isnull=False
    ).exists()
    
    if has_ranks:
        # Use stored ranks
        users = UserModel.objects.filter(
            is_active=True,
            global_rank__isnull=False
        ).order_by("global_rank")
        
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
    
    # Fallback: Calculate dynamically
    return RankingService.get_leaderboard_up_to_round(round_code=None)
```

### Out of Scope
- `get_leaderboard_up_to_round()` (stays dynamic)
- UI template changes

### Acceptance Criteria
- [x] `get_current_leaderboard()` uses stored rank when available
- [x] Falls back to dynamic calculation if ranks not populated
- [x] Returns same dict structure as before
- [x] All existing leaderboard tests pass

### Tests Required
- `test_get_current_leaderboard_uses_stored_rank`
- `test_get_current_leaderboard_fallback_no_ranks`

---

## Task 5: Create seed_global_ranks Management Command

**Priority**: MEDIUM  
**Estimated Time**: 20 min  
**Dependencies**: Task 2

### Goal
Provide management command for initial rank population and recovery.

### Scope
- New file: [users/management/commands/seed_global_ranks.py](users/management/commands/seed_global_ranks.py)

### Implementation

```python
"""Management command to seed global ranks for all active users."""

from django.core.management.base import BaseCommand

from scoring.ranking_service import RankingService


class Command(BaseCommand):
    """Calculate and store global ranks for all active users."""
    
    help = "Calculate and store global ranks for all active users"

    def handle(self, *args, **options):
        self.stdout.write("Calculating global ranks...")
        
        count = RankingService.update_all_user_ranks()
        
        self.stdout.write(
            self.style.SUCCESS(f"Updated global ranks for {count} users")
        )
```

Create directory structure if needed:
```bash
mkdir -p users/management/commands
touch users/management/__init__.py
touch users/management/commands/__init__.py
```

### Out of Scope
- Automatic post-migration hook
- Dry-run mode

### Acceptance Criteria
- [x] Command exists at `python manage.py seed_global_ranks`
- [x] Command calls `RankingService.update_all_user_ranks()`
- [x] Success message shows count of users updated
- [x] Command runs without errors on empty database

### Tests Required
- `test_seed_global_ranks_command`

---

## Task 6: Add Comprehensive Rank Update Tests

**Priority**: MEDIUM  
**Estimated Time**: 45 min  
**Dependencies**: Task 2, Task 3

### Goal
Add tests verifying rank calculation, updates, and edge cases.

### Scope
- [scoring/tests/test_ranking_service.py](scoring/tests/test_ranking_service.py) - Add test cases

### Implementation

Add test class:

```python
class TestUpdateAllUserRanks:
    """Tests for RankingService.update_all_user_ranks()."""
    
    def test_update_all_user_ranks_basic(self, db):
        """Ranks assigned correctly for users with different scores."""
        # Create users with different scores
        user1 = User.objects.create_user("alice", password="test")
        user1.total_points = 100
        user1.exact_match_count = 5
        user1.jokers_used = 2
        user1.save()
        
        user2 = User.objects.create_user("bob", password="test")
        user2.total_points = 80
        user2.exact_match_count = 4
        user2.jokers_used = 3
        user2.save()
        
        count = RankingService.update_all_user_ranks()
        
        user1.refresh_from_db()
        user2.refresh_from_db()
        
        assert count == 2
        assert user1.global_rank == 1
        assert user2.global_rank == 2
    
    def test_update_all_user_ranks_olympic_ties(self, db):
        """Users with identical tiebreakers share rank, next rank skips."""
        user1 = User.objects.create_user("alice", password="test")
        user1.total_points = 100
        user1.exact_match_count = 5
        user1.jokers_used = 2
        user1.save()
        
        user2 = User.objects.create_user("bob", password="test")
        user2.total_points = 100  # Same
        user2.exact_match_count = 5  # Same
        user2.jokers_used = 2  # Same
        user2.save()
        
        user3 = User.objects.create_user("carol", password="test")
        user3.total_points = 80
        user3.exact_match_count = 4
        user3.jokers_used = 3
        user3.save()
        
        RankingService.update_all_user_ranks()
        
        user1.refresh_from_db()
        user2.refresh_from_db()
        user3.refresh_from_db()
        
        assert user1.global_rank == 1
        assert user2.global_rank == 1  # Tied
        assert user3.global_rank == 3  # Skips 2
    
    def test_update_all_user_ranks_empty_users(self, db):
        """Handles no active users gracefully."""
        count = RankingService.update_all_user_ranks()
        assert count == 0
    
    def test_update_all_user_ranks_excludes_inactive(self, db):
        """Inactive users are not ranked."""
        active_user = User.objects.create_user("active", password="test")
        active_user.total_points = 100
        active_user.save()
        
        inactive_user = User.objects.create_user("inactive", password="test")
        inactive_user.total_points = 200
        inactive_user.is_active = False
        inactive_user.save()
        
        count = RankingService.update_all_user_ranks()
        
        active_user.refresh_from_db()
        inactive_user.refresh_from_db()
        
        assert count == 1
        assert active_user.global_rank == 1
        assert inactive_user.global_rank is None
```

Add signal integration test:

```python
class TestRankUpdateSignal:
    """Tests for rank updates via match result signal."""
    
    def test_ranks_update_after_match_result(self, db, match, users_with_predictions):
        """Global ranks update after match result is entered."""
        # Verify ranks are None initially
        for user in users_with_predictions:
            user.refresh_from_db()
            assert user.global_rank is None
        
        # Enter match result
        match.goals_home = 2
        match.goals_away = 1
        match.status = "finished"
        match.save()
        
        # Trigger signal
        from matches.signals import match_result_entered
        match_result_entered.send(sender=match.__class__, match=match)
        
        # Verify ranks are now set
        for user in users_with_predictions:
            user.refresh_from_db()
            assert user.global_rank is not None
```

### Out of Scope
- Performance benchmarks
- Concurrency stress tests

### Acceptance Criteria
- [x] Basic ranking test passes
- [x] Olympic tie handling test passes
- [x] Empty users test passes
- [x] Inactive users excluded test passes
- [x] Signal integration test passes

### Tests Required
- All tests listed in Implementation section

---

## Task 7: Update Documentation

**Priority**: LOW  
**Estimated Time**: 15 min  
**Dependencies**: Task 1-5

### Goal
Document the new rank caching behavior.

### Scope
- [docs/project/decisions.md](docs/project/decisions.md) - Add ADR

### Implementation

Add to decisions.md:

```markdown
## Global Rank Caching

**Date**: 2026-08-24  
**Status**: Implemented

### Context
Every leaderboard request was computing Olympic-style ranking via Python loop.
With HTMX-heavy UI and concurrent users, this caused redundant calculations.

### Decision
Store computed `global_rank` on User model, updated via signal after match scoring.

### Consequences
- Leaderboard queries are simple `ORDER BY global_rank`
- Ranks must be re-seeded if data is manually modified
- Round-filtered rankings remain dynamic (acceptable trade-off)
- Added `seed_global_ranks` management command for recovery
```

### Out of Scope
- README updates
- API documentation

### Acceptance Criteria
- [x] ADR added to decisions.md
- [x] Documents rationale and trade-offs

### Tests Required
- None (documentation only)

---

## Summary

| Task | Priority | Est. Time | Dependencies |
|------|----------|-----------|--------------|
| 1. Add global_rank field | HIGH | 15 min | None |
| 2. Implement update_all_user_ranks() | HIGH | 30 min | Task 1 |
| 3. Integrate signal | HIGH | 15 min | Task 2 |
| 4. Simplify views | MEDIUM | 30 min | Task 2, 3 |
| 5. Management command | MEDIUM | 20 min | Task 2 |
| 6. Add tests | MEDIUM | 45 min | Task 2, 3 |
| 7. Update documentation | LOW | 15 min | Task 1-5 |

**Total Estimated Time**: ~2.5 hours

**Recommended Order**: 1 → 2 → 3 → 6 → 4 → 5 → 7
