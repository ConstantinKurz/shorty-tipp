## 1. Team Model Implementation

- [x] 1.1 Create Team model in matches/models.py with name, fifa_code, and group fields
- [x] 1.2 Add Meta class with ordering by name and db_table specification
- [x] 1.3 Implement __str__ method to return team name
- [x] 1.4 Add GROUP_CHOICES for groups A-H
- [x] 1.5 Set fifa_code as unique field

## 2. Match Model Implementation

- [x] 2.1 Create Match model in matches/models.py with ForeignKeys to Team
- [x] 2.2 Add team_home with related_name='home_matches'
- [x] 2.3 Add team_away with related_name='away_matches'
- [x] 2.4 Add kickoff DateTimeField
- [x] 2.5 Add round CharField with ROUND_CHOICES (group, r32, r16, qf, sf, 3rd, final)
- [x] 2.6 Add nullable goals_home and goals_away IntegerFields
- [x] 2.7 Add status CharField with choices (scheduled, live, finished)
- [x] 2.8 Add Meta class with ordering by kickoff datetime
- [x] 2.9 Implement __str__ method showing teams and score/round

## 3. Database Migrations

- [x] 3.1 Generate migrations for Team and Match models
- [x] 3.2 Review generated migration file
- [x] 3.3 Run migrations on development database
- [x] 3.4 Verify tables created correctly in database

## 4. Admin Interface

- [x] 4.1 Register Team model in matches/admin.py
- [x] 4.2 Configure TeamAdmin with list_display (name, fifa_code, group)
- [x] 4.3 Add search_fields for team name
- [x] 4.4 Add list_filter for group
- [x] 4.5 Register Match model in matches/admin.py
- [x] 4.6 Configure MatchAdmin with list_display (teams, kickoff, round, status)
- [x] 4.7 Add list_filter for round and status
- [x] 4.8 Add search capability for team names
- [x] 4.9 Configure date_hierarchy for kickoff field

## 5. Model Tests

- [x] 5.1 Create test file for Team model (matches/tests.py or tests/test_team.py)
- [x] 5.2 Test Team creation with all required fields
- [x] 5.3 Test Team __str__ returns name
- [x] 5.4 Test fifa_code uniqueness constraint
- [x] 5.5 Test Team ordering by name
- [x] 5.6 Create test file for Match model
- [x] 5.7 Test Match creation with teams and metadata
- [x] 5.8 Test Match __str__ representation
- [x] 5.9 Test Match ordering by kickoff
- [x] 5.10 Test relationship: team.home_matches returns correct matches
- [x] 5.11 Test relationship: team.away_matches returns correct matches
- [x] 5.12 Test Match with NULL goals (scheduled match)
- [x] 5.13 Test Match with goals set (finished match)

## 6. Verification

- [x] 6.1 Run all tests and verify they pass
- [x] 6.2 Run ruff check and fix any linting issues
- [x] 6.3 Run mypy and fix any type errors
- [x] 6.4 Manually create sample teams via admin
- [x] 6.5 Manually create sample matches via admin
- [x] 6.6 Verify admin interfaces work correctly
- [x] 6.7 Verify relationships work (query team matches)
