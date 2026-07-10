## ADDED Requirements

### Requirement: Match prediction data model

The system SHALL provide a MatchPrediction model to store user predictions for match results.

#### Scenario: Create match prediction
- **WHEN** a user creates a prediction for a match
- **THEN** the prediction is saved with user, match, predicted goals, and joker status
- **AND** all fields are populated correctly

#### Scenario: Prediction uniqueness
- **WHEN** attempting to create a second prediction for the same user and match
- **THEN** the system raises a validation error
- **AND** the duplicate prediction is not created

#### Scenario: Default joker status
- **WHEN** creating a match prediction without specifying joker status
- **THEN** joker_active defaults to False

### Requirement: Match prediction relationships

The system SHALL establish relationships between predictions, users, and matches.

#### Scenario: Access user's predictions
- **WHEN** querying user.match_predictions
- **THEN** all match predictions for that user are returned
- **AND** they are ordered by match kickoff time

#### Scenario: Access predictions for a match
- **WHEN** querying match.predictions
- **THEN** all user predictions for that match are returned

#### Scenario: User deleted cascades predictions
- **WHEN** a user is deleted
- **THEN** all their match predictions are also deleted

#### Scenario: Match deleted cascades predictions
- **WHEN** a match is deleted
- **THEN** all predictions for that match are also deleted

### Requirement: Match prediction goals

The system SHALL store predicted goals for both teams.

#### Scenario: Set predicted goals
- **WHEN** creating a prediction with specific goal values
- **THEN** both predicted_goals_home and predicted_goals_away are saved
- **AND** both must be non-negative integers

#### Scenario: Update predicted goals
- **WHEN** updating an existing prediction
- **THEN** the new goal values replace the old values
- **AND** the updated_at timestamp is updated

### Requirement: Joker functionality

The system SHALL support joker activation on predictions.

#### Scenario: Activate joker on prediction
- **WHEN** setting joker_active to True on a prediction
- **THEN** the joker status is saved
- **AND** can be queried later

#### Scenario: Query predictions with active joker
- **WHEN** filtering predictions by joker_active=True
- **THEN** only predictions with active jokers are returned

#### Scenario: Count jokers used per round
- **WHEN** counting predictions with joker_active=True for a specific round
- **THEN** the count reflects number of jokers used in that round

### Requirement: Match prediction timestamps

The system SHALL track when predictions are created and modified.

#### Scenario: Prediction creation timestamp
- **WHEN** a prediction is created
- **THEN** created_at is automatically set to current time

#### Scenario: Prediction update timestamp
- **WHEN** a prediction is modified
- **THEN** updated_at is automatically updated to current time
- **AND** created_at remains unchanged

### Requirement: Match prediction ordering

The system SHALL order predictions by match kickoff time by default.

#### Scenario: List user predictions
- **WHEN** querying all predictions for a user without explicit ordering
- **THEN** predictions are returned ordered by match kickoff time (earliest first)

### Requirement: Match prediction admin interface

The system SHALL provide Django admin interface for prediction management.

#### Scenario: List predictions in admin
- **WHEN** accessing the predictions admin page
- **THEN** predictions are listed with user, match, predicted scores, and joker status

#### Scenario: Create prediction via admin
- **WHEN** an admin user creates a new prediction
- **THEN** user and match can be selected via dropdown
- **AND** predicted goals can be entered
- **AND** joker can be toggled

#### Scenario: Filter predictions by user
- **WHEN** filtering predictions in admin by user
- **THEN** only that user's predictions are shown

#### Scenario: Filter predictions by joker status
- **WHEN** filtering predictions by joker_active
- **THEN** only predictions matching the joker status are shown

### Requirement: Match prediction string representation

The system SHALL display prediction details in readable format.

#### Scenario: Prediction display format
- **WHEN** viewing a prediction in admin or shell
- **THEN** format shows "User: Match (predicted score)" or similar readable representation
