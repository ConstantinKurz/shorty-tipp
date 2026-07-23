## ADDED Requirements

### Requirement: CSV export

The system SHALL export leaderboard as CSV file.

#### Scenario: Export current leaderboard as CSV
- **WHEN** CSV export is requested
- **THEN** CSV file is generated with headers: Rank, Username, Total Points, Exact Matches, Jokers Used
- **AND** all leaderboard entries are included

#### Scenario: CSV download response
- **WHEN** CSV export is triggered
- **THEN** HTTP response provides downloadable CSV file
- **AND** filename includes timestamp

#### Scenario: CSV handles shared ranks
- **WHEN** users share a rank
- **THEN** rank number is repeated in CSV for tied users

### Requirement: PDF export

The system SHALL export leaderboard as PDF file.

#### Scenario: Export current leaderboard as PDF
- **WHEN** PDF export is requested
- **THEN** PDF file is generated with formatted leaderboard table

#### Scenario: PDF formatting
- **WHEN** generating PDF
- **THEN** PDF includes title, generation timestamp, and table with rank, username, points, exact matches, jokers used

#### Scenario: PDF download response
- **WHEN** PDF export is triggered
- **THEN** HTTP response provides downloadable PDF file
- **AND** filename includes timestamp

### Requirement: Export via management command

The system SHALL support exporting leaderboard via command line.

#### Scenario: Export CSV via command
- **WHEN** export_leaderboard --format csv command is run
- **THEN** CSV file is saved to specified path

#### Scenario: Export PDF via command
- **WHEN** export_leaderboard --format pdf command is run
- **THEN** PDF file is saved to specified path

#### Scenario: Default output path
- **WHEN** no output path specified
- **THEN** file is saved to current directory with timestamp in name

### Requirement: Export admin action

The system SHALL provide admin action to export leaderboard.

#### Scenario: Export from admin interface
- **WHEN** admin selects export leaderboard action
- **THEN** CSV or PDF is downloaded immediately

### Requirement: Export data consistency

The system SHALL ensure exported data matches current rankings.

#### Scenario: Export reflects current state
- **WHEN** leaderboard is exported
- **THEN** exported data matches current leaderboard query result

#### Scenario: Export includes all users
- **WHEN** leaderboard is exported
- **THEN** all users with predictions are included
- **AND** users without predictions may be excluded

### Requirement: Export formatting

The system SHALL format export data for readability.

#### Scenario: Column headers in exports
- **WHEN** generating CSV or PDF
- **THEN** column headers clearly label: Rank, Username, Total Points, Exact Matches, Jokers Used

#### Scenario: Number formatting
- **WHEN** formatting numbers in export
- **THEN** integers are displayed without decimals
- **AND** rank ties are clearly indicated
