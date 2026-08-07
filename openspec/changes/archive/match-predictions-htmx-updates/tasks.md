# Tasks: HTMX Auto-Updates for Match Predictions Page

## Task 1: Extract Prediction List Building Logic

- [x] Completed

### Goal
Extract the user predictions list building logic from `MatchPredictionsView` into a reusable helper function that can be shared with the new update endpoint.

### Scope
- Create helper function `build_match_predictions_list()` in `predictions/views.py`
- Function takes: `match`, `sort_mode`, `current_user`
- Function returns: list of prediction dicts with user, rank, prediction data, points, stats
- Move all prediction querying and ranking logic from `MatchPredictionsView.get_context_data()` into helper
- Refactor `MatchPredictionsView` to use the new helper
- Add type hints and docstring to helper function

### Out of Scope
- Creating the update endpoint view
- Template changes
- URL configuration
- Changing the actual prediction logic or ranking algorithm

### Acceptance Criteria
- Helper function `build_match_predictions_list()` exists in `predictions/views.py`
- Function has complete type hints: parameters and return type
- Function has Google-style docstring explaining purpose, args, and returns
- `MatchPredictionsView.get_context_data()` calls the helper instead of inline logic
- Helper returns same data structure as before (no breaking changes)
- Sort mode "match" sorts by match points descending, then username
- Sort mode "total" sorts by total points descending, then username
- Rankings assigned correctly (1, 2, 3, ...)
- Each prediction dict contains: user, rank, has_predicted, predicted_goals_home, predicted_goals_away, joker_active, points_earned, champion, exact_matches, joker_count, total_points
- Code passes mypy type checking
- Code passes ruff linting

### Required Tests
- Unit test: `test_build_match_predictions_list_sort_by_match_points()`
  - Create match with predictions from multiple users
  - Users have different match points for this match
  - Call helper with sort_mode="match"
  - Assert users sorted by match points descending
  - Assert ties broken by username alphabetically
- Unit test: `test_build_match_predictions_list_sort_by_total_points()`
  - Create match with predictions
  - Users have different total points in their profiles
  - Call helper with sort_mode="total"
  - Assert users sorted by total points descending
- Unit test: `test_build_match_predictions_list_includes_users_without_predictions()`
  - Create match with some users having predictions, some not
  - Call helper
  - Assert all active users included in result
  - Assert users without predictions show has_predicted=False, points_earned=0
- Unit test: `test_build_match_predictions_list_assigns_ranks()`
  - Create match with 5 users having different scores
  - Call helper
  - Assert ranks are 1, 2, 3, 4, 5 in order
- Integration test: `test_match_predictions_view_still_works()`
  - Make GET request to `/predictions/match/<id>/all/`
  - Assert response 200
  - Assert context contains user_predictions
  - Assert template renders successfully

---

## Task 2: Create Match Predictions Update Endpoint

- [x] Completed

### Goal
Create a new view `MatchPredictionsUpdateView` that returns an HTML partial with updated predictions for HTMX polling.

### Scope
- Add `MatchPredictionsUpdateView` class in `predictions/views.py`
- Inherit from `LoginRequiredMixin` and `View`
- Implement `get()` method
- Use helper function from Task 1 to build predictions list
- Parse `sort` query parameter (default: "match", allowed: "match", "total")
- Parse `from` query parameter for origin tracking (preserve in context)
- Render `predictions/partials/match_predictions_content.html` (will be created in Task 3)
- Return 404 if match doesn't exist
- Require authentication

### Out of Scope
- Creating the partial template (Task 3)
- URL configuration (Task 4)
- Full page template changes (Task 5)
- Polling logic in frontend

