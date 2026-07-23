## ADDED Requirements

### Requirement: User statistics fields

The system SHALL track cumulative statistics on User model.

#### Scenario: Total points field
- **WHEN** user is created
- **THEN** total_points defaults to 0

#### Scenario: Exact match count field
- **WHEN** user is created
- **THEN** exact_match_count defaults to 0

#### Scenario: Jokers used field
- **WHEN** user is created
- **THEN** jokers_used defaults to 0

### Requirement: Statistics updates on scoring

The system SHALL update user statistics when predictions are scored.

#### Scenario: Add points to total
- **WHEN** prediction is scored with points_earned
- **THEN** User.total_points increases by points_earned

#### Scenario: Increment exact match count
- **WHEN** prediction is scored with is_exact_match=True
- **THEN** User.exact_match_count increments by 1

#### Scenario: Increment jokers used
- **WHEN** prediction with joker_active=True is scored
- **THEN** User.jokers_used increments by 1

### Requirement: Statistics reset

The system SHALL support resetting user statistics.

#### Scenario: Reset statistics for recalculation
- **WHEN** recalculation starts
- **THEN** all users' total_points set to 0
- **AND** all users' exact_match_count set to 0
- **AND** all users' jokers_used set to 0

#### Scenario: Rebuild from predictions
- **WHEN** statistics are reset and recalculated
- **THEN** statistics match sum of all scored predictions

### Requirement: Statistics display in admin

The system SHALL display user statistics in admin interface.

#### Scenario: View statistics in user list
- **WHEN** viewing users in admin
- **THEN** total_points, exact_match_count, and jokers_used are displayed

#### Scenario: Filter by statistics
- **WHEN** admin filters users
- **THEN** can filter by ranges of total_points or exact_match_count

#### Scenario: Sort by statistics
- **WHEN** viewing users in admin
- **THEN** can sort by total_points, exact_match_count, or jokers_used

### Requirement: Statistics accuracy

The system SHALL maintain accurate statistics.

#### Scenario: Statistics match predictions
- **WHEN** querying user statistics
- **THEN** total_points equals sum of user's match_predictions.points_earned
- **AND** exact_match_count equals count of user's match_predictions with is_exact_match=True

#### Scenario: Atomic updates
- **WHEN** prediction is scored
- **THEN** prediction fields and user statistics are updated atomically

### Requirement: Champion points in total

The system SHALL include champion prediction points in total_points.

#### Scenario: Add champion points to total
- **WHEN** champion prediction is scored
- **THEN** User.total_points includes champion points

#### Scenario: Champion points distinguishable
- **WHEN** querying user points breakdown
- **THEN** can separate match prediction points from champion points
