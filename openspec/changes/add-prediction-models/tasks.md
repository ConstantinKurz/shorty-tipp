## 1. Update User Model

- [x] 1.1 Add predicted_champion ForeignKey field to User model in users/models.py
- [x] 1.2 Set ForeignKey to 'matches.Team' with on_delete=SET_NULL
- [x] 1.3 Add null=True, blank=True to make field optional
- [x] 1.4 Add related_name='champion_predictions'
- [x] 1.5 Add help text explaining the field
- [x] 1.6 Add type annotation for the field

## 2. Create MatchPrediction Model

- [x] 2.1 Create MatchPrediction model in predictions/models.py
- [x] 2.2 Add user ForeignKey with on_delete=CASCADE and related_name='match_predictions'
- [x] 2.3 Add match ForeignKey with on_delete=CASCADE and related_name='predictions'
- [x] 2.4 Add predicted_goals_home IntegerField
- [x] 2.5 Add predicted_goals_away IntegerField
- [x] 2.6 Add joker_active BooleanField with default=False
- [x] 2.7 Add created_at DateTimeField with auto_now_add=True
- [x] 2.8 Add updated_at DateTimeField with auto_now=True
- [x] 2.9 Add Meta class with unique_together=['user', 'match']
- [x] 2.10 Add Meta ordering by 'match__kickoff'
- [x] 2.11 Add db_table specification
- [x] 2.12 Implement __str__ method showing user and match
- [x] 2.13 Add type annotations for all fields

## 3. Database Migrations

- [x] 3.1 Generate migration for User model changes
- [x] 3.2 Generate migration for MatchPrediction model
- [x] 3.3 Review generated migration files
- [x] 3.4 Run migrations on development database
- [x] 3.5 Verify database schema updated correctly

## 4. Admin Interface for User

- [x] 4.1 Update UserAdmin in users/admin.py to show predicted_champion
- [x] 4.2 Add predicted_champion to list_display (optional - might clutter)
- [x] 4.3 Add predicted_champion to fields/fieldsets for detail view
- [x] 4.4 Verify admin interface displays correctly

## 5. Admin Interface for MatchPrediction

- [x] 5.1 Register MatchPrediction model in predictions/admin.py
- [x] 5.2 Configure MatchPredictionAdmin with list_display (user, match, scores, joker, created_at)
- [x] 5.3 Add list_filter for joker_active and user
- [x] 5.4 Add search_fields for user__username and match details
- [x] 5.5 Add date_hierarchy for created_at
- [x] 5.6 Configure readonly_fields for created_at and updated_at
- [x] 5.7 Add custom display methods if needed (e.g., predicted_score)
- [x] 5.8 Verify admin interface works correctly

## 6. Tests for User Model Changes

- [x] 6.1 Update existing user tests if needed
- [x] 6.2 Add test for user with predicted_champion set
- [x] 6.3 Add test for user without predicted_champion (NULL)
- [x] 6.4 Add test for relationship: team.champion_predictions.all()
- [x] 6.5 Add test for cascade behavior (team deleted sets NULL)

## 7. Tests for MatchPrediction Model

- [x] 7.1 Create test file for MatchPrediction (predictions/tests.py)
- [x] 7.2 Create fixtures for users, teams, and matches
- [x] 7.3 Test MatchPrediction creation with all required fields
- [x] 7.4 Test unique_together constraint (user + match)
- [x] 7.5 Test __str__ representation
- [x] 7.6 Test ordering by match kickoff
- [x] 7.7 Test relationship: user.match_predictions.all()
- [x] 7.8 Test relationship: match.predictions.all()
- [x] 7.9 Test joker_active default value (False)
- [x] 7.10 Test joker_active can be set to True
- [x] 7.11 Test created_at timestamp is set automatically
- [x] 7.12 Test updated_at timestamp updates on save
- [x] 7.13 Test cascade: user deleted removes predictions
- [x] 7.14 Test cascade: match deleted removes predictions

## 8. Verification

- [x] 8.1 Run all tests and verify they pass
- [x] 8.2 Run ruff check and fix any linting issues
- [x] 8.3 Run mypy and fix any type errors
- [x] 8.4 Create sample users with champion predictions via shell
- [x] 8.5 Create sample match predictions via admin
- [x] 8.6 Verify unique constraint prevents duplicates
- [x] 8.7 Verify joker filtering works in admin
- [x] 8.8 Verify relationships work (user.match_predictions, match.predictions)
- [x] 8.9 Verify timestamps are set correctly
