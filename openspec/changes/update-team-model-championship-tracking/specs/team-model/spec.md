## MODIFIED Requirements

### Requirement: Team data model

The system SHALL provide a Team model to represent countries participating in the World Cup 2026 tournament.

#### Scenario: Create team with required fields
- **WHEN** a team is created with name and FIFA code
- **THEN** the team is saved to the database
- **AND** all fields are populated correctly
- **AND** points defaults to 0
- **AND** is_champion defaults to False

#### Scenario: FIFA code uniqueness
- **WHEN** attempting to create a team with a duplicate FIFA code
- **THEN** the system raises a validation error
- **AND** the team is not created

### Requirement: Team admin interface

The system SHALL provide Django admin interface for team management.

#### Scenario: List teams in admin
- **WHEN** accessing the teams admin page
- **THEN** teams are listed with name, FIFA code, points, and champion status

#### Scenario: Create team via admin
- **WHEN** an admin user creates a new team
- **THEN** the team is added to the database
- **AND** appears in the team list

#### Scenario: Edit team via admin
- **WHEN** an admin user updates team details
- **THEN** changes are saved
- **AND** updated values are displayed

## ADDED Requirements

### Requirement: Team championship points

The system SHALL track championship points for each team.

#### Scenario: Create team with default points
- **WHEN** a team is created without specifying points
- **THEN** points is set to 0

#### Scenario: Set team points
- **WHEN** updating a team's points value
- **THEN** the new points value is saved
- **AND** can be queried

#### Scenario: Points can be negative
- **WHEN** setting team points to a negative value
- **THEN** the negative value is accepted
- **AND** saved correctly

### Requirement: Team champion status

The system SHALL track whether a team won the tournament.

#### Scenario: Create team with default champion status
- **WHEN** a team is created without specifying champion status
- **THEN** is_champion is set to False

#### Scenario: Mark team as champion
- **WHEN** setting a team's is_champion to True
- **THEN** the team is marked as tournament champion

#### Scenario: Filter champions
- **WHEN** querying teams with is_champion=True
- **THEN** only champion teams are returned

## REMOVED Requirements

### Requirement: Group validation

**Reason:** Tournament group assignment is not needed for the WM 2026 tipping game rules. Teams are tracked by championship points instead.

**Migration:** Remove any code referencing team.group. Use team.points for rankings and team.is_champion to identify the winner.
