## ADDED Requirements

### Requirement: Team data model

The system SHALL provide a Team model to represent countries participating in the World Cup 2026 tournament.

#### Scenario: Create team with required fields
- **WHEN** a team is created with name, FIFA code, and group
- **THEN** the team is saved to the database
- **AND** all fields are populated correctly

#### Scenario: FIFA code uniqueness
- **WHEN** attempting to create a team with a duplicate FIFA code
- **THEN** the system raises a validation error
- **AND** the team is not created

#### Scenario: Group validation
- **WHEN** creating a team with a group assignment
- **THEN** the group must be one of A, B, C, D, E, F, G, or H
- **AND** invalid group values are rejected

### Requirement: Team string representation

The system SHALL display team name as the string representation.

#### Scenario: Team display in admin
- **WHEN** viewing teams in Django admin or shell
- **THEN** the team name is shown (not object ID)

### Requirement: Team relationship to matches

The system SHALL allow querying matches where a team plays.

#### Scenario: Query home matches
- **WHEN** accessing team.home_matches
- **THEN** all matches where the team plays at home are returned

#### Scenario: Query away matches
- **WHEN** accessing team.away_matches
- **THEN** all matches where the team plays away are returned

### Requirement: Team admin interface

The system SHALL provide Django admin interface for team management.

#### Scenario: List teams in admin
- **WHEN** accessing the teams admin page
- **THEN** teams are listed with name, FIFA code, and group

#### Scenario: Create team via admin
- **WHEN** an admin user creates a new team
- **THEN** the team is added to the database
- **AND** appears in the team list

#### Scenario: Edit team via admin
- **WHEN** an admin user updates team details
- **THEN** changes are saved
- **AND** updated values are displayed

### Requirement: Team ordering

The system SHALL order teams alphabetically by name by default.

#### Scenario: Team list ordering
- **WHEN** querying all teams without explicit ordering
- **THEN** teams are returned in alphabetical order by name
