## 1. Update MatchPrediction Model

- [ ] 1.1 Add points_earned IntegerField to MatchPrediction model in predictions/models.py
- [ ] 1.2 Set null=True, blank=True on points_earned field
- [ ] 1.3 Add help_text explaining the points_earned field
- [ ] 1.4 Add type annotation for points_earned field
- [ ] 1.5 Add is_exact_match BooleanField to MatchPrediction model
- [ ] 1.6 Set null=True, blank=True on is_exact_match field
- [ ] 1.7 Add help_text explaining the is_exact_match field
- [ ] 1.8 Add type annotation for is_exact_match field
- [ ] 1.9 Update model docstring to mention new scoring fields

## 2. Database Migration

- [ ] 2.1 Generate migration for MatchPrediction model changes
- [ ] 2.2 Review generated migration file
- [ ] 2.3 Run migration on development database
- [ ] 2.4 Verify database schema updated correctly (two new nullable columns)

## 3. Admin Interface Updates

- [ ] 3.1 Add points_earned to MatchPredictionAdmin list_display
- [ ] 3.2 Add is_exact_match to MatchPredictionAdmin list_display
- [ ] 3.3 Add is_exact_match to list_filter
- [ ] 3.4 Add points_earned and is_exact_match to readonly_fields
- [ ] 3.5 Create custom display method for is_exact_match (highlight True values)
- [ ] 3.6 Verify admin interface displays scoring fields correctly

## 4. Update Existing Tests

- [ ] 4.1 Update test_create_match_prediction to assert new fields are NULL
- [ ] 4.2 Update test_str_representation to work with NULL scoring fields
- [ ] 4.3 Update other existing tests to handle NULL scoring fields
- [ ] 4.4 Run existing prediction tests to ensure they still pass

## 5. Add Tests for Points Tracking

- [ ] 5.1 Test points_earned defaults to NULL on creation
- [ ] 5.2 Test setting points_earned to integer value
- [ ] 5.3 Test setting points_earned to 0 (incorrect prediction)
- [ ] 5.4 Test filtering predictions by points_earned value
- [ ] 5.5 Test querying scored vs unscored predictions (NULL check)
- [ ] 5.6 Test aggregating total points for a user
- [ ] 5.7 Test points_earned is read-only in admin (if applicable)

## 6. Add Tests for Exact Match Tracking

- [ ] 6.1 Test is_exact_match defaults to NULL on creation
- [ ] 6.2 Test setting is_exact_match to True
- [ ] 6.3 Test setting is_exact_match to False
- [ ] 6.4 Test filtering predictions by is_exact_match=True
- [ ] 6.5 Test counting exact matches for a user
- [ ] 6.6 Test ordering users by count of exact matches
- [ ] 6.7 Test is_exact_match is read-only in admin (if applicable)

## 7. Add Tests for Scoring Field Consistency

- [ ] 7.1 Test unscored prediction has both fields NULL
- [ ] 7.2 Test scored exact match has is_exact_match=True and points > 0
- [ ] 7.3 Test scored non-exact match has is_exact_match=False
- [ ] 7.4 Test updating both scoring fields together
- [ ] 7.5 Test timestamp (updated_at) changes when scoring fields are set

## 8. Verification

- [ ] 8.1 Run all tests and verify they pass
- [ ] 8.2 Run ruff check and fix any linting issues
- [ ] 8.3 Run mypy and fix any type errors
- [ ] 8.4 Create sample predictions via shell
- [ ] 8.5 Manually set scoring fields on test predictions
- [ ] 8.6 Verify NULL values display correctly in admin
- [ ] 8.7 Verify filtering by is_exact_match works in admin
- [ ] 8.8 Verify points aggregation query works correctly
- [ ] 8.9 Verify readonly_fields prevent manual editing in admin
