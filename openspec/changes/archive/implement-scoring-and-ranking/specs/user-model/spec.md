## ADDED Requirements

### Requirement: User cumulative statistics

The system SHALL track cumulative scoring statistics on User model.

#### Scenario: Statistics initialized on creation
- **WHEN** user is created
- **THEN** total_points, exact_match_count, and jokers_used default to 0

#### Scenario: Statistics updated on prediction scoring
- **WHEN** user's prediction is scored
- **THEN** statistics are incremented based on points earned, exact matches, and joker usage

#### Scenario: Statistics used for ranking
- **WHEN** generating leaderboard
- **THEN** users are ordered by total_points, exact_match_count, jokers_used

#### Scenario: Statistics displayed in admin
- **WHEN** viewing user in admin
- **THEN** total_points, exact_match_count, and jokers_used are visible

#### Scenario: Statistics reset for recalculation
- **WHEN** scores are recalculated
- **THEN** statistics can be reset to 0 and rebuilt from predictions
