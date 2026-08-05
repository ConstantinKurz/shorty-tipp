# Tasks: Add Predictions View

## 1. Create PredictionLimitService

- [ ] 1.1 Create `predictions/services.py`
- [ ] 1.2 Create `PredictionLimitService` class with configurable limits
- [ ] 1.3 Implement `JOKER_LIMITS` dict (gs=0, r32=3, r16=3, qf=2, sf/final/third=2 combined)
- [ ] 1.4 Implement `COMBINED_ROUNDS` set for sf, final, third sharing joker pool
- [ ] 1.5 Implement `GROUP_STAGE_LIMIT = 36`
- [ ] 1.6 Implement `get_joker_limit_for_round(round_code) -> int`
- [ ] 1.7 Implement `get_joker_count_for_round(user, round_code) -> int` (handles combined rounds)
- [ ] 1.8 Implement `can_add_joker(user, round_code) -> bool`
- [ ] 1.9 Implement `get_group_stage_prediction_count(user) -> int`
- [ ] 1.10 Implement `can_add_group_stage_prediction(user) -> bool`
- [ ] 1.11 Add type hints and docstrings

## 2. Create PredictionForm

- [ ] 2.1 Create `predictions/forms.py`
- [ ] 2.2 Create `PredictionForm` as ModelForm for `MatchPrediction`
- [ ] 2.3 Include fields: `predicted_goals_home`, `predicted_goals_away`
- [ ] 2.4 Add `min_value=0` and `max_value=99` validation for goal fields
- [ ] 2.5 Style widgets with Tailwind classes (small number inputs)
- [ ] 2.6 Add type hints and docstring

## 3. Create PredictionListView

- [ ] 3.1 Create `PredictionListView` in `predictions/views.py`
- [ ] 3.2 Inherit from `LoginRequiredMixin` and `TemplateView`
- [ ] 3.3 Set `template_name = "predictions/prediction_list.html"`
- [ ] 3.4 Implement `get_context_data()` method
- [ ] 3.5 Query ALL matches with `select_related('team_home', 'team_away')` ordered by `kickoff`
- [ ] 3.6 Query user's predictions with `select_related('match')`
- [ ] 3.7 Build `prediction_map` dict (match_id -> prediction)
- [ ] 3.8 Build `matches_data` list with match, prediction, is_locked, joker info
- [ ] 3.9 Group matches by date for display
- [ ] 3.10 Add `group_stage_count` and `group_stage_limit` to context
- [ ] 3.11 Add type hints to all methods

## 4. Create PredictionSaveView (HTMX)

- [ ] 4.1 Create `PredictionSaveView` in `predictions/views.py`
- [ ] 4.2 Inherit from `LoginRequiredMixin` and `View`
- [ ] 4.3 Implement `post()` method only
- [ ] 4.4 Load match by `match_id` URL parameter (return 404 if not found)
- [ ] 4.5 Check locktime: if `kickoff <= now`, return 400 error partial
- [ ] 4.6 Validate form data (goals 0-99)
- [ ] 4.7 Check group stage limit if new prediction for gs match
- [ ] 4.8 Create or update prediction (get_or_create pattern)
- [ ] 4.9 Return updated match row partial (prediction_row.html)
- [ ] 4.10 Add type hints

## 5. Create PredictionDeleteView (HTMX)

- [ ] 5.1 Create `PredictionDeleteView` in `predictions/views.py`
- [ ] 5.2 Inherit from `LoginRequiredMixin` and `View`
- [ ] 5.3 Implement `post()` method only
- [ ] 5.4 Load match and prediction (404 if not found)
- [ ] 5.5 Check locktime (400 if locked)
- [ ] 5.6 Delete prediction
- [ ] 5.7 Return cleared match row partial
- [ ] 5.8 Add type hints

## 6. Create PredictionJokerView (HTMX)

