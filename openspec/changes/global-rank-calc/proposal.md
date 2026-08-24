# Proposal: Stored Global Rank for Performance

## Summary

Store the calculated Olympic-style global rank directly on the User model, updating it via signal after each match result. This eliminates redundant rank calculations on every leaderboard request.

## Problem

**Current State:**
- Every call to `RankingService.get_current_leaderboard()` performs:
  1. Database query sorted by `(-total_points, -exact_match_count, jokers_used)`
  2. Python loop via `apply_olympic_ranking()` to assign shared rank numbers
- HTMX-heavy UI triggers frequent leaderboard requests
- With ~50 concurrent users during live matches, this causes redundant identical calculations

**Impact:**
- Wasted CPU cycles on identical rank calculations
- Unnecessary latency on every leaderboard view
- Poor scalability during peak match times

## Solution

Store the computed global rank on the User model and update it atomically after each match result is scored.

### Key Changes

1. **User Model**: Add `global_rank` IntegerField with index
2. **RankingService**: Add `update_all_user_ranks()` method for bulk rank calculation and update
3. **Signal**: Call `update_all_user_ranks()` after match scoring completes
4. **Views**: Simplify global leaderboard queries to `ORDER BY global_rank`
5. **Management Command**: Provide `seed_global_ranks` for initial data and recovery

### What Changes

| Component | Before | After |
|-----------|--------|-------|
| User model | No rank field | `global_rank` field + index |
| Leaderboard query | Sort + Python loop | `ORDER BY global_rank` |
| Match result signal | Score predictions | Score + update ranks |
| Round-filtered ranking | On-the-fly calculation | Unchanged (stays dynamic) |

## Benefits

- **Performance**: Single-column index scan vs. multi-column sort + Python
- **Consistency**: Rank computed once, read many times
- **Simplicity**: Views become trivial `ORDER BY` queries
- **Atomicity**: All ranks updated in single transaction

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Stale rank after manual DB edit | Management command for re-seeding |
| Transaction conflicts during bulk update | Single atomic transaction with `select_for_update` |
| Migration on production data | Run `seed_global_ranks` immediately after migration |

## Scope

### In Scope
- Add `global_rank` field to User model
- Update ranks via signal after match scoring
- Simplify global leaderboard views
- Management command for seeding/recovery

### Out of Scope
- Match-specific ranking (remains on-the-fly)
- Rank history or snapshots
- Per-round filtered ranking (remains on-the-fly)
- UI changes (rank display unchanged)

## Success Criteria

1. `global_rank` field exists with database index
2. Ranks update automatically after every match result
3. Olympic-style ties preserved (shared ranks, gaps after ties)
4. Global leaderboard views use `ORDER BY global_rank`
5. Tests verify rank correctness and update triggers
6. No regression in existing leaderboard functionality
