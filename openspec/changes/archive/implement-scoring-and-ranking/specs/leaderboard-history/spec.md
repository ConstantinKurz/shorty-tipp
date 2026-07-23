## ADDED Requirements

### Requirement: Leaderboard snapshot model

The system SHALL provide a model to store historical leaderboard snapshots.

#### Scenario: Create snapshot
- **WHEN** snapshot is created
- **THEN** current leaderboard data is saved with timestamp

#### Scenario: Snapshot includes full rankings
- **WHEN** snapshot is saved
- **THEN** data includes rank, user_id, username, total_points, exact_match_count, jokers_used for all users

#### Scenario: Snapshot type classification
- **WHEN** snapshot is created
- **THEN** snapshot_type is set to daily, weekly, or final

### Requirement: Snapshot immutability

The system SHALL preserve historical snapshots unchanged.

#### Scenario: Snapshots not affected by user deletion
- **WHEN** user is deleted
- **THEN** historical snapshots containing that user remain unchanged

#### Scenario: Snapshots not affected by rescoring
- **WHEN** predictions are recalculated
- **THEN** historical snapshots remain unchanged
- **AND** new snapshot can be created with updated rankings

### Requirement: Snapshot creation command

The system SHALL provide command to create snapshots manually.

#### Scenario: Manual snapshot creation
- **WHEN** create_snapshot command is run
- **THEN** current leaderboard is saved as new snapshot

#### Scenario: Specify snapshot type
- **WHEN** creating snapshot with type parameter
- **THEN** snapshot_type is set to specified value

### Requirement: Snapshot querying

The system SHALL allow querying historical snapshots.

#### Scenario: Get all snapshots
- **WHEN** querying all snapshots
- **THEN** snapshots are returned ordered by created_at descending

#### Scenario: Get snapshots by type
- **WHEN** filtering by snapshot_type
- **THEN** only snapshots of that type are returned

#### Scenario: Get snapshot at date
- **WHEN** querying snapshot nearest to specific date
- **THEN** closest snapshot before or on that date is returned

### Requirement: Snapshot data structure

The system SHALL store snapshot data as JSON.

#### Scenario: JSON field contains rankings array
- **WHEN** snapshot is created
- **THEN** data field contains array of ranking dictionaries

#### Scenario: Each ranking entry complete
- **WHEN** snapshot data is accessed
- **THEN** each entry has rank, user_id, username, total_points, exact_match_count, jokers_used

### Requirement: Snapshot admin interface

The system SHALL provide admin interface for snapshots.

#### Scenario: List snapshots in admin
- **WHEN** accessing snapshots admin
- **THEN** snapshots are listed with created_at and snapshot_type

#### Scenario: View snapshot details
- **WHEN** viewing snapshot in admin
- **THEN** formatted leaderboard data is displayed

#### Scenario: Create snapshot via admin
- **WHEN** admin triggers create snapshot action
- **THEN** new snapshot is created with current rankings
