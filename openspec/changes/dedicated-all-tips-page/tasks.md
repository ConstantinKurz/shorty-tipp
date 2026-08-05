# Tasks: Dedicated All Tips Page

## Task 1: Refactor MatchPredictionsView to Full Page

- [x] Done

### Goal
Convert `MatchPredictionsView` from returning an HTMX partial to rendering a complete page template.

### Scope
- Change view base class from `View` to `TemplateView`
- Add `template_name = "predictions/match_predictions_page.html"`
- Move logic from `get()` to `get_context_data()`
- Parse `from` query parameter for origin tracking
- Parse `sort` query parameter for ranking mode
- Return full context for template rendering

### Out of Scope
- Template creation (separate task)
- URL changes
- Removing bottom sheet

### Acceptance Criteria
- View inherits from `TemplateView` and `LoginRequiredMixin`
- `get_context_data()` returns context with: match, user_predictions, sort_mode, origin, current_user
- Origin defaults to "predictions" if not provided or invalid
- Sort mode defaults to "match" if not provided or invalid
- View still requires authentication
- View returns 404 for non-existent match

### Required Tests
- Test unauthenticated user is redirected
- Test 404 for invalid match ID
- Test context contains all required keys
- Test origin parameter validation ("home", "predictions", invalid → "predictions")
- Test sort parameter validation ("match", "total", invalid → "match")
- Test user_predictions list structure and ranking

---

## Task 2: Create Full Page Template

- [x] Done

### Goal
Create the dedicated page template for displaying all predictions for a match.

### Scope
- Create `templates/predictions/match_predictions_page.html`
- Extend `base.html`
- Include sticky header with back button
- Display match info card (teams, result, kickoff time)
- Add sort toggle (Spielpunkte / Gesamtpunkte)
- Display predictions list with ranking
- Reuse prediction item markup from current partial
- Implement responsive design (mobile-first)
- Use consistent icons

### Out of Scope
- View logic
- JavaScript interactivity
- Real-time updates

### Acceptance Criteria
- Template extends base.html
- Page title includes match teams
- Back button links to origin page (home or predictions)
- Back button uses 🔙 icon
- Match info displayed: teams, score, kickoff time
- Sort toggle preserves origin parameter in URLs
- Predictions list shows: rank, username, prediction, joker, points, stats
- Current user's prediction is highlighted (emerald background)
- Empty state message if no predictions
- Responsive on mobile (320px+) and desktop (1024px+)
- Max width container centers content
- Icons match design spec (👥, 🔙, ⭐, 🏆, ✓)

### Required Tests
- Template renders without errors
- Visual inspection on multiple screen sizes
- Back navigation works from both origins

---

## Task 3: Update Predictions Page Navigation

- [x] Done

### Goal
Replace bottom sheet trigger with standard link to dedicated page.

### Scope
- Update `templates/predictions/prediction_row.html`
- Replace HTMX button with anchor tag
- Add `?from=predictions` query parameter
- Use 👥 icon for "Alle Tipps" button
- Maintain existing styling

### Out of Scope
- Home page updates
- Bottom sheet removal
- View changes

### Acceptance Criteria
- "Alle Tipps" button is an `<a>` tag, not a button with HTMX
- Link URL: `/predictions/match/<id>/all/?from=predictions`
- Button displays 👥 icon and "Alle Tipps" text
- Styling matches existing design (text-sm, gap-2, hover states)
- No HTMX attributes on the link

### Required Tests
- Visual inspection
- Click navigates to dedicated page
- Back button returns to predictions page

---

## Task 4: Add Home Page Navigation

- [x] Done

### Goal
Add "Alle Tipps" button to match cards on the home page.

### Scope
- Update `templates/home.html`
- Add "Alle Tipps" link to match display
- Add `?from=home` query parameter
- Use 👥 icon for consistency
- Position appropriately in match card layout

### Out of Scope
- Predictions page updates
- Template restructuring
- Adding new match card features

### Acceptance Criteria
- "Alle Tipps" link added to each match card on home page
- Link URL: `/predictions/match/<id>/all/?from=home`
- Button displays 👥 icon and "Alle Tipps" text
- Link is touch-friendly on mobile (44x44px target)
- Styling consistent with home page design
- Link is accessible and keyboard-navigable

### Required Tests
- Visual inspection on home page
- Click navigates to dedicated page with origin=home
- Back button returns to home page

---

## Task 5: Standardize Icons Across App

- [x] Done

### Goal
Ensure consistent icon usage across all pages (home, predictions, ranking, all-tips).

