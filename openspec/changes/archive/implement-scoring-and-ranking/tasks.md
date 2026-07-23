## 1. Update Team Model for Champion Categories

- [x] 1.1 Add odds_category CharField to Team model in matches/models.py
- [x] 1.2 Add choices for odds_category: (A, Category A) (B, Category B)
- [x] 1.3 Set default=None or create migration to populate existing teams
- [x] 1.4 Add help_text explaining Category A (1-8 odds), Category B (9+)
- [x] 1.5 Add type annotations for odds_category field
- [x] 1.6 Create migration for Team model odds_category field
- [x] 1.7 Update Team admin to show odds_category field and allow editing
- [x] 1.8 Document that admin sets odds_category based on current betting odds

## 2. Update User Model for Statistics

- [x] 2.1 Add total_points IntegerField to User model in users/models.py
- [x] 2.2 Set default=0 on total_points field
- [x] 2.3 Add exact_match_count IntegerField to User model
- [x] 2.4 Set default=0 on exact_match_count field
- [x] 2.5 Add jokers_used IntegerField to User model
- [x] 2.6 Set default=0 on jokers_used field
- [x] 2.7 Add type annotations for all statistics fields
- [x] 2.8 Add help_text for each statistics field
- [x] 2.9 Update User model docstring to mention statistics

## 3. Create LeaderboardSnapshot Model

- [x] 3.1 Create LeaderboardSnapshot model in scoring/models.py
- [x] 3.2 Add created_at DateTimeField with auto_now_add=True
- [x] 3.3 Add snapshot_type CharField with choices (daily, weekly, final)
- [x] 3.4 Add data JSONField for rankings array
- [x] 3.5 Add Meta class with ordering by created_at descending
- [x] 3.6 Add db_table specification
- [x] 3.7 Implement __str__ method showing type and date
- [x] 3.8 Add type annotations for all fields

## 4. Database Migrations

- [x] 4.1 Generate migration for Team model odds_category field
- [x] 4.2 Generate migration for User model statistics fields
- [x] 4.3 Generate migration for LeaderboardSnapshot model
- [x] 4.4 Review generated migration files
- [x] 4.5 Run migrations on development database
- [x] 4.6 Verify database schema updated correctly

## 5. Implement ScoringService Core

- [x] 5.1 Create scoring/services.py file
- [x] 5.2 Create ScoringService class with static methods
- [x] 5.3 Implement _calculate_base_points method (6 scoring categories)
- [x] 5.4 Implement _check_exact_score method
- [x] 5.5 Implement _check_tendency_and_diff method
- [x] 5.6 Implement _check_tendency_and_one_goal method
- [x] 5.7 Implement _check_tendency_only method
- [x] 5.8 Implement _check_one_goal_only method
- [x] 5.9 Add ROUND_MULTIPLIERS constant dict
- [x] 5.10 Implement _get_round_multiplier method
- [x] 5.11 Implement _apply_joker_multiplier method

## 6. Implement ScoringService Calculate Methods

- [x] 6.1 Implement calculate_match_points method
- [x] 6.2 Return dict with points, is_exact, base_points from calculate_match_points
- [x] 6.3 Add comprehensive docstrings with examples
- [x] 6.4 Add type hints for all parameters and returns
- [x] 6.5 Implement calculate_champion_points method
- [x] 6.6 Handle category A and B champion scoring

## 7. Implement ScoringService Batch Methods

- [x] 7.1 Implement score_prediction method (single prediction)
- [x] 7.2 Update MatchPrediction.points_earned and is_exact_match in score_prediction
- [x] 7.3 Update User statistics in score_prediction
- [x] 7.4 Implement score_all_predictions_for_match method
- [x] 7.5 Batch update predictions efficiently in score_all_predictions_for_match
- [x] 7.6 Return count of scored predictions

## 7.5. Implement Champion Prediction Scoring