### Acceptance Criteria
- `MatchPredictionsUpdateView` class exists in `predictions/views.py`
- View inherits from `LoginRequiredMixin` and `View`
- View has `get(request, match_id)` method with type hints
- Method calls `build_match_predictions_list()` helper from Task 1
- Method validates `sort` parameter: "match" or "total", defaults to "match"
- Method preserves `from` parameter in context (for sort toggle links)
- Method returns rendered partial template
- Method returns 404 for non-existent match
- Unauthenticated users redirected to login
- View passes mypy type checking
- View passes ruff linting

### Required Tests
- View test: `test_match_predictions_update_view_requires_auth()`
  - GET request from anonymous user
  - Assert redirect to login
- View test: `test_match_predictions_update_view_returns_404_for_invalid_match()`
  - GET request with non-existent match_id
  - Assert 404 response
- View test: `test_match_predictions_update_view_default_sort_mode()`
  - GET request without sort parameter
  - Assert context["sort_mode"] == "match"
- View test: `test_match_predictions_update_view_validates_sort_mode()`
  - GET request with sort="invalid"
  - Assert context["sort_mode"] == "match" (falls back to default)
- View test: `test_match_predictions_update_view_accepts_valid_sort_modes()`
  - GET request with sort="match" → assert context["sort_mode"] == "match"
  - GET request with sort="total" → assert context["sort_mode"] == "total"
- View test: `test_match_predictions_update_view_preserves_origin()`
  - GET request with from="home"
  - Assert context["origin"] == "home"
- View test: `test_match_predictions_update_view_context_structure()`
  - GET request with valid match
  - Assert context contains: match, user_predictions, sort_mode, current_user, origin
- View test: `test_match_predictions_update_view_uses_correct_template()`
  - GET request
  - Assert response renders "predictions/partials/match_predictions_content.html"

---

## Task 3: Create Partial Template for Predictions Content

- [x] Completed

### Goal
Extract the sort toggle and predictions list from `match_predictions_page.html` into a reusable partial template that can be rendered by both the full page and the update endpoint.

### Scope
- Create `templates/predictions/partials/match_predictions_content.html`
- Copy sort toggle section from `match_predictions_page.html`
- Copy predictions list section from `match_predictions_page.html`
- Ensure all template variables are used correctly: match, user_predictions, sort_mode, origin, current_user
- Maintain all existing styling and structure
- Include empty state for when no predictions exist

### Out of Scope
- Match info card (stays in full page template)
- Back button (stays in full page template)
- HTMX polling attributes (added in Task 5)
- Changes to prediction rendering logic

### Acceptance Criteria
- File `templates/predictions/partials/match_predictions_content.html` exists
- Partial contains sort toggle with two buttons: "Spielpunkte" and "Gesamtpunkte"
- Sort toggle buttons link to `?sort=match&from={{ origin }}` and `?sort=total&from={{ origin }}`
- Active sort mode has emerald background, inactive has gray background
- Partial contains predictions list with all users
- Each prediction shows: rank, username, joker icon (if active), prediction, points earned
- Each prediction shows stats: champion team, exact matches, joker count, total points
- Current user's prediction highlighted with emerald background
- Empty state shown when `user_predictions` is empty
- All icons match spec: ⭐ (joker), 🏆 (champion), ✓ (exact matches)
- Styling matches existing design (Tailwind classes, dark mode support)
- Responsive design works on mobile and desktop
- No syntax errors in template

### Required Tests
- Template test: `test_match_predictions_content_partial_renders()`
  - Render partial with valid context
  - Assert no template errors
- Template test: `test_match_predictions_content_partial_shows_predictions()`
  - Create context with 3 users and predictions
  - Render partial
  - Assert HTML contains all 3 usernames
  - Assert HTML contains all 3 predictions
- Template test: `test_match_predictions_content_partial_highlights_current_user()`
  - Create context with current_user in predictions
  - Render partial
  - Assert current user's row has emerald background class
- Template test: `test_match_predictions_content_partial_empty_state()`
  - Render partial with empty user_predictions list
  - Assert HTML contains "Noch keine Tipps" message
