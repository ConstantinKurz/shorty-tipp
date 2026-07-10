## Why

The MatchPrediction model currently tracks user predictions but doesn't store the calculated points earned or identify exact score matches ("Sechser"). Without these fields, scoring calculations must be repeated for every query, and identifying perfect predictions requires runtime comparison. Adding these fields enables efficient scoring queries and leaderboard generation.

## What Changes

- Add `points_earned` field to MatchPrediction model to cache calculated points
- Add `is_exact_match` boolean field to identify perfect score predictions (Sechser)
- Update MatchPrediction model with proper type annotations and help text
- Add database migration for new fields
- Update admin interface to display points and exact matches
- Add tests for new fields and their behavior
- Update existing tests to account for new nullable fields

## Capabilities

### New Capabilities
<!-- No new capabilities - only modifying existing model -->

### Modified Capabilities
- `match-prediction-model`: Add points tracking and exact match identification to support efficient scoring and leaderboard queries

## Impact

- MatchPrediction model schema changes (migration required)
- Admin interface updated to show points_earned and is_exact_match
- Database: Two new columns on predictions_matchprediction table
- Existing MatchPrediction tests need updates for new nullable fields
- Foundation for scoring service to populate these fields when results are entered