### Scope
- Audit icon usage in all templates
- Standardize to agreed icon set:
  - 👥 "Alle Tipps" button
  - 🔙 Back navigation
  - ⭐ Joker indicator
  - 🏆 Champion prediction
  - ✓ Exact match count
  - ✏️ Edit button
  - 🗑️ Delete button
- Update templates to use consistent icons
- Document icon choices in code comments

### Out of Scope
- Adding new features
- Changing icon meanings
- Using icon fonts or SVG sprites

### Acceptance Criteria
- All "Alle Tipps" buttons use 👥 icon
- All back buttons use 🔙 icon
- All joker indicators use ⭐ icon
- All champion predictions use 🏆 icon
- All exact match counts use ✓ icon
- Icons are consistent in: home.html, prediction_list.html, prediction_row.html, ranking.html, match_predictions_page.html
- Icon usage documented with HTML comments in templates

### Required Tests
- Visual inspection across all pages
- Manual comparison of icon usage

---

## Task 6: Remove Bottom Sheet Component

- [x] Done

### Goal
Clean up bottom sheet code from templates and JavaScript.

### Scope
- Remove bottom sheet HTML from `templates/base.html`
- Remove bottom sheet JavaScript from `templates/base.html`
- Remove bottom sheet styles from base template or CSS files
- Remove unused partial template if not needed elsewhere

### Out of Scope
- Other template changes
- Updating links (already done in previous tasks)

### Acceptance Criteria
- No `#bottom-sheet-backdrop` element in base.html
- No `#bottom-sheet` element in base.html
- No bottom sheet JavaScript event listeners
- No bottom sheet CSS animations or styles
- Partial template `match_predictions.html` removed if not used elsewhere
- No console errors after removal
- No visible UI artifacts

### Required Tests
- Visual inspection of all pages
- Test that no JavaScript errors occur
- Verify predictions page still works
- Verify home page still works
- Test navigation to dedicated all-tips page

---

## Task 7: Add Integration Tests

- [x] Done

### Goal
Verify end-to-end navigation flow and page rendering.

### Scope
- Create `predictions/tests/test_match_predictions_page.py`
- Test navigation from predictions page (origin=predictions)
- Test navigation from home page (origin=home)
- Test back link URL generation
- Test sort parameter persistence
- Test responsive template rendering
- Test authentication requirement

### Out of Scope
- Unit tests for views (covered in task 1)
- UI/E2E tests with browser automation

### Acceptance Criteria
- Test: Anonymous user redirected to login
- Test: Authenticated user can access page
- Test: 404 for non-existent match
- Test: Page renders with origin=predictions
- Test: Page renders with origin=home
- Test: Back link points to correct origin
- Test: Sort toggle preserves origin parameter
- Test: Invalid origin defaults to predictions
- Test: Invalid sort defaults to match
- Test: Template includes expected elements (header, match info, predictions list)
- All tests pass

### Required Tests
- `test_anonymous_user_redirected`
- `test_authenticated_user_can_access`
- `test_invalid_match_returns_404`
- `test_origin_predictions_renders_correctly`
- `test_origin_home_renders_correctly`
- `test_back_link_to_predictions`
- `test_back_link_to_home`
- `test_sort_toggle_preserves_origin`
- `test_invalid_origin_defaults_to_predictions`
- `test_invalid_sort_defaults_to_match`
- `test_template_contains_required_elements`

---

## Task 8: Update Documentation

- [x] Done

### Goal
Document the new dedicated page feature and navigation patterns.

### Scope
- Update README if user-facing features are documented
- Add comments to MatchPredictionsView explaining origin/sort parameters
- Document icon standardization choices
- Update any developer guides if they exist

### Out of Scope
- Writing new user documentation from scratch
- Creating screenshots or videos

### Acceptance Criteria
- View docstring explains origin and sort parameters
- Icon choices documented in template comments
- Navigation flow documented (predictions → all tips → back to predictions)
- Code comments added for origin parameter handling

### Required Tests
- Manual review of documentation
- Verify docstrings are complete and accurate

---

## Implementation Order

1. Task 1: Refactor MatchPredictionsView (foundation)
2. Task 2: Create Full Page Template (visual component)
3. Task 5: Standardize Icons (before updating navigation)
4. Task 3: Update Predictions Page Navigation
5. Task 4: Add Home Page Navigation
6. Task 6: Remove Bottom Sheet Component
7. Task 7: Add Integration Tests
8. Task 8: Update Documentation

## Dependencies

- Task 2 depends on Task 1 (needs view context)
- Task 3, 4 depend on Task 2 (need template to link to)
- Task 6 depends on Task 3, 4 (links updated before removing bottom sheet)
- Task 7 depends on Task 1-6 (integration tests verify complete implementation)
- Task 8 is final (documents completed work)
