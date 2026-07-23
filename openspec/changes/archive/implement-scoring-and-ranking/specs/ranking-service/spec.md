## ADDED Requirements

### Requirement: Leaderboard generation

The system SHALL generate current leaderboard from user statistics.

#### Scenario: Get current rankings
- **WHEN** current leaderboard is requested
- **THEN** all users are ranked by total_points descending
- **AND** each entry includes rank, user, points, exact matches, jokers used

#### Scenario: Empty leaderboard
- **WHEN** no users have scored predictions
- **THEN** empty leaderboard is returned

### Requirement: Olympic tiebreaker rules

The system SHALL apply Olympic-style tiebreakers for ranking.

#### Scenario: Rank by total points first
- **WHEN** users have different total_points
- **THEN** user with higher total_points ranks higher

#### Scenario: Tiebreak by exact matches
- **WHEN** users have same total_points
- **THEN** user with more exact_match_count ranks higher

#### Scenario: Tiebreak by jokers used
- **WHEN** users have same total_points AND same exact_match_count
- **THEN** user with more jokers_used ranks higher

#### Scenario: Shared rank
- **WHEN** users have identical total_points, exact_match_count, and jokers_used
- **THEN** users share the same rank
- **AND** next rank number accounts for tied users

### Requirement: Rank numbering

The system SHALL number ranks correctly with ties.

#### Scenario: Sequential ranks without ties
- **WHEN** no users share ranks
- **THEN** ranks are 1, 2, 3, 4...

#### Scenario: Shared ranks skip numbers
- **WHEN** two users share rank 2
- **THEN** ranks are 1, 2, 2, 4... (3 is skipped)

### Requirement: User statistics tracking

The system SHALL track cumulative statistics for ranking.

#### Scenario: Total points aggregation
- **WHEN** predictions are scored
- **THEN** User.total_points is sum of all points_earned

#### Scenario: Exact match count tracking
- **WHEN** prediction with is_exact_match=True is scored
- **THEN** User.exact_match_count is incremented

#### Scenario: Jokers used count
- **WHEN** counting jokers for tiebreaker
- **THEN** count includes only scored predictions with joker_active=True

### Requirement: Statistics reset

The system SHALL support resetting user statistics.

#### Scenario: Reset for recalculation
- **WHEN** recalculation starts
- **THEN** all user statistics are set to 0
- **AND** statistics are rebuilt from scored predictions

### Requirement: Leaderboard ordering

The system SHALL order leaderboard entries correctly.

#### Scenario: Database sorting
- **WHEN** generating leaderboard
- **THEN** database query uses ORDER BY total_points DESC, exact_match_count DESC, jokers_used DESC

#### Scenario: Consistent ordering
- **WHEN** leaderboard is generated multiple times
- **THEN** ordering is stable for identical statistics
