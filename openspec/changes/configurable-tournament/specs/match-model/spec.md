## MODIFIED Requirements

### Requirement: Tournament round classification

The system SHALL classify each match by a configured round of the active tournament, rather than by a
fixed set of round codes.

Previously `Match.round` was a `CharField` constrained by a hardcoded `ROUND_CHOICES` list of seven
values. It becomes a `ForeignKey` to `Round`.

#### Scenario: Match references a configured round

- **WHEN** a match is created with a round
- **THEN** the round is a `Round` instance belonging to the configured tournament
- **AND** `match.round.label`, `match.round.multiplier` and `match.round.joker_multiplier` are
  reachable from the match

#### Scenario: Available rounds are not fixed

- **WHEN** a tournament is configured without a third-place round
- **THEN** no match can be assigned a third-place round
- **AND** every other round continues to work unchanged

#### Scenario: Round is required

- **WHEN** a match is saved without a round
- **THEN** the database rejects the write

#### Scenario: Deleting a round that has matches

- **WHEN** a round with matches is deleted
- **THEN** the deletion is refused with a protected-relation error
- **AND** the matches remain unchanged

#### Scenario: Filtering matches by round

- **WHEN** matches are filtered by round code
- **THEN** the filter traverses the relation
- **AND** the result matches what the previous string filter returned for the same code

#### Scenario: Migration of existing matches

- **WHEN** the foreign-key migration runs on a database with existing matches
- **THEN** every match is re-pointed to the round whose code equals its previous value
- **AND** the migration fails loudly if any match has a code with no matching round

### Requirement: Match string representation

The system SHALL display match details in readable format, using the configured round label.

#### Scenario: Match display format

- **WHEN** viewing a scheduled match in admin or shell
- **THEN** the format shows "TeamA vs TeamB (Round label)" using `Round.label`

#### Scenario: Finished match display format

- **WHEN** viewing a finished match with both goal values set
- **THEN** the format shows "TeamA X-Y TeamB"

### Requirement: Match admin interface

The system SHALL allow administrators to filter and select matches by their configured round.

#### Scenario: Filtering by round in the admin

- **WHEN** an administrator opens the match changelist
- **THEN** the round filter lists the configured rounds of the tournament

#### Scenario: Selecting a round for a match

- **WHEN** an administrator edits a match
- **THEN** the round field offers the configured rounds
- **AND** no round codes from other tournament formats are offered