- [x] 7.5.1 Implement score_champion_predictions method in ScoringService
- [x] 7.5.2 Query final match (Match.round == 'final')
- [x] 7.5.3 Check if final match is finished (status == 'finished' and goals set)
- [x] 7.5.4 Check if champion team is designated (Team.is_champion == True)
- [x] 7.5.5 Query users where User.predicted_champion.is_champion == True
- [x] 7.5.6 Determine champion team category (A: 1-8 by odds, B: 9+)
- [x] 7.5.7 Query Team model for odds_category field or mapping
- [x] 7.5.8 Assign points based on category (A: 20 pts, B: 30 pts)
- [x] 7.5.9 Add champion points to User.total_points
- [x] 7.5.10 Track which users received champion points to avoid duplication
- [x] 7.5.11 Call score_champion_predictions from final match scoring trigger
- [x] 7.5.12 Ensure idempotent (calling multiple times yields same result)
- [x] 7.5.13 Log which users awarded champion points

## 8. Implement RankingService

- [x] 8.1 Create RankingService class in scoring/services.py
- [x] 8.2 Implement get_current_leaderboard method
- [x] 8.3 Query users ordered by total_points, exact_match_count, jokers_used
- [x] 8.4 Implement rank calculation with shared rank support
- [x] 8.5 Format leaderboard entries as dicts
- [x] 8.6 Add comprehensive docstrings and type hints
- [x] 8.7 Implement _calculate_rank_numbers helper method
- [x] 8.8 Handle empty leaderboard case

## 9. Implement Match Save Override

- [x] 9.1 Override Match.save() method in matches/models.py
- [x] 9.2 Check if goals_home and goals_away are set
- [x] 9.3 Call ScoringService.score_all_predictions_for_match after save
- [x] 9.4 Wrap in try-except and log errors
- [x] 9.5 Call super().save() properly
- [x] 9.6 Add docstring explaining scoring trigger

## 10. Create Management Commands

- [x] 10.1 Create management/commands/ directory in scoring app
- [x] 10.2 Create recalculate_scores.py command
- [x] 10.3 Implement handle method to reset all statistics
- [x] 10.4 Implement iteration over finished matches
- [x] 10.5 Score champion predictions if Team.is_champion set and final match finished
- [x] 10.6 Add progress output and summary
- [x] 10.7 Create create_snapshot.py command
- [x] 10.8 Implement snapshot creation with type parameter
- [x] 10.9 Create export_leaderboard.py command
- [x] 10.10 Implement CSV export in management command
- [x] 10.11 Implement PDF export in management command
- [x] 10.12 Add file output path parameter

## 11. Update Admin Interfaces

- [x] 11.1 Add statistics fields to UserAdmin list_display
- [x] 11.2 Add statistics fields to UserAdmin fieldsets
- [x] 11.3 Make statistics fields readonly in UserAdmin
- [x] 11.4 Add list_filter for statistics ranges in UserAdmin
- [x] 11.5 Register LeaderboardSnapshot in scoring/admin.py
- [x] 11.6 Configure LeaderboardSnapshotAdmin list_display
- [x] 11.7 Add custom display method for formatted rankings
- [x] 11.8 Add admin action to create snapshot
- [x] 11.9 Make LeaderboardSnapshot fields readonly
- [x] 11.10 Add admin action to export leaderboard as CSV
- [x] 11.11 Add admin action to export leaderboard as PDF

## 12. Tests for ScoringService

- [x] 12.1 Create test_scoring_service.py in scoring/tests/
- [x] 12.2 Create fixtures for teams and matches
- [x] 12.3 Test exact score match (6 points)
- [x] 12.4 Test correct tendency and goal difference (5 points)
- [x] 12.5 Test correct tendency and one goal (4 points)
- [x] 12.6 Test correct tendency only (3 points)
- [x] 12.7 Test one goal only (1 point)
- [x] 12.8 Test no match (0 points)
- [x] 12.9 Test scoring precedence (higher category wins)
- [x] 12.10 Test group stage multiplier (x1)
- [x] 12.11 Test round of 32/16 multiplier (x2)
- [x] 12.12 Test knockout multiplier (x3)
- [x] 12.13 Test joker doubling
- [x] 12.14 Test combined: base * round * joker
- [x] 12.15 Test champion category A (20 points)
- [x] 12.16 Test champion category B (30 points)
- [x] 12.17 Test score_prediction updates prediction and user