- Template test: `test_match_predictions_content_partial_sort_toggle()`
  - Render with sort_mode="match"
  - Assert "Spielpunkte" button has active styling
  - Render with sort_mode="total"
  - Assert "Gesamtpunkte" button has active styling
- Visual test: Manual inspection on multiple screen sizes

---

## Task 4: Add URL Pattern for Update Endpoint

- [x] Completed

### Goal
Add URL configuration for the new `MatchPredictionsUpdateView` so it can be accessed via HTMX polling.

### Scope
- Update `predictions/urls.py`
- Add URL pattern for `match/<int:match_id>/updates/`
- Map to `MatchPredictionsUpdateView.as_view()`
- Name the URL pattern `match-predictions-updates`
- Place the pattern near the existing `match-predictions` pattern for clarity

### Out of Scope
- View implementation (Task 2)
- Template changes
- Frontend HTMX integration

### Acceptance Criteria
- URL pattern exists in `predictions/urls.py`
- Pattern path: `"match/<int:match_id>/updates/"`
- Pattern view: `views.MatchPredictionsUpdateView.as_view()`
- Pattern name: `"match-predictions-updates"`
- URL is resolvable with `reverse("predictions:match-predictions-updates", args=[match_id])`
- No URL conflicts with existing patterns

### Required Tests
- URL test: `test_match_predictions_updates_url_resolves()`
  - Reverse URL with match_id=1
  - Assert URL is `/predictions/match/1/updates/`
- Integration test: `test_match_predictions_updates_url_accessible()`
  - Create match and login user
  - GET `/predictions/match/<id>/updates/`
  - Assert response 200
  - Assert response is HTML

---

## Task 5: Add HTMX Polling to Full Page Template

- [x] Completed

### Goal
Update the match predictions full page template to use the partial from Task 3 and add HTMX polling attributes for automatic updates.

### Scope
- Update `templates/predictions/match_predictions_page.html`
- Add `polling_interval` to view context in `MatchPredictionsView`
- Replace inline predictions list with `{% include "predictions/partials/match_predictions_content.html" %}`
- Wrap included partial in a div with HTMX attributes
- Add `id="predictions-content"` to the wrapper
- Add `hx-get` pointing to update endpoint with query params
- Add `hx-trigger="every {{ polling_interval }}s"` for dynamic polling
- Add `hx-swap="innerHTML"` to replace content smoothly
- Ensure sort mode and origin are passed in hx-get URL

### Out of Scope
- Changing match info card or back button
- Modifying the partial template itself
- Backend polling interval logic (already exists)
- Adding new JavaScript

### Acceptance Criteria
- `MatchPredictionsView.get_context_data()` adds `polling_interval` to context
- Polling interval calculated using `get_polling_interval()` function
- Template includes partial: `{% include "predictions/partials/match_predictions_content.html" %}`
- Partial wrapped in div with `id="predictions-content"`
- Div has `hx-get="{% url 'predictions:match-predictions-updates' match.id %}?sort={{ sort_mode }}&from={{ origin }}"`
- Div has `hx-trigger="every {{ polling_interval }}s"`
- Div has `hx-swap="innerHTML"`
- Match info card and back button remain in full page template (not in partial)
- Template renders without errors
- HTMX polling starts on page load
- Polling preserves sort mode and origin parameters

### Required Tests
- View test: `test_match_predictions_view_includes_polling_interval()`
  - GET request to `/predictions/match/<id>/all/`
  - Assert context["polling_interval"] exists
  - Assert value is integer (1 or 60)
- Template test: `test_match_predictions_page_has_htmx_polling()`
  - Render full page template
  - Assert HTML contains `hx-get` attribute
  - Assert HTML contains `hx-trigger` with polling interval
  - Assert HTML contains `hx-swap="innerHTML"`
- Template test: `test_match_predictions_page_includes_partial()`
  - Render full page template
  - Assert partial content is included
  - Assert sort toggle present
  - Assert predictions list present
