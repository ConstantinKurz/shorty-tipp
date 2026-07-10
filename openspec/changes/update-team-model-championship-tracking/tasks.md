## 1. Update Team Model

- [x] 1.1 Remove group field from Team model in matches/models.py
- [x] 1.2 Remove GROUP_CHOICES from Team model
- [x] 1.3 Add points IntegerField with default=0
- [x] 1.4 Add is_champion BooleanField with default=False
- [x] 1.5 Update Team model docstring if needed

## 2. Database Migration

- [x] 2.1 Generate migration for Team model changes
- [x] 2.2 Review generated migration file
- [x] 2.3 Run migration on development database
- [x] 2.4 Verify database schema updated correctly

## 3. Update Admin Interface

- [x] 3.1 Update TeamAdmin list_display to remove 'group'
- [x] 3.2 Add 'points' to TeamAdmin list_display
- [x] 3.3 Add 'is_champion' to TeamAdmin list_display
- [x] 3.4 Update list_filter to include 'is_champion' instead of 'group'
- [x] 3.5 Verify admin interface displays correctly

## 4. Update Existing Tests

- [x] 4.1 Remove group references from test_create_team_with_required_fields
- [x] 4.2 Update test to check default points=0 and is_champion=False
- [x] 4.3 Remove test_team_ordering_by_name if it references group (or update)
- [x] 4.4 Update any other tests referencing team.group

## 5. Add New Tests for Points and Champion Status

- [x] 5.1 Add test for team creation with default points
- [x] 5.2 Add test for setting team points
- [x] 5.3 Add test for negative points values
- [x] 5.4 Add test for default is_champion=False
- [x] 5.5 Add test for marking team as champion
- [x] 5.6 Add test for filtering champion teams

## 6. Verification

- [x] 6.1 Run all tests and verify they pass
- [x] 6.2 Run ruff check and fix any linting issues
- [x] 6.3 Run mypy and fix any type errors
- [x] 6.4 Create sample teams with different points via shell
- [x] 6.5 Mark one team as champion via admin
- [x] 6.6 Verify admin filtering by champion status works
- [x] 6.7 Verify team ordering still works correctly