- [ ] 6.1 Create `PredictionJokerView` in `predictions/views.py`
- [ ] 6.2 Inherit from `LoginRequiredMixin` and `View`
- [ ] 6.3 Implement `post()` method only
- [ ] 6.4 Load match and prediction (404/400 if not found)
- [ ] 6.5 Check locktime (400 if locked)
- [ ] 6.6 Check round is not 'gs' (400 if group stage)
- [ ] 6.7 If enabling joker: check limit with `PredictionLimitService.can_add_joker()`
- [ ] 6.8 Toggle `joker_active` and save
- [ ] 6.9 Return updated match row partial
- [ ] 6.10 Add type hints

## 7. Add URL Routes

- [ ] 7.1 Create `predictions/urls.py`
- [ ] 7.2 Add `path("", PredictionListView.as_view(), name="prediction-list")`
- [ ] 7.3 Add `path("<int:match_id>/save/", PredictionSaveView.as_view(), name="prediction-save")`
- [ ] 7.4 Add `path("<int:match_id>/delete/", PredictionDeleteView.as_view(), name="prediction-delete")`
- [ ] 7.5 Add `path("<int:match_id>/joker/", PredictionJokerView.as_view(), name="prediction-joker")`
- [ ] 7.6 Update `tipapp/urls.py` to include `predictions.urls` at `/predictions/`

## 8. Create Prediction List Template

- [ ] 8.1 Create `templates/predictions/` directory
- [ ] 8.2 Create `templates/predictions/prediction_list.html` extending `base.html`
- [ ] 8.3 Set page title "Meine Tipps - Shortytipp Tippspiel"
- [ ] 8.4 Add gradient background wrapper matching existing pages
- [ ] 8.5 Create main card container
- [ ] 8.6 Add heading "🎯 Meine Tipps" with group stage counter (X/36)
- [ ] 8.7 Group matches by date with date headers
- [ ] 8.8 Include match row partial for each match
- [ ] 8.9 Include HTMX library in base or template
- [ ] 8.10 Style for dark/light mode
- [ ] 8.11 Make template responsive for mobile

## 9. Create Match Row Partial Template

- [ ] 9.1 Create `templates/predictions/prediction_row.html`
- [ ] 9.2 Add match row container with `id="match-{{ match.id }}"`
- [ ] 9.3 Display kickoff time
- [ ] 9.4 Display team names with flag emojis
- [ ] 9.5 Add goal input fields (disabled if locked)
- [ ] 9.6 Add `hx-post` to inputs for auto-save
- [ ] 9.7 Add `hx-trigger="change"` with JS to only trigger when both fields filled
- [ ] 9.8 Add `hx-target="#match-{{ match.id }}"` and `hx-swap="outerHTML"`
- [ ] 9.9 Add joker toggle button (⭐/☆) if not group stage
- [ ] 9.10 Add `hx-post` to joker button for immediate save
- [ ] 9.11 Add delete button (🗑️) if prediction exists and not locked
- [ ] 9.12 Add `hx-post` to delete button
- [ ] 9.13 Show 🔒 icon if match is locked
- [ ] 9.14 Show match result (goals_home:goals_away) if match finished
- [ ] 9.15 Show points earned if prediction scored
- [ ] 9.16 Include CSRF token in forms

## 10. Create Error Partial Template

- [ ] 10.1 Create `templates/predictions/prediction_error.html`
- [ ] 10.2 Display error message inline
- [ ] 10.3 Style with red/warning colors

## 11. Add JavaScript for Auto-save Logic

- [ ] 11.1 Create `static/predictions/js/autosave.js` or inline in template
- [ ] 11.2 Add event listener for input changes
- [ ] 11.3 Check if both goal fields are filled before triggering HTMX
- [ ] 11.4 Prevent save with only one field filled

## 12. Update Base Template

