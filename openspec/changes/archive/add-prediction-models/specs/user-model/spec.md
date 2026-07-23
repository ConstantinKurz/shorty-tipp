## ADDED Requirements

### Requirement: User champion prediction

The system SHALL allow users to predict the tournament champion.

#### Scenario: User selects champion
- **WHEN** a user selects a team as their predicted champion
- **THEN** the predicted_champion field is set to that team
- **AND** the relationship is stored in the database

#### Scenario: User has not predicted champion
- **WHEN** a user has not selected a champion prediction
- **THEN** predicted_champion is NULL
- **AND** the user can still use all other features

#### Scenario: Query users who predicted a specific team
- **WHEN** querying which users predicted a specific team as champion
- **THEN** all users with that team as predicted_champion are returned

#### Scenario: Predicted team deleted
- **WHEN** a team that is predicted as champion is deleted
- **THEN** the user's predicted_champion field is set to NULL
- **AND** the user record is not deleted

### Requirement: User prediction relationships

The system SHALL provide relationship access to user predictions.

#### Scenario: Access user's match predictions
- **WHEN** accessing user.match_predictions
- **THEN** all MatchPrediction objects for that user are returned

#### Scenario: Access users who predicted a team as champion
- **WHEN** accessing team.champion_predictions
- **THEN** all users who predicted that team as champion are returned
