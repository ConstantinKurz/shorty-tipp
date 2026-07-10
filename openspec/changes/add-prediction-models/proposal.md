## Why

The tipping game needs to track user predictions for matches and the tournament champion. Currently, we have User, Team, and Match models but no way for users to make predictions. Without prediction models, the core game functionality cannot work.

## What Changes

- Add `predicted_champion` ForeignKey field to User model pointing to Team
- Create new MatchPrediction model to track user predictions for individual matches
- Add related_name relationships for querying predictions
- Create admin interfaces for managing predictions
- Add migrations for both changes
- Implement comprehensive tests for prediction models and relationships

## Capabilities

### New Capabilities
- `match-prediction-model`: User predictions for match results with goals, joker support, and automatic constraints

### Modified Capabilities
- `user-model`: User model extended with champion prediction capability (ForeignKey to Team)

## Impact

- User model schema changes (migration required)
- New MatchPrediction model in `predictions` app
- New database tables: predictions_matchprediction
- User model gets new relationship to Team (predicted_champion)
- Admin interface extended for prediction management
- Foundation for scoring logic (predictions provide the data for points calculation)