- [ ] 12.1 Open `templates/base.html`
- [ ] 12.2 Add "Tipps" navigation link to `/predictions/`
- [ ] 12.3 Ensure HTMX is included (CDN or static)

## 13. Write Service Tests

- [ ] 13.1 Create `predictions/tests/test_services.py`
- [ ] 13.2 Test: `get_joker_limit_for_round` returns correct limits
- [ ] 13.3 Test: `get_joker_count_for_round` counts correctly
- [ ] 13.4 Test: `get_joker_count_for_round` combines sf/final/third
- [ ] 13.5 Test: `can_add_joker` returns True when under limit
- [ ] 13.6 Test: `can_add_joker` returns False when at limit
- [ ] 13.7 Test: `can_add_joker` returns False for group stage
- [ ] 13.8 Test: `get_group_stage_prediction_count` counts correctly
- [ ] 13.9 Test: `can_add_group_stage_prediction` returns True under 36
- [ ] 13.10 Test: `can_add_group_stage_prediction` returns False at 36

## 14. Write Form Tests

- [ ] 14.1 Create `predictions/tests/test_forms.py`
- [ ] 14.2 Test: valid data creates valid form
- [ ] 14.3 Test: negative home goals rejected
- [ ] 14.4 Test: negative away goals rejected
- [ ] 14.5 Test: goals over 99 rejected
- [ ] 14.6 Test: missing goals rejected

## 15. Write View Tests

- [ ] 15.1 Create `predictions/tests/test_views.py`
- [ ] 15.2 Create fixtures: user, teams, matches (future/past/gs/knockout)
- [ ] 15.3 Test: GET /predictions/ requires authentication
- [ ] 15.4 Test: GET /predictions/ returns 200 for authenticated user
- [ ] 15.5 Test: prediction list shows all matches ordered by kickoff
- [ ] 15.6 Test: prediction list shows user's existing predictions
- [ ] 15.7 Test: POST /predictions/<id>/save/ creates new prediction
- [ ] 15.8 Test: POST /predictions/<id>/save/ updates existing prediction
- [ ] 15.9 Test: POST /predictions/<id>/save/ rejected after locktime
- [ ] 15.10 Test: POST /predictions/<id>/save/ rejected when gs limit exceeded
- [ ] 15.11 Test: POST /predictions/<id>/delete/ removes prediction
- [ ] 15.12 Test: POST /predictions/<id>/delete/ rejected after locktime
- [ ] 15.13 Test: POST /predictions/<id>/joker/ toggles joker
- [ ] 15.14 Test: POST /predictions/<id>/joker/ rejected for group stage
- [ ] 15.15 Test: POST /predictions/<id>/joker/ rejected when limit exceeded
- [ ] 15.16 Test: 404 for invalid match ID
- [ ] 15.17 Test: Points displayed correctly for finished matches

## 16. Code Quality

- [ ] 16.1 Run `ruff check predictions/` and fix issues
- [ ] 16.2 Run `ruff format predictions/`
- [ ] 16.3 Run `mypy predictions/` and fix type errors
- [ ] 16.4 Add docstrings to all public classes and methods
- [ ] 16.5 Verify no unused imports

## 17. Final Verification

- [ ] 17.1 Run full test suite with `pytest`
- [ ] 17.2 Verify all new tests pass
- [ ] 17.3 Verify existing tests still pass
- [ ] 17.4 Manual test: view prediction list
- [ ] 17.5 Manual test: auto-save prediction (both fields filled)
- [ ] 17.6 Manual test: no save with only one field
- [ ] 17.7 Manual test: toggle joker
- [ ] 17.8 Manual test: delete prediction
- [ ] 17.9 Manual test: verify locktime blocks editing
- [ ] 17.10 Manual test: verify joker limit blocks additional jokers
- [ ] 17.11 Manual test: verify group stage limit blocks 37th prediction
- [ ] 17.12 Manual test: verify points and results display
- [ ] 17.13 Commit changes with descriptive message