## 12.5. Tests for Champion Prediction Scoring

- [x] 12.5.1 Test champion points awarded when user.predicted_champion == champion team
- [x] 12.5.2 Test no points awarded when prediction != champion team
- [x] 12.5.3 Test champion points added to user.total_points
- [x] 12.5.4 Test category A champion (20 points)
- [x] 12.5.5 Test category B champion (30 points)
- [ ] 12.5.6 Test idempotent scoring (calling twice = same result)
- [x] 12.5.7 Test champion scoring only triggers when Team.is_champion set
- [ ] 12.5.8 Test champion scoring with final match draw (is_champion determines winner)
- [x] 12.5.9 Test multiple users predicting same champion all receive points
- [x] 12.5.10 Test champion scoring doesn't affect match prediction points
- [x] 12.5.11 Test champion scoring called automatically when final match saved

## 13. Tests for RankingService

- [x] 13.1 Create test_ranking_service.py in scoring/tests/
- [x] 13.2 Test basic ranking by total points
- [x] 13.3 Test tiebreaker: exact matches
- [x] 13.4 Test tiebreaker: jokers used
- [x] 13.5 Test shared ranks
- [x] 13.6 Test rank numbering with ties (1, 2, 2, 4)
- [x] 13.7 Test empty leaderboard
- [x] 13.8 Test leaderboard with single user

## 14. Tests for LeaderboardSnapshot

- [x] 14.1 Create test_leaderboard_snapshot.py in scoring/tests/
- [x] 14.2 Test snapshot creation
- [x] 14.3 Test snapshot data structure
- [x] 14.4 Test snapshot immutability after creation
- [x] 14.5 Test snapshot querying by type
- [x] 14.6 Test snapshot ordering by date

## 15. Tests for Match Scoring Trigger

- [x] 15.1 Create test_match_scoring.py in matches/tests/
- [x] 15.2 Test scoring triggered on match save with results
- [x] 15.3 Test prediction points updated after match save
- [x] 15.4 Test user statistics updated after match save
- [x] 15.5 Test re-scoring when result changes
- [x] 15.6 Test no scoring when goals not set

## 16. Tests for Management Commands

- [x] 16.1 Test recalculate_scores command
- [x] 16.2 Test statistics reset in recalculate_scores
- [x] 16.3 Test rebuilding statistics from predictions
- [x] 16.4 Test create_snapshot command
- [x] 16.5 Test export_leaderboard CSV output
- [ ] 16.6 Test export_leaderboard PDF output

## 17. Integration Tests

- [x] 17.1 Create test_scoring_integration.py
- [x] 17.2 Test end-to-end: predictions → match result → scoring → leaderboard
- [x] 17.3 Test multiple matches with different rounds and jokers
- [x] 17.4 Test champion prediction flow
- [x] 17.5 Test recalculation maintains consistency
- [x] 17.6 Test leaderboard snapshot captures state correctly

## 18. Export Implementation

- [x] 18.1 Install reportlab package for PDF generation
- [x] 18.2 Create scoring/exports.py module
- [x] 18.3 Implement generate_leaderboard_csv function
- [x] 18.4 Implement generate_leaderboard_pdf function
- [x] 18.5 Add HTTP response helpers for downloads
- [x] 18.6 Test CSV formatting
- [x] 18.7 Test PDF formatting
- [x] 18.8 Test file download responses

## 19. Verification

- [x] 19.1 Run all tests and verify they pass
- [x] 19.2 Run ruff check and fix any linting issues
- [x] 19.3 Run mypy and fix any type errors
- [ ] 19.4 Create sample predictions via shell
- [ ] 19.5 Enter match results and verify automatic scoring
- [ ] 19.6 Verify user statistics updated correctly
- [ ] 19.7 Generate leaderboard and verify ranking order
- [ ] 19.8 Create snapshot and verify data saved
- [ ] 19.9 Export CSV and verify formatting
- [ ] 19.10 Export PDF and verify formatting
- [ ] 19.11 Run recalculate_scores and verify consistency
- [ ] 19.12 Test tiebreakers with sample data
- [x] 19.13 Verify admin interfaces show all fields correctly

