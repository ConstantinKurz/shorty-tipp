## ADDED Requirements

### Requirement: Match prediction point calculation

The system SHALL calculate points for match predictions according to WM 2026 scoring rules.

#### Scenario: Exact score match
- **WHEN** predicted score exactly matches actual result
- **THEN** 6 base points are awarded
- **AND** is_exact_match is set to True

#### Scenario: Correct tendency and goal difference
- **WHEN** tendency is correct AND goal difference is correct AND exact score does not match
- **THEN** 5 base points are awarded

#### Scenario: Correct tendency and one team goals
- **WHEN** tendency is correct AND at least one team's goals are correct AND exact score does not match AND goal difference does not match
- **THEN** 4 base points are awarded

#### Scenario: Correct tendency only
- **WHEN** tendency is correct AND no higher category applies
- **THEN** 3 base points are awarded

#### Scenario: Correct goals for one team only
- **WHEN** tendency is incorrect AND at least one team's goals are correct
- **THEN** 1 base point is awarded

#### Scenario: No match
- **WHEN** none of the above conditions apply
- **THEN** 0 points are awarded

### Requirement: Scoring category precedence

The system SHALL evaluate scoring categories in strict precedence order.

#### Scenario: Only highest category applies
- **WHEN** multiple categories could apply
- **THEN** only the highest precedence category's points are awarded
- **AND** lower category points are not added

#### Scenario: Evaluation order
- **WHEN** scoring a prediction
- **THEN** categories are evaluated in order: exact → tendency+diff → tendency+one_goal → tendency → one_goal → none
- **AND** evaluation stops at first match

### Requirement: Round multiplier application

The system SHALL apply round multipliers to base points.

#### Scenario: Group stage multiplier
- **WHEN** match is in group stage
- **THEN** base points are multiplied by 1

#### Scenario: Round of 32 and 16 multiplier
- **WHEN** match is in round of 32 or round of 16
- **THEN** base points are multiplied by 2

#### Scenario: Knockout rounds multiplier
- **WHEN** match is in quarter-final, semi-final, third place, or final
- **THEN** base points are multiplied by 3

### Requirement: Joker multiplier application

The system SHALL double points when joker is active.

#### Scenario: Joker doubles after round multiplier
- **WHEN** joker_active is True
- **THEN** final points are (base_points * round_multiplier * 2)

#### Scenario: No joker applied
- **WHEN** joker_active is False
- **THEN** final points are (base_points * round_multiplier)

### Requirement: Champion prediction scoring

The system SHALL calculate points for champion predictions.

#### Scenario: Correct category A champion
- **WHEN** user's predicted_champion matches tournament winner AND winner is category A
- **THEN** 20 points are awarded

#### Scenario: Correct category B champion
- **WHEN** user's predicted_champion matches tournament winner AND winner is category B
- **THEN** 30 points are awarded

#### Scenario: Incorrect champion prediction
- **WHEN** user's predicted_champion does not match tournament winner
- **THEN** 0 points are awarded

#### Scenario: No champion prediction
- **WHEN** user has no predicted_champion
- **THEN** 0 points are awarded

### Requirement: Automatic scoring trigger

The system SHALL automatically calculate points when match results are entered.

#### Scenario: Score on match result entry
- **WHEN** match goals_home and goals_away are set
- **THEN** all predictions for that match are automatically scored

#### Scenario: Update on result change
- **WHEN** match result is changed after initial entry
- **THEN** all predictions for that match are re-scored with new result

### Requirement: Prediction field updates

The system SHALL update MatchPrediction fields when scoring occurs.

#### Scenario: Points earned stored
- **WHEN** prediction is scored
- **THEN** points_earned field is set to calculated final points

#### Scenario: Exact match flag stored
- **WHEN** prediction is scored
- **THEN** is_exact_match field is set based on exact score match

#### Scenario: Updated timestamp changes
- **WHEN** prediction scoring fields are updated
- **THEN** updated_at timestamp reflects scoring time

### Requirement: Bulk scoring for match

The system SHALL score all predictions for a match efficiently.

#### Scenario: Batch scoring
- **WHEN** scoring all predictions for a match
- **THEN** all user predictions are scored in single operation
- **AND** database updates are batched

#### Scenario: Return count of scored predictions
- **WHEN** batch scoring completes
- **THEN** number of scored predictions is returned

### Requirement: Manual recalculation

The system SHALL support manual recalculation of all scores.

#### Scenario: Recalculate all predictions
- **WHEN** recalculation command is run
- **THEN** all prediction points are cleared
- **AND** all finished matches are re-scored
- **AND** user statistics are recalculated

#### Scenario: Idempotent recalculation
- **WHEN** recalculation is run multiple times
- **THEN** final state is identical each time
