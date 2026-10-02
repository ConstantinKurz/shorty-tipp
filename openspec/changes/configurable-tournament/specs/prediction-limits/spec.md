## ADDED Requirements

### Requirement: Per-round prediction limit

The system SHALL limit how many matches of a round a participant may predict, using the limit
configured on that round.

This replaces the hardcoded `GROUP_STAGE_LIMIT = 36` and the group-stage special case that went with
it. The group stage stops being a special kind of round and becomes a round that has a limit.

#### Scenario: Limit enforced

- **WHEN** a round has `prediction_limit = 10` and a participant already has 10 predictions in it
- **THEN** an eleventh prediction in that round is rejected
- **AND** the rejection message names the limit

#### Scenario: No limit configured

- **WHEN** a round has no `prediction_limit`
- **THEN** a participant may predict every match of that round

#### Scenario: Limits are independent per round

- **WHEN** a participant reaches the limit in one round
- **THEN** predictions in other rounds remain possible

#### Scenario: Limit displayed in prediction statistics

- **WHEN** prediction statistics are shown for a round with a limit
- **THEN** the limit is displayed as the total
- **WHEN** the round has no limit
- **THEN** the number of matches in the round is displayed as the total

#### Scenario: Deleting a prediction frees capacity

- **WHEN** a participant at the limit deletes a prediction in that round
- **THEN** a new prediction in that round is accepted

### Requirement: Per-round joker limit

The system SHALL limit how many jokers a participant may set in a round, using the joker count
configured on that round.

This replaces the hardcoded `JOKER_LIMITS` dictionary.

#### Scenario: Joker limit enforced

- **WHEN** a round has `joker_count = 3` and a participant already has 3 jokers in it
- **THEN** a fourth joker in that round is rejected

#### Scenario: Round without jokers

- **WHEN** a round has `joker_count = 0`
- **THEN** no joker can be set on any of its matches

#### Scenario: Joker limit changed by an administrator

- **WHEN** a round's `joker_count` is raised
- **THEN** participants may immediately set additional jokers in that round

### Requirement: Shared joker pools

The system SHALL count jokers against a shared pool when several rounds are configured with the same
joker pool.

This replaces the hardcoded `COMBINED_ROUNDS = {"sf", "final", "3rd"}` set.

#### Scenario: Jokers counted across the pool

- **WHEN** the semi-final, third-place and final rounds share a pool with `joker_count = 2` and a
  participant has set 2 jokers across any of them
- **THEN** a further joker in any round of that pool is rejected

#### Scenario: Pool without a third-place round

- **WHEN** a tournament has no third-place round and its semi-final and final share a pool
- **THEN** the shared limit is enforced across those two rounds
- **AND** no configuration change is required

#### Scenario: Round outside any pool

- **WHEN** a round has a blank joker pool
- **THEN** its jokers count only against its own limit

### Requirement: Configured prediction lock

The system SHALL lock predictions for a match a configured number of minutes before kickoff.

This replaces the hardcoded `LOCK_BUFFER_MINUTES = 3`.

#### Scenario: Lock buffer read from the tournament

- **WHEN** the tournament has `lock_buffer_minutes = 5` and the current time is 4 minutes before
  kickoff
- **THEN** the match is locked
- **AND** predictions for it are rejected

#### Scenario: Before the lock

- **WHEN** the current time is earlier than kickoff minus the configured buffer
- **THEN** the match is not locked

#### Scenario: Lock is enforced server-side

- **WHEN** a prediction is submitted for a locked match
- **THEN** the server rejects it regardless of what the client sent
