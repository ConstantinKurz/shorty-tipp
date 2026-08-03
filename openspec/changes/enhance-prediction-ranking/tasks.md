# Tasks: Enhanced Prediction Ranking View

## Task 1: Add user statistics aggregation to MatchPredictionsView

### Goal
Extend the existing `MatchPredictionsView` to fetch and compute aggregated user statistics (champion prediction, exact predictions count, jokers used, total points) efficiently.

### Scope
- Modify `MatchPredictionsView.get()` in `predictions/views.py`
- Add ORM annotations for:
  - `total_points`: Sum of all `points_earned` across user's predictions
  - `exact_predictions_count`: Count of predictions with 6 points
  - `jokers_used_count`: Count of predictions with `joker_used=True`
- Select related `predicted_champion` for each user
- Build user predictions list including all statistics
- Keep existing match-based sorting as default

### Out of Scope
- Sorting toggle UI
- Template changes
- Sort mode parameter handling

### Acceptance Criteria
- [x] View fetches users with annotated statistics in single query
- [x] Each user entry includes: `champion`, `exact_count`, `jokers_count`, `total_points`
- [x] No N+1 queries (verify with Django Debug Toolbar or query logging)
- [x] Existing sorting behavior preserved (match points descending)
- [x] Context passed to template includes new statistics

### Required Tests
- Test user statistics aggregation correctness
  - User with multiple predictions: verify total_points sum
  - User with exact predictions: verify count
  - User with jokers: verify jokers_used_count
  - User with no predictions: verify all stats are 0 or default
- Test query count (should be 3 queries total)
- Test champion name handling (user with/without champion)

---

## Task 2: Add sort mode parameter and flexible ranking

### Goal
Add `sort` query parameter to `MatchPredictionsView` that switches between match points and total points ranking with Olympic-style ranking applied to the selected criterion.

### Scope
- Accept `sort` parameter (`match` or `total`, default `match`)
- Apply different sorting logic based on mode:
  - `match`: Sort by match points (desc), then username
  - `total`: Sort by total points (desc), then username
- Implement Olympic-style ranking for whichever criterion is active
- Pass `sort_mode` to template context

### Out of Scope
- Template implementation
- HTMX integration
- UI for toggling sort

### Acceptance Criteria
- [x] View accepts `?sort=match` and `?sort=total` query parameters
- [x] Default behavior is `sort=match`
- [x] Invalid sort values default to `match`
- [x] Ranking is calculated based on selected sort criterion
- [x] Olympic-style ranking applied correctly:
  - Users with same value share rank
  - Next rank skips (1, 2, 2, 4)
- [x] Context includes `sort_mode` variable

### Required Tests
- Test sort parameter parsing (match, total, invalid, missing)
- Test sorting by match points (verify order)
- Test sorting by total points (verify order)
- Test Olympic ranking with ties in match mode
- Test Olympic ranking with ties in total mode
- Test rank skipping after ties

---

## Task 3: Update match predictions template with statistics display

### Goal
Enhance the match predictions template to display user statistics (champion, exact count, jokers count, total points) in a compact, mobile-friendly layout.

### Scope
- Modify `templates/predictions/partials/match_predictions.html`
- Add statistics line under username in each user row
- Use icons + numbers for compact display:
  - 🏆 Champion name
  - ✓ Exact predictions count
  - ⭐ Jokers used count
  - Σ Total points
- Keep existing layout structure
- Ensure mobile responsiveness

### Out of Scope
- Sort toggle UI
- HTMX integration
- View logic

### Acceptance Criteria
- [x] Statistics displayed for each user in predictions list
- [x] Champion name shown (or placeholder if not set)
- [x] Exact count, jokers count, total points visible
- [x] Layout remains scannable on mobile (320px+)
- [x] Current user row highlighting preserved
- [x] No prediction users still show statistics

### Required Tests
- Visual inspection on mobile and desktop
- Template rendering with various user data scenarios
- Check layout with long champion names
- Check layout with high stat numbers (3+ digits)