- Integration test: `test_match_predictions_page_polling_works_end_to_end()`
  - Load full page
  - Create new prediction in database
  - Wait for polling interval
  - Assert updated prediction appears in next poll response

---

## Task 6: Add Tests for Polling Behavior

- [x] Completed

### Goal
Add integration tests that verify HTMX polling updates work correctly and display changes when predictions or rankings change.

### Scope
- Test that update endpoint returns current predictions
- Test that polling detects new predictions
- Test that polling detects prediction changes
- Test that polling reflects ranking changes
- Test that sort mode is preserved during updates
- Test that polling interval adjusts based on match activity

### Out of Scope
- Frontend JavaScript testing (focus on server responses)
- Performance testing or load testing
- Testing HTMX library itself

### Acceptance Criteria
- All tests pass
- Tests verify prediction updates are reflected in polling response
- Tests verify ranking changes are reflected in polling response
- Tests verify sort mode preserved across polls
- Tests verify polling interval changes based on match timing
- Tests use realistic match and prediction data

### Required Tests
- Integration test: `test_polling_detects_new_prediction()`
  - Load match predictions page
  - Get initial update response
  - Another user submits prediction
  - Get second update response
  - Assert second response includes new prediction
- Integration test: `test_polling_detects_prediction_changes()`
  - User A has prediction with 3 points
  - Load update endpoint
  - User A's prediction changes, now has 5 points
  - Load update endpoint again
  - Assert response shows updated points
- Integration test: `test_polling_detects_ranking_changes()`
  - Users ranked: A (10 pts), B (8 pts), C (5 pts)
  - Load update endpoint
  - User C scores 10 points on another match (total changes)
  - Load update endpoint with sort=total
  - Assert rankings updated to reflect total points change
- Integration test: `test_polling_preserves_sort_mode()`
  - Load update endpoint with sort=match
  - Assert sort toggle shows "Spielpunkte" as active
  - Load update endpoint with sort=total
  - Assert sort toggle shows "Gesamtpunkte" as active
- Integration test: `test_polling_interval_during_active_match()`
  - Create match with kickoff 30 minutes ago
  - Get polling interval
  - Assert interval == 1 (active match)
- Integration test: `test_polling_interval_during_idle_period()`
  - Create match with kickoff 5 hours ago (past active window)
  - Get polling interval
  - Assert interval == 60 (idle)

---

## Task 7: Update Documentation

- [x] Completed

### Goal
Document the HTMX polling feature, polling intervals, and update endpoint in project documentation.

### Scope
- Update relevant code docstrings
- Add comments explaining HTMX polling behavior in template
- Update `docs/project/decisions.md` if this affects architectural decisions

### Out of Scope
- Writing user-facing help documentation
- Creating API documentation
- Writing tutorial guides

### Acceptance Criteria
- `MatchPredictionsUpdateView` has docstring explaining its purpose
- Template comments explain HTMX polling attributes and behavior
- If polling interval logic is not obvious, add inline comments
- All new functions have Google-style docstrings
- Code is self-documenting with clear variable names

### Required Tests
- Documentation review: verify all public methods have docstrings
- Code review: verify complex logic has explanatory comments

---

## Implementation Order

1. Task 1 (extract helper) - foundational refactoring
2. Task 2 (create view) - depends on Task 1
3. Task 3 (create partial) - can be done in parallel with Task 2
4. Task 4 (add URL) - quick, depends on Task 2
5. Task 5 (update template) - depends on Tasks 3 and 4
6. Task 6 (tests) - comprehensive testing after all features work
7. Task 7 (docs) - final polish

## Dependencies

```
Task 1 (helper)
    ↓
Task 2 (view endpoint) ──→ Task 4 (URL)
    ↓                           ↓
Task 3 (partial template) ──→ Task 5 (full page HTMX)
                                ↓
                           Task 6 (tests)
                                ↓
                           Task 7 (docs)
```
