## ADDED Requirements

### Requirement: Match prediction points tracking

The system SHALL track points earned for each match prediction.

#### Scenario: Points field is nullable
- **WHEN** a prediction is created for an upcoming match
- **THEN** points_earned is NULL
- **AND** the prediction can be saved successfully

#### Scenario: Points calculated after match result
- **WHEN** a match result is entered and scoring is calculated
- **THEN** points_earned is set to the calculated integer value
- **AND** the value is based on prediction accuracy

#### Scenario: Zero points for incorrect prediction
- **WHEN** a prediction does not match the result in any way
- **THEN** points_earned is set to 0
- **AND** is distinguishable from NULL (not yet scored)

#### Scenario: Query predictions by points
- **WHEN** filtering predictions by points_earned value
- **THEN** only predictions with that exact points value are returned

#### Scenario: Query scored vs unscored predictions
- **WHEN** filtering by points_earned__isnull=False
- **THEN** only predictions that have been scored are returned
- **AND** predictions for unfinished matches are excluded

#### Scenario: Aggregate total points for user
- **WHEN** summing points_earned for a user's predictions
- **THEN** the total includes all scored predictions
- **AND** NULL values are treated as 0 in the aggregation

### Requirement: Exact match identification

The system SHALL identify predictions with exact score matches (Sechser).

#### Scenario: Exact match field is nullable
- **WHEN** a prediction is created for an upcoming match
- **THEN** is_exact_match is NULL
- **AND** the prediction can be saved successfully

#### Scenario: Exact match detected
- **WHEN** a prediction exactly matches the final score
- **THEN** is_exact_match is set to True
- **AND** points_earned reflects the exact match bonus

#### Scenario: Non-exact match
- **WHEN** a prediction matches the result but not the exact score
- **THEN** is_exact_match is set to False
- **AND** points_earned reflects partial points

#### Scenario: Incorrect prediction not exact
- **WHEN** a prediction does not match the result
- **THEN** is_exact_match is set to False
- **AND** points_earned is 0

#### Scenario: Filter exact match predictions
- **WHEN** filtering predictions by is_exact_match=True
- **THEN** only predictions with perfect score matches are returned

#### Scenario: Count exact matches for user
- **WHEN** counting is_exact_match=True for a user
- **THEN** the count shows total number of Sechser for that user

#### Scenario: Leaderboard by exact matches
- **WHEN** ordering users by count of exact matches
- **THEN** users with most Sechser are ranked higher

### Requirement: Scoring fields admin display

The system SHALL display scoring information in the admin interface.

#### Scenario: View points in admin list
- **WHEN** viewing predictions in admin list view
- **THEN** points_earned is displayed for each prediction
- **AND** NULL values are clearly indicated

#### Scenario: View exact match indicator in admin
- **WHEN** viewing predictions in admin list view
- **THEN** is_exact_match status is displayed
- **AND** TRUE values are clearly highlighted

#### Scenario: Filter by exact match in admin
- **WHEN** applying is_exact_match filter in admin
- **THEN** predictions can be filtered to show only Sechser

#### Scenario: Scoring fields are read-only
- **WHEN** editing a prediction in admin
- **THEN** points_earned and is_exact_match are shown but not editable
- **AND** only the scoring service can modify these fields

### Requirement: Scoring field constraints

The system SHALL enforce data integrity for scoring fields.

#### Scenario: Points must be non-negative
- **WHEN** setting points_earned to a negative value
- **THEN** the system raises a validation error
- **AND** the value is not saved

#### Scenario: Exact match requires points
- **WHEN** is_exact_match is True
- **THEN** points_earned must be greater than 0
- **AND** reflects the exact match scoring rules

#### Scenario: Unscored prediction consistency
- **WHEN** a prediction has not been scored
- **THEN** both points_earned and is_exact_match are NULL
- **AND** they are set together when scoring occurs