---

## Task 4: Add sort toggle UI with HTMX

### Goal
Add a sort toggle control above the predictions list that dynamically re-sorts the view using HTMX without full page reload.

### Scope
- Add toggle button group to template (Match Points / Total Points)
- Wire buttons with HTMX attributes:
  - `hx-get` with sort parameter
  - `hx-target` for bottom sheet content
  - `hx-swap` for smooth update
- Add active state styling based on `sort_mode`
- Ensure touch-friendly sizing for mobile

### Out of Scope
- View logic (already implemented in Task 2)
- Statistics display (already implemented in Task 3)

### Acceptance Criteria
- [x] Toggle buttons displayed above predictions list
- [x] Active sort mode visually indicated
- [x] Clicking toggle triggers HTMX request with sort parameter
- [x] Predictions list re-renders with new sort order
- [x] No full page reload
- [x] Toggle works on mobile and desktop
- [x] Bottom sheet remains open during re-sort

### Required Tests
- Manual testing: click both toggle buttons
- Verify HTMX request sent with correct query parameter
- Verify predictions list updates without closing bottom sheet
- Test on mobile device or responsive view
- Verify active state switches correctly

---

## Task 5: Add CSS styling for sort toggle and statistics

### Goal
Style the sort toggle and statistics display to match the app's design system and ensure mobile-first responsiveness.

### Scope
- Add styles for sort toggle buttons
  - Pill-style design
  - Active state styling (background, color)
  - Hover and focus states
- Style statistics line
  - Compact spacing
  - Icon + number alignment
  - Responsive font sizing
- Ensure consistent spacing and alignment across mobile and desktop

### Out of Scope
- JavaScript logic
- Template structure
- View logic

### Acceptance Criteria
- [x] Sort toggle has clear active state
- [x] Buttons are touch-friendly (min 44px touch target)
- [x] Statistics line is scannable and well-spaced
- [x] Design matches existing app aesthetics (Tailwind CSS if used)
- [x] Styles work across major browsers
- [x] Dark mode compatibility (if app has dark mode)

### Required Tests
- Visual inspection on different screen sizes
- Test active state transitions
- Test accessibility (keyboard navigation, focus indicators)
- Cross-browser testing (Chrome, Safari, Firefox)

---

## Task 6: Add view and integration tests

### Goal
Add comprehensive tests for the enhanced view logic, sorting behavior, and HTMX integration.

### Scope
- Add tests to `predictions/tests/test_views.py`
- Test cases:
  - Statistics aggregation accuracy
  - Sort parameter handling
  - Ranking algorithm with both sort modes
  - Context data correctness
  - HTMX request/response behavior
- Use pytest-django fixtures for test data

### Out of Scope
- Frontend JavaScript tests
- End-to-end browser tests

### Acceptance Criteria
- [x] Test statistics aggregation for multiple users
- [x] Test sort mode switching
- [x] Test Olympic ranking in both modes with ties
- [x] Test HTMX response format
- [x] Test edge cases (no predictions, all users tied)
- [x] All tests pass
- [x] Code coverage for new view logic at 90%+

### Required Tests
- `test_match_predictions_view_with_statistics`: Verify stats in context
- `test_sort_by_match_points`: Verify match sort order
- `test_sort_by_total_points`: Verify total sort order
- `test_olympic_ranking_match_mode`: Ranking with ties
- `test_olympic_ranking_total_mode`: Ranking with ties
- `test_invalid_sort_parameter`: Defaults to match
- `test_no_predictions_edge_case`: All stats are zero

---

## Implementation Order

1. Task 1: Add statistics aggregation (foundation)
2. Task 2: Add sort mode logic (core feature)
3. Task 3: Update template with statistics (UI)
4. Task 4: Add sort toggle with HTMX (UI interaction)
5. Task 5: Add styling (polish)
6. Task 6: Add tests (validation)

Each task can be independently reviewed and tested.
