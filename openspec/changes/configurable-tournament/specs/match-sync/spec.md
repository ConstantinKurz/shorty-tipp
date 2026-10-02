## ADDED Requirements

### Requirement: Competition code from the tournament

The system SHALL fetch teams and matches for the competition configured on the tournament rather
than for a hardcoded default.

Previously `FootballDataClient.get_teams()` and `get_matches()` defaulted to `competition="WC"`, and
the `sync_teams` command exposed a `--competition` option.

#### Scenario: Sync uses the active tournament

- **WHEN** a sync command is run with no arguments
- **THEN** the competition code of the active tournament is used

#### Scenario: Sync targets a named tournament

- **WHEN** a sync command is run with a tournament slug
- **THEN** that tournament's competition code is used

#### Scenario: No tournament configured

- **WHEN** a sync command is run and no tournament is active
- **THEN** the command fails with a message naming the missing configuration
- **AND** no API request is made

### Requirement: Stage mapping from round configuration

The system SHALL map an API stage name to a round using the `api_stage` value configured on the
tournament's rounds.

This replaces the hardcoded `API_ROUND_MAP` dictionary.

#### Scenario: Known stage mapped to its round

- **WHEN** a match payload carries a stage that matches a round's `api_stage`
- **THEN** the match is assigned that round

#### Scenario: Unknown stage rejected

- **WHEN** a match payload carries a stage that no round declares
- **THEN** the sync raises an error naming the unrecognised stage and the configured stages
- **AND** no match is created or updated for that payload

#### Scenario: No silent fallback

- **WHEN** a stage cannot be resolved
- **THEN** the match is never assigned the group stage as a default

#### Scenario: Stage names differ per tournament

- **WHEN** a tournament configures different `api_stage` values than another tournament
- **THEN** each tournament's sync uses its own mapping

### Requirement: Sync command options

The system SHALL expose a tournament selector on the synchronisation commands.

#### Scenario: Tournament option available

- **WHEN** `sync_teams` or `update_matches` is run with a tournament slug option
- **THEN** the named tournament is used

#### Scenario: Default without options

- **WHEN** the option is omitted
- **THEN** the active tournament is used

#### Scenario: Unknown slug

- **WHEN** a slug is given that no tournament has
- **THEN** the command fails with a readable error
- **AND** no API request is made

### Requirement: API client behaviour preserved

The system SHALL keep the existing retry, rate-limit and backoff behaviour of the API client
unchanged.

#### Scenario: Rate limit response

- **WHEN** the API responds with status 429
- **THEN** the client waits for the duration in the `Retry-After` header and retries

#### Scenario: Server error

- **WHEN** the API responds with a 5xx status
- **THEN** the client retries with exponential backoff up to the configured maximum

#### Scenario: Client error

- **WHEN** the API responds with a 4xx status other than 429
- **THEN** the client raises without retrying
