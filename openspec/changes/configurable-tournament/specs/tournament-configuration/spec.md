## ADDED Requirements

### Requirement: Tournament configuration model

The system SHALL provide a Tournament model that holds tournament-wide settings and acts as the
container for all round configuration.

#### Scenario: Create a tournament

- **WHEN** a tournament is created with a name, slug, API competition code and lock buffer
- **THEN** the tournament is saved
- **AND** `api_season` may be left empty
- **AND** `lock_buffer_minutes` defaults to 3

#### Scenario: Exactly one tournament is active

- **WHEN** a second tournament is saved with `is_active=True`
- **THEN** the database rejects the write with an integrity error
- **AND** the existing active tournament is unchanged

#### Scenario: Slug uniqueness

- **WHEN** a tournament is created with a slug that already exists
- **THEN** the database rejects the write

#### Scenario: Resolving the active tournament

- **WHEN** `get_active_tournament()` is called and an active tournament exists
- **THEN** it returns that tournament

#### Scenario: No active tournament configured

- **WHEN** `get_active_tournament()` is called and no tournament has `is_active=True`
- **THEN** it raises an exception naming the missing configuration
- **AND** it does not return `None`

### Requirement: Round configuration model

The system SHALL provide a Round model that defines which rounds a tournament has and all scoring
and prediction parameters for each of them.

#### Scenario: Round belongs to exactly one tournament

- **WHEN** a round is created
- **THEN** it references exactly one tournament
- **AND** deleting the tournament deletes its rounds

#### Scenario: Round carries all per-round parameters

- **WHEN** a round is created
- **THEN** it stores `code`, `label`, `order`, `multiplier`, `joker_count`, `joker_multiplier`,
  `joker_pool`, `prediction_limit`, `is_final` and `api_stage`

#### Scenario: Round ordering

- **WHEN** the rounds of a tournament are queried
- **THEN** they are returned ordered by `order` ascending

#### Scenario: Codes are unique per tournament but reusable across tournaments

- **WHEN** two rounds in the same tournament are given the same `code`
- **THEN** the database rejects the write
- **WHEN** two rounds in different tournaments are given the same `code`
- **THEN** both are accepted

#### Scenario: Order and API stage are unique per tournament

- **WHEN** two rounds in the same tournament share an `order` value or an `api_stage` value
- **THEN** the database rejects the write

#### Scenario: Multiplier must be at least one

- **WHEN** a round is validated with `multiplier` below 1
- **THEN** validation fails

#### Scenario: Prediction limit is optional

- **WHEN** a round is created with `prediction_limit` unset
- **THEN** the value is `NULL`
- **AND** the round places no limit on how many of its matches may be predicted

### Requirement: Final round identification

The system SHALL identify the final of a tournament through an explicit flag rather than a round
code.

#### Scenario: One final per tournament

- **WHEN** a second round in the same tournament is saved with `is_final=True`
- **THEN** the database rejects the write

#### Scenario: Missing final rejected during administration

- **WHEN** a tournament's rounds are saved with no round marked as the final
- **THEN** the admin formset rejects the save with a readable message

### Requirement: Joker pools

The system SHALL allow several rounds to draw jokers from one shared pool.

#### Scenario: Round without a pool forms its own pool

- **WHEN** a round has a blank `joker_pool`
- **THEN** its effective pool key is its `code`
- **AND** its joker limit applies to that round alone

#### Scenario: Rounds sharing a pool key share one limit

- **WHEN** several rounds carry the same non-empty `joker_pool`
- **THEN** their jokers count against one shared limit

#### Scenario: Pool members must declare the same limit

- **WHEN** rounds sharing a `joker_pool` are saved with different `joker_count` values
- **THEN** the admin formset rejects the save with a readable message

#### Scenario: Pool with a missing round still works

- **WHEN** a tournament has no third-place round and its semi-final and final share a pool
- **THEN** the shared limit is enforced across those two rounds

### Requirement: Tournament administration

The system SHALL allow an administrator to create and manage tournaments and their rounds through
the Django admin.

#### Scenario: Editing rounds inline

- **WHEN** an administrator opens a tournament change form
- **THEN** its rounds are editable inline
- **AND** rounds can be added, edited, reordered and removed

#### Scenario: Round deletion is blocked while matches reference it

- **WHEN** an administrator deletes a round that has matches
- **THEN** the deletion is refused
- **AND** the matches are unchanged

#### Scenario: Warning when configuration changes after scoring

- **WHEN** an administrator opens a tournament that already has scored predictions
- **THEN** the form displays a warning that round changes require recalculation

#### Scenario: Warning for teams without champion points

- **WHEN** teams exist with `champion_points` equal to 0
- **THEN** the tournament administration surfaces the count

#### Scenario: Recalculating scores after a configuration change

- **WHEN** an administrator runs the "Recalculate scores" action
- **THEN** all stored prediction points and user statistics are recomputed from the current
  configuration

### Requirement: Tournament presets

The system SHALL provide reusable tournament format presets so a tournament can be created without
entering every round by hand.

#### Scenario: Presets are defined in code

- **WHEN** the database is dropped and recreated
- **THEN** the presets are still available

#### Scenario: Creating from the 48-team World Cup preset

- **WHEN** a tournament is created from the `wm48` preset
- **THEN** it has seven rounds including a round of 32 and a third-place match

#### Scenario: Creating from the 24-team European Championship preset

- **WHEN** a tournament is created from the `em24` preset
- **THEN** it has five rounds
- **AND** no round of 32 exists
- **AND** no third-place round exists

#### Scenario: Creating without a preset

- **WHEN** a tournament is created with no preset
- **THEN** it has no rounds
- **AND** rounds can be added through the admin

#### Scenario: Preset values are defaults, not constraints

- **WHEN** a tournament created from a preset has its round values changed
- **THEN** the changes are saved
- **AND** nothing references the preset afterwards

### Requirement: Tournament creation through one shared code path

The system SHALL create tournaments through a single function used by the admin, the management
command and the test fixtures.

#### Scenario: Creating from the command line

- **WHEN** `manage.py create_tournament` is run with a preset, name, slug and competition code
- **THEN** the tournament and its rounds are created

#### Scenario: Creating from the admin

- **WHEN** an administrator selects a preset on the tournament add form
- **THEN** the resulting rounds are identical to those the command produces for the same preset

#### Scenario: Activating on creation

- **WHEN** a tournament is created with the activate option
- **THEN** it becomes the active tournament
- **AND** any previously active tournament is deactivated in the same transaction

#### Scenario: Creation is atomic

- **WHEN** creating a tournament fails while its rounds are being written
- **THEN** no tournament and no rounds remain
