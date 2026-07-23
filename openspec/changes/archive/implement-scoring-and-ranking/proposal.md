## Why

The prediction models exist but lack the core game functionality: calculating points and generating rankings. Without scoring logic, users cannot see their performance, and without ranking logic, there's no leaderboard or winner determination. This change implements the complete scoring engine and ranking system based on WM 2026 game rules.

## What Changes

- Create scoring service to calculate match prediction points (exact: 6, tendency+diff: 5, tendency+one_goal: 4, tendency: 3, one_goal: 1, none: 0)
- Implement round multipliers (group: x1, r32/r16: x2, qf/sf/final: x3)
- Implement joker doubling (applied after round multiplier)
- Calculate champion prediction points based on Team.is_champion field (category A: 20, category B: 30)
- Auto-score champion predictions when final match is scored and champion team is designated
- Automatic scoring when match results are entered
- Create ranking service with Olympic-style tiebreakers (total points → exact matches → jokers used)
- Add LeaderboardSnapshot model for historical ranking tracking
- Add user statistics tracking (total_points, jokers_used, exact_match_count on User model)
- Add Team.odds_category field to store champion prediction category (A or B)
- Export leaderboard as CSV and PDF
- Create management command for manual recalculation
- Update MatchPrediction with points_earned and is_exact_match when scored
- All rankings are public (no privacy filters)

## Capabilities

### New Capabilities
- `scoring-service`: Calculate points for match predictions and champion predictions based on WM 2026 rules
- `ranking-service`: Generate leaderboards with Olympic tiebreakers and historical snapshots
- `leaderboard-history`: Track ranking changes over time with daily/weekly snapshots
- `leaderboard-export`: Export rankings as CSV and PDF formats
- `user-statistics`: Track cumulative scoring statistics per user

### Modified Capabilities
- `match-prediction-model`: Points and exact match fields will be populated by scoring service
- `user-model`: Add statistics fields for ranking performance

## Impact

- New scoring app service layer (scoring/services.py)
- New LeaderboardSnapshot model in scoring app
- User model schema changes (add statistics fields)
- MatchPrediction scoring fields populated automatically
- Admin interface extended for leaderboard management
- New management commands for scoring and snapshots
- Foundation for real-time leaderboard updates
- Database: new leaderboard_snapshot table, new fields on users table
- All match result entries trigger automatic scoring
