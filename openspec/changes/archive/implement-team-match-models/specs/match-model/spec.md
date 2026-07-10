## ADDED Requirements

### Requirement: Match data model

The system SHALL provide a Match model to represent games between two teams in the World Cup 2026 tournament.

#### Scenario: Create match with teams and metadata
- **WHEN** a match is created with home team, away team, kickoff time, and round
- **THEN** the match is saved to the database
- **AND** all required fields are populated

#### Scenario: Match relationships to teams
- **WHEN** querying a match
- **THEN** both team_home and team_away return Team instances
- **AND** related names allow reverse queries from Team

#### Scenario: Scheduled match without result
- **WHEN** creating a match without goals
- **THEN** goals_home and goals_away are NULL
- **AND** status is 'scheduled'

### Requirement: Match result recording

The system SHALL allow recording match results with goals scored by each team.

#### Scenario: Record match result
- **WHEN** updating a match with final goals
- **THEN** goals_home and goals_away are saved
- **AND** status can be set to 'finished'

#### Scenario: Update match during game
- **WHEN** setting status to 'live'
- **THEN** the match shows as in-progress
- **AND** scores can be updated

### Requirement: Tournament round classification

The system SHALL categorize each match by tournament round.

#### Scenario: Group stage match
- **WHEN** creating a match with round='group'
- **THEN** the match is identified as group stage

#### Scenario: Knockout round match
- **WHEN** creating a match with round from knockout stages
- **THEN** valid rounds are r32, r16, qf, sf, 3rd, final

#### Scenario: Invalid round rejected
- **WHEN** attempting to set an invalid round value
- **THEN** the system raises a validation error

### Requirement: Match string representation

The system SHALL display match details in readable format.

#### Scenario: Match display format
- **WHEN** viewing a match in admin or shell
- **THEN** format shows "TeamA vs TeamB (Round)" or "TeamA X-Y TeamB" if finished

### Requirement: Match admin interface

The system SHALL provide Django admin interface for match management.

#### Scenario: List matches in admin
- **WHEN** accessing the matches admin page
- **THEN** matches are listed with teams, date, round, and status

#### Scenario: Create match via admin
- **WHEN** an admin user creates a new match
- **THEN** both teams can be selected via dropdown
- **AND** kickoff datetime can be set
- **AND** round can be chosen from valid options

#### Scenario: Enter match result via admin
- **WHEN** an admin user updates a finished match
- **THEN** goals for both teams can be entered
- **AND** status can be set to 'finished'

### Requirement: Match validation

The system SHALL validate match data integrity.

#### Scenario: Team differentiation
- **WHEN** creating a match
- **THEN** team_home and team_away can be different teams
- **AND** (optional) validation can prevent team_home == team_away

#### Scenario: Score validation
- **WHEN** setting match scores
- **THEN** goals must be non-negative integers if provided

### Requirement: Match ordering

The system SHALL order matches by kickoff time by default.

#### Scenario: Match list chronological order
- **WHEN** querying all matches without explicit ordering
- **THEN** matches are returned ordered by kickoff datetime (earliest first)

### Requirement: Match querysets

The system SHALL support filtering matches by various criteria.

#### Scenario: Filter by round
- **WHEN** querying matches with round='group'
- **THEN** only group stage matches are returned

#### Scenario: Filter by team
- **WHEN** querying matches involving a specific team
- **THEN** matches where team is home OR away are returned

#### Scenario: Filter by status
- **WHEN** querying finished matches
- **THEN** only matches with status='finished' are returned
