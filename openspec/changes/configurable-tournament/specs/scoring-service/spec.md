## MODIFIED Requirements

### Requirement: Round multipliers

The system SHALL multiply base prediction points by the multiplier configured on the match's round.

Previously the multiplier came from a hardcoded `ScoringService.ROUND_MULTIPLIERS` dictionary with
seven fixed entries.

#### Scenario: Multiplier read from configuration

- **WHEN** a prediction is scored for a match whose round has `multiplier = 5`
- **THEN** the base points are multiplied by 5

#### Scenario: Changing a multiplier

- **WHEN** an administrator changes a round's multiplier and recalculates scores
- **THEN** all predictions in that round are rescored with the new value
- **AND** predictions in other rounds are unchanged

#### Scenario: Unknown round is impossible

- **WHEN** a prediction is scored
- **THEN** the multiplier is resolved through the match's round relation
- **AND** no round-code lookup can fail

### Requirement: Joker point multiplier

The system SHALL multiply a joker prediction's points by the joker multiplier configured on the
match's round.

Previously the joker doubled points through a hardcoded factor of 2.

#### Scenario: Joker multiplier read from configuration

- **WHEN** a joker prediction is scored in a round with `joker_multiplier = 3`
- **THEN** the points are `base × round multiplier × 3`

#### Scenario: Joker multiplier applies after the round multiplier

- **WHEN** a joker prediction is scored
- **THEN** the round multiplier is applied first
- **AND** the joker multiplier is applied to the result

#### Scenario: No joker set

- **WHEN** a prediction without an active joker is scored
- **THEN** the joker multiplier is not applied

### Requirement: Champion prediction bonus

The system SHALL award the champion bonus stored on the winning team.

Previously the bonus was looked up from a hardcoded map keyed by the team's odds category.

#### Scenario: Bonus taken from the team

- **WHEN** the tournament winner is determined and a user predicted that team
- **THEN** the user receives the winning team's `champion_points`

#### Scenario: Team without a configured bonus

- **WHEN** the winning team has `champion_points` equal to 0
- **THEN** no bonus is awarded
- **AND** no error is raised

### Requirement: Final match identification

The system SHALL identify the final through the `is_final` flag on the round.

Previously the final was located with `Match.objects.filter(round="final")`, a literal string
comparison in three modules.

#### Scenario: Locating the final

- **WHEN** the champion is determined
- **THEN** the final is the match whose round has `is_final = True`

#### Scenario: Tournament with the third-place match ordered last

- **WHEN** a tournament orders its third-place round after the final
- **THEN** the final is still identified correctly by the flag

#### Scenario: Result entered for the final

- **WHEN** a result is entered for a match whose round is the final
- **THEN** champion bonuses are recalculated

### Requirement: Round-filtered leaderboard

The system SHALL calculate leaderboards up to and including a selected round using the configured
round order.

Previously the cutoff was computed from the index of a round code in a hardcoded `ROUND_ORDER` list.

#### Scenario: Leaderboard up to a round

- **WHEN** a leaderboard is requested up to a given round
- **THEN** it includes predictions for all rounds whose `order` is less than or equal to that
  round's `order`

#### Scenario: Round set follows the configuration

- **WHEN** a tournament has no round of 32
- **THEN** the round filter offers only the rounds that exist
- **AND** no empty filter option is shown

#### Scenario: Round labels come from configuration

- **WHEN** a round label is rendered anywhere in the application
- **THEN** it is `Round.label`
- **AND** a 48-team World Cup's round of 32 is labelled "Sechzehntelfinale"
