# Architectural Decisions

This document tracks major architectural and design decisions made during the development of the tipapp project.

## 2026-08-17: Code Structure Refactoring

**Context**: The original `scoring/services.py` file had grown to 700+ lines containing multiple service classes (`ScoringService` and `RankingService`) with different responsibilities. The codebase also had 10+ inline imports to work around circular dependency issues, and the `Match.save()` method directly imported and called `ScoringService`, creating tight coupling between the matches and scoring apps.

**Decision**: Refactor the code structure to improve separation of concerns and reduce coupling:

1. **Split services into focused modules**:
   - `scoring/match_scoring.py` - Match prediction scoring logic
   - `scoring/champion_scoring.py` - Champion prediction scoring logic
   - `scoring/ranking_service.py` - Leaderboard and ranking logic
   - `scoring/services.py` - Backward-compatibility facade

2. **Implement signal-based scoring**:
   - Created `matches/signals.py` with `match_result_entered` signal
   - Created `scoring/signals.py` with receivers for automatic scoring
   - Updated `Match.save()` to send signals instead of directly calling services
   - Registered signal receivers in `scoring/apps.py` ready() method

3. **Document remaining inline imports**:
   - TYPE_CHECKING imports for type hints (zero runtime cost)
   - Lazy imports in functions to avoid circular dependencies at runtime
   - All inline imports now have comments explaining why they're necessary

**Consequences**:

*Positive*:
- Better separation of concerns - each module has a single focus
- Decoupled architecture - matches app doesn't depend on scoring app
- Improved testability - can test signal receivers independently
- Better code navigation - easier to find specific functionality
- Consistent with Django patterns - uses signals like `users/signals.py`
- Backward compatible - existing imports continue to work via facade

*Negative*:
- Slightly more files to navigate (4 new files)
- Signal-based architecture adds indirection (but improves decoupling)
- Some inline imports still necessary for circular dependency avoidance

**Status**: Implemented

**Related Files**:
- `scoring/match_scoring.py`
- `scoring/champion_scoring.py`
- `scoring/ranking_service.py`
- `scoring/signals.py`
- `scoring/services.py` (facade)
- `matches/signals.py`
- `matches/models.py` (Match.save())
- `scoring/apps.py` (signal registration)

## 2026-08-24: Global Rank Caching

**Context**: Every leaderboard request was computing Olympic-style ranking via Python loop. With HTMX-heavy UI and concurrent users, this caused redundant calculations. During live matches with ~50 concurrent users, identical rank calculations were performed repeatedly for every leaderboard view.

**Decision**: Store computed `global_rank` on User model, updated via signal after match scoring.

**Implementation**:
- Added `global_rank` IntegerField to User model with database index
- Created `RankingService.update_all_user_ranks()` for bulk rank calculation
- Signal receiver calls `update_all_user_ranks()` after match scoring
- `get_current_leaderboard()` uses stored ranks when available, falls back to dynamic calculation
- Created `seed_global_ranks` management command for initial population and recovery

**Consequences**:

*Positive*:
- Leaderboard queries simplified to `ORDER BY global_rank`
- Single-column index scan vs. multi-column sort + Python loop
- Rank computed once per match result, read many times
- Atomic updates ensure consistency
- Backward compatible - fallback to dynamic calculation if ranks not populated

*Negative*:
- Ranks must be re-seeded if data is manually modified
- Additional field on User model
- Round-filtered rankings remain dynamic (acceptable trade-off)

*Mitigation*:
- Management command available for re-seeding
- Signal-based updates ensure ranks stay current
- Round-filtered views continue working as before

**Status**: Implemented
