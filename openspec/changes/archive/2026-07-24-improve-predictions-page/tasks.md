# Tasks: Improve Predictions Page

## Phase 1: Test Data Management Command

### Task 1.1: Create Management Command Structure

**Goal**: Set up the Django management command skeleton

**Scope**:
- Create `predictions/management/` directory structure
- Create `predictions/management/commands/` directory
- Create `create_wm2026_testdata.py` command file
- Add `__init__.py` files for proper Python packaging

**Out of Scope**:
- Data generation logic (covered in later tasks)
- Command options parsing (covered in Task 1.2)

**Acceptance Criteria**:
- [x] Directory structure exists: `predictions/management/commands/`
- [x] File exists: `predictions/management/commands/create_wm2026_testdata.py`
- [x] All directories have `__init__.py` files
- [x] Command can be discovered by Django: `python manage.py help create_wm2026_testdata`

**Required Tests**:
- Test: Command is discoverable via `python manage.py help`
- Test: Command can be imported without errors

---

### Task 1.2: Implement Command Options and Base Structure

**Goal**: Add command options, help text, and transaction handling

**Scope**:
- Add `--clear` option to delete existing test data
- Add `--users N` option for number of test users (default: 8)
- Add help text and command description
- Implement transaction wrapper for atomic data creation
- Add progress logging

**Out of Scope**:
- Actual data creation (covered in Tasks 1.3-1.6)

**Acceptance Criteria**:
- [x] Command accepts `--clear` option
- [x] Command accepts `--users N` option with default value of 8
- [x] Help text is clear and informative
- [x] Command uses `@transaction.atomic` decorator
- [x] Progress messages printed to stdout
- [x] Errors printed to stderr

**Required Tests**:
- Test: `--clear` option is recognized
- Test: `--users` option accepts integer value
- Test: Invalid `--users` value raises CommandError
- Test: Transaction rollback on error (no partial data)

---

### Task 1.3: Implement Team and Match Creation

**Goal**: Generate 48 teams and 104 matches with correct structure

**Scope**:
- Create 48 teams (16 groups × 3 teams)
- Team naming: "Team A1", "Team A2", ..., "Team P3"
- Create 48 group stage matches (round-robin within each group)
- Create 56 knockout stage matches (R32=32, R16=16, QF=8, SF=2, Third=1, Final=1)
- Assign realistic kickoff times:
  - Group stage: 2026-06-11 to 2026-06-25 (15 days)
  - R32: 2026-06-27 to 2026-06-30
  - R16: 2026-07-03 to 2026-07-06
  - QF: 2026-07-09 to 2026-07-10
  - SF + Third: 2026-07-14 to 2026-07-15
  - Final: 2026-07-19
- Kickoff times distributed: 13:00, 16:00, 19:00, 22:00 (local time)
- Mark ~20 group stage matches as finished with results (0-5 goals each team)

**Out of Scope**:
- Predictions (covered in Task 1.5)
- Real WM 2026 schedule (simplified dates)
- Team logos or detailed metadata

**Acceptance Criteria**:
- [x] Exactly 48 teams created
- [x] Team names follow pattern: "Team {Group}{Number}"
- [x] Exactly 48 group stage matches created (round='group')
- [x] Exactly 32 R32 matches created (round='r32')
- [x] Exactly 16 R16 matches created (round='r16')
- [x] Exactly 8 QF matches created (round='qf')
- [x] Exactly 4 semi-final stage matches (round='sf', '3rd', 'final')
- [x] Total: 108 matches (spec said 104 but math requires 108 with SF stage)
- [x] Each group has exactly 3 matches (A vs B, A vs C, B vs C pattern)
- [x] Kickoff times span correct date ranges
- [x] ~20 group stage matches have status='finished' and results
- [x] Finished matches have `goals_home` and `goals_away` set (0-5 range)

**Required Tests**:
- Test: Exactly 48 teams created
- Test: Team names match pattern
- Test: Exactly 104 matches created
- Test: Group stage has 48 matches
- Test: Each group has 3 matches
- Test: Round-robin pattern in each group (all teams play each other once)
- Test: Knockouts have correct match counts (32+16+8+4)
- Test: Kickoff times are in correct date ranges
- Test: ~20 finished matches exist
- Test: Finished matches have valid results (goals >= 0)
- Test: `--clear` deletes matches and teams before creating

---

### Task 1.4: Implement User Creation

**Goal**: Create test users (tippers) with consistent credentials

**Scope**:
- Create 6-10 test users (configurable via `--users` option)
- Usernames: "tipper1", "tipper2", ..., "tipperN"
- Emails: "tipper1@example.com", etc.
- Password: "testpass123" (same for all, for easy testing)
- Set all users as active and staff=False
- Create user profiles if Profile model exists

**Out of Scope**:
- Predictions (covered in Task 1.5)
- User permissions beyond default
- Email verification (set as verified)

**Acceptance Criteria**:
- [x] Number of users matches `--users` option (default: 8)
- [x] Usernames follow pattern: "tipper{N}"
- [x] Emails follow pattern: "tipper{N}@example.com"
- [x] All users have password "testpass123"
- [x] All users are active (is_active=True)
- [x] All users are not staff (is_staff=False)
- [x] User profiles created if Profile model exists

**Required Tests**:
- Test: Correct number of users created
- Test: Usernames match pattern
- Test: Emails are valid and unique
- Test: Users can authenticate with "testpass123"
- Test: `--users 10` creates 10 users
- Test: `--clear` deletes test users before creating

---

### Task 1.5: Implement Prediction Creation with Joker Rules

**Goal**: Generate realistic predictions for each user following joker limits

**Scope**:
- For each user, create predictions for 70-90% of matches (randomized coverage)
- Prediction patterns per user:
  - tipper1: Optimistic (high scores, 3-5 goals per team)
  - tipper2: Pessimistic (low scores, 0-2 goals per team)
  - tipper3: Chaotic (random scores, 0-5 goals)
  - tipper4: Realistic (balanced, 0-3 goals)
  - tipper5: Home-team bias (home team +1 goal advantage)
  - tipper6+: Random balanced patterns
- **Group stage limit**: Exactly 36 predictions per user for group stage
- **Joker distribution** (critical):
  - Group stage: 0 jokers (no jokers allowed)
  - R32: Assign 3 random jokers per user
  - R16: Assign 3 random jokers per user
  - QF: Assign 2 random jokers per user
  - SF/Final/Third: Assign 2 jokers total per user (combined pool)
- For finished matches: Vary prediction accuracy:
  - ~20% exact matches (same score, max points)
  - ~30% tendency matches (correct winner/draw, partial points)
  - ~50% misses (wrong tendency, no points)

**Out of Scope**:
- Scoring calculation (covered in Task 1.6)
- Prediction history/audit log
- User-specific strategies beyond listed patterns

**Acceptance Criteria**:
- [x] Each user has predictions for 70-90% of matches
- [x] Each user has exactly 36 group stage predictions
- [x] Joker counts per user:
  - [x] 0 jokers in group stage
  - [x] 3 jokers in R32 (if user has R32 predictions)
  - [x] 3 jokers in R16 (if user has R16 predictions)
  - [x] 2 jokers in QF (if user has QF predictions)
  - [x] 2 jokers total in SF/Final/Third combined
- [x] Prediction patterns match user profiles (optimistic, pessimistic, etc.)
- [x] For finished matches, predictions vary in accuracy (~20% exact, ~30% tendency, ~50% miss)
- [x] No joker violations (service should enforce, but command should not create invalid data)

**Required Tests**:
- Test: Each user has predictions
- Test: Each user has exactly 36 group stage predictions
- Test: Joker count for tipper1 in R32 is 3 (if applicable)
- Test: Joker count for tipper1 in group stage is 0
- Test: Combined joker count for SF/Final/Third is 2 per user
- Test: tipper1 predictions are optimistic (high scores)
- Test: tipper2 predictions are pessimistic (low scores)
- Test: tipper5 predictions show home-team bias
- Test: Prediction accuracy distribution for finished matches (~20/30/50 split)
- Test: No user exceeds group stage limit (36)
- Test: No user exceeds joker limits per round

---

### Task 1.6: Implement Scoring Calculation

**Goal**: Calculate and store points for predictions on finished matches

**Scope**:
- Run `PredictionScoringService.score_predictions()` for each user
- Calculate `points_earned` for all predictions on finished matches
- Save results to `MatchPrediction.points_earned` field
- Verify scoring rules match `docs/rules/wm2026-rules.md`

**Out of Scope**:
- Ranking calculation (separate feature)
- Historical scoring (only current state)

**Acceptance Criteria**:
- [x] All predictions for finished matches have `points_earned` calculated
- [x] Scoring follows rules:
  - [x] Exact score: base_points × joker_multiplier (2 or 3)
  - [x] Correct goal difference: base_points × joker_multiplier
  - [x] Correct tendency: base_points × joker_multiplier
  - [x] Wrong tendency: 0 points
- [x] Joker multiplier applied correctly (×2 for regular, ×3 if both goal difference and tendency correct)
- [x] Unfinished matches have `points_earned` as None or 0

**Required Tests**:
- Test: Finished matches with predictions have points calculated
- Test: Exact score match earns correct points
- Test: Correct tendency earns correct points
- Test: Wrong tendency earns 0 points
- Test: Joker multiplier applied correctly
- Test: Unfinished matches have no points yet

---

### Task 1.7: Add Command Validation and Summary Output

**Goal**: Validate created data and print summary statistics

**Scope**:
- After data creation, validate:
  - Match counts per round
  - User count
  - Prediction counts per user
  - Joker distribution per user per round
  - Group stage prediction limit compliance
- Print summary to stdout:
  - Total matches created
  - Total users created
  - Total predictions created
  - Joker distribution summary
  - Finished matches count
  - Scored predictions count
- Raise `CommandError` if validation fails

**Out of Scope**:
- Detailed error messages for each validation (single error is sufficient)

**Acceptance Criteria**:
- [x] Validation checks all counts
- [x] Validation checks joker limits
- [x] Validation checks group stage limit (36 per user)
- [x] Summary printed to stdout with clear formatting
- [x] Summary includes all key statistics
- [x] CommandError raised if validation fails

**Required Tests**:
- Test: Valid data passes validation
- Test: Summary output includes all statistics
- Test: Invalid joker count triggers validation error
- Test: Invalid group stage count triggers validation error

---

## Phase 2: Predictions Page Frontend Improvements

### Task 2.1: Remove Stage Tabs and Create Scrollable List

**Goal**: Convert tab-based navigation to single scrollable list

**Scope**:
- Remove any existing tab UI components from `prediction_list.html`
- Keep match rows grouped by date
- Ensure full list is scrollable vertically
- Keep existing HTMX auto-save functionality intact

**Out of Scope**:
- Filtering (covered in Task 2.2)
- Auto-scroll (covered in Task 2.3)
- Live updates (covered in Task 2.4)

**Acceptance Criteria**:
- [x] No tab navigation visible
- [x] All matches visible in single scrollable list
- [x] Matches grouped by date with date headers
- [x] Vertical scrolling works smoothly
- [x] Existing prediction forms still work (auto-save)
- [x] No JavaScript errors in console

**Required Tests**:
- Test: GET /predictions/ returns 200
- Test: Template renders all matches
- Test: Matches ordered by kickoff
- Test: Date grouping visible in HTML
- Test: Auto-save still functional (existing tests should pass)

---

### Task 2.2: Add Stage Filter UI

**Goal**: Implement filter dropdown for stage selection

**Scope**:
- Add filter button in page header: "🔽 Filter"
- Add dropdown menu with stage options:
  - All
  - Group Stage
  - Round of 32
  - Round of 16
  - Quarter-final
  - Semi-final
  - Final
- Add JavaScript to show/hide dropdown on button click
- Add JavaScript to filter matches by `data-match-stage` attribute
- Update URL parameter `?stage=<stage>` on filter selection
- Persist filter on page reload (read `?stage=` from URL)
- Close dropdown on selection or outside click

**Out of Scope**:
- Server-side filtering (all matches always sent, filtered client-side)
- Advanced filters (by team, date range, etc.)

**Acceptance Criteria**:
- [x] Filter button visible in page header
- [x] Dropdown menu appears on button click
- [x] Dropdown contains all stage options
- [x] Clicking stage option filters matches (hides non-matching)
- [x] URL parameter `?stage=<stage>` updated on selection
- [x] Page reload with `?stage=group` applies group stage filter
- [x] Dropdown closes after selection
- [x] Dropdown closes on outside click
- [x] Filter button shows active filter: "🔽 Filter (Gruppenphase)"

**Required Tests**:
- Test: Filter button rendered in template
- Test: Dropdown contains all stage options
- Test: JavaScript applies filter correctly (check match visibility)
- Test: URL parameter set correctly on filter selection
- Test: Page reload with `?stage=gs` applies filter
- Test: Filter state persists across page reloads

---

### Task 2.3: Add Data Attributes to Match Rows

**Goal**: Add `data-match-stage` and `data-kickoff-timestamp` attributes for filtering and auto-scroll

**Scope**:
- Update `prediction_row.html` template
- Add `data-match-stage="{{ match.round }}"` to match row div
- Add `data-kickoff-timestamp="{{ match.kickoff|date:'U' }}"` to match row div (Unix timestamp)
- Ensure attributes are present on all match rows

**Out of Scope**:
- JavaScript functionality (covered in Tasks 2.2 and 2.4)

**Acceptance Criteria**:
- [x] All match rows have `data-match-stage` attribute
- [x] `data-match-stage` value matches match round (group, r32, r16, qf, sf, final, 3rd)
- [x] All match rows have `data-kickoff-timestamp` attribute
- [x] `data-kickoff-timestamp` is valid Unix timestamp (seconds since epoch)

**Required Tests**:
- Test: Rendered HTML contains `data-match-stage` attribute
- Test: `data-match-stage` value is correct for group stage match
- Test: `data-match-stage` value is correct for knockout match
- Test: Rendered HTML contains `data-kickoff-timestamp` attribute
- Test: `data-kickoff-timestamp` is integer (Unix timestamp)

---

### Task 2.4: Implement Auto-scroll to Nearest Match

**Goal**: Auto-scroll to nearest upcoming match on page load

**Scope**:
- Add JavaScript (inline or external file) to run on `DOMContentLoaded`
- Find all match rows with `data-kickoff-timestamp` attribute
- Compare kickoff timestamps to current time (`Date.now()`)
- Identify nearest future match (smallest positive difference)
- If no future matches, scroll to last match
- Smooth scroll to match with 100px offset (for header)

**Out of Scope**:
- Auto-scroll on filter change (only on page load)
- Keyboard navigation enhancements

**Acceptance Criteria**:
- [x] JavaScript runs on page load
- [x] Nearest upcoming match is identified correctly
- [x] Page scrolls smoothly to nearest match
- [x] Scroll offset accounts for header (100px)
- [x] If all matches finished, scrolls to last match
- [x] If no matches, no scroll action (no error)
- [x] No console errors

**Required Tests**:
- Test: JavaScript runs without errors
- Test: Nearest match calculation correct (mock timestamps)
- Test: Scroll to last match if all matches finished
- Test: No error if no matches exist
- Unit test: `findNearestMatch()` function (if extracted)

---

### Task 2.5: Implement Live Update Endpoint (Polling)

**Goal**: Create HTMX polling endpoint to fetch updated match results

**Scope**:
- Create `PredictionUpdatesView` in `predictions/views.py`
- Inherit from `LoginRequiredMixin` and `View`
- Implement `get()` method:
  - Accept `last_update` timestamp from query parameter
  - Query matches updated since `last_update` (filter by `updated_at` field)
  - Filter for finished matches only
  - Get user's predictions for updated matches
  - Render `prediction_row.html` for each updated match
  - Add `hx-swap-oob="true"` attribute to each row
  - Return HTML fragments
  - Return empty response if no updates
- Add URL route: `path("updates/", PredictionUpdatesView.as_view(), name="prediction-updates")`

**Out of Scope**:
- WebSocket implementation
- Push notifications
- Polling interval configuration UI

**Acceptance Criteria**:
- [x] View accepts GET requests
- [x] View requires authentication
- [x] View returns empty response if no finished matches
- [x] View returns HTML fragments for finished matches
- [x] Each fragment has `hx-swap-oob="true"` attribute
- [x] View returns correct match rows for user's predictions

**Required Tests**:
- Test: GET /predictions/updates/ requires authentication
- Test: GET /predictions/updates/ returns 200
- Test: No updates returns empty response
- Test: Updated match returns HTML fragment with OOB attribute
- Test: Multiple updated matches return multiple fragments
- Test: Only user's predictions returned (not other users)
- Test: Invalid `last_update` timestamp handled gracefully (defaults to 24h ago)

---

### Task 2.6: Add HTMX Polling to Template

**Goal**: Integrate HTMX polling into predictions page template

**Scope**:
- Add HTMX polling div to `prediction_list.html`:
  ```html
  <div hx-get="{% url 'prediction-updates' %}" 
       hx-trigger="every 60s" 
       hx-swap="none"
       hx-vals='{"last_update": "{{ last_update_timestamp }}"}'>
  </div>
  ```
- Pass `last_update_timestamp` from view context (current time as Unix timestamp)
- Ensure HTMX library is loaded (CDN or static file)

**Out of Scope**:
- Configurable polling interval (hardcoded 60s)
- Stop polling on user inactivity

**Acceptance Criteria**:
- [x] Polling div present in template
- [x] `hx-get` points to correct URL
- [x] `hx-trigger` set to "every 60s"
- [x] `hx-swap` set to "none" (OOB handles updates)
- [x] HTMX library loaded (via base template)
- [x] Polling starts automatically on page load

**Required Tests**:
- Test: Polling div rendered in HTML
- Test: HTMX attributes present and correct
- Test: `last_update_timestamp` in context
- Manual test: Polling fires every 60 seconds (check Network tab)
- Manual test: Updated matches swap in-place without page reload

---

### Task 2.7: Add Tailwind Styling for Filter UI

**Goal**: Style filter button and dropdown with Tailwind CSS

**Scope**:
- Style filter button: Size, color, hover states
- Style dropdown: Positioning, width, shadow, border
- Style dropdown options: Hover states, active state
- Ensure responsive design (mobile-friendly)
- Match existing page styling (dark/light mode compatibility)

**Out of Scope**:
- Complete design system overhaul
- Animation/transition effects (optional enhancement)

**Acceptance Criteria**:
- [x] Filter button has consistent styling with page theme
- [x] Dropdown positioned correctly (below button)
- [x] Dropdown has shadow and border for visibility
- [x] Dropdown options have hover states
- [x] Active filter highlighted in button text
- [x] Responsive design works on mobile (full-width dropdown if needed)
- [x] Dark/light mode compatible

**Required Tests**:
- Manual test: Filter button looks good on desktop
- Manual test: Filter button looks good on mobile
- Manual test: Dropdown positioned correctly
- Manual test: Hover states work
- Manual test: Active filter highlighted

---

## Phase 3: Testing and Quality Assurance

### Task 3.1: Write Management Command Tests

**Goal**: Comprehensive tests for `create_wm2026_testdata` command

**Scope**:
- Create `predictions/tests/test_management_commands.py`
- Tests covered in Task 1.3-1.7 acceptance criteria
- Use `call_command()` to invoke command in tests
- Use `@pytest.mark.django_db` decorator
- Test both success and failure scenarios

**Out of Scope**:
- Performance tests (command runtime)
- Concurrency tests

**Acceptance Criteria**:
- [ ] All tests from Phase 1 tasks implemented
- [ ] Test file exists and runs successfully
- [ ] All tests pass
- [ ] Test coverage > 90% for command code
- [ ] Tests run in isolation (each test cleans up data)

**Required Tests**:
- See acceptance criteria from Tasks 1.3-1.7

---

### Task 3.2: Write Frontend JavaScript Tests

**Goal**: Test auto-scroll and filter JavaScript functionality

**Scope**:
- Create JavaScript test file (e.g., using Jest or QUnit)
- Test auto-scroll logic:
  - Nearest match calculation
  - Scroll to last match fallback
  - No error if no matches
- Test filter logic:
  - Match visibility toggling
  - URL parameter updates
  - Filter persistence on reload

**Out of Scope**:
- End-to-end tests (covered in Task 3.4)
- Cross-browser testing (assume modern browsers)

**Acceptance Criteria**:
- [ ] Test file exists for JavaScript code
- [ ] Tests cover auto-scroll logic
- [ ] Tests cover filter logic
- [ ] All tests pass
- [ ] Test coverage > 80% for JavaScript code

**Required Tests**:
- Test: `findNearestMatch()` returns correct match
- Test: `findNearestMatch()` returns last match if all finished
- Test: `applyFilter('gs')` hides non-group-stage matches
- Test: `applyFilter('all')` shows all matches
- Test: URL parameter updated on filter change

---

### Task 3.3: Write View Tests for Polling Endpoint

**Goal**: Test `PredictionUpdatesView` behavior

**Scope**:
- Create tests in `predictions/tests/test_views.py`
- Tests covered in Task 2.5 acceptance criteria
- Use `pytest-django` fixtures
- Mock match updates by changing `updated_at` timestamp

**Out of Scope**:
- Load testing for polling endpoint

**Acceptance Criteria**:
- [ ] All tests from Task 2.5 implemented
- [ ] Tests cover authentication requirement
- [ ] Tests cover empty response case
- [ ] Tests cover updated match response
- [ ] Tests cover HTMX OOB attribute
- [ ] All tests pass

**Required Tests**:
- See acceptance criteria from Task 2.5

---

### Task 3.4: Manual End-to-End Testing

**Goal**: Verify full user flow with real browser interaction

**Scope**:
- Run `python manage.py create_wm2026_testdata --clear`
- Start development server
- Open predictions page in browser
- Manually verify:
  - All matches visible
  - Auto-scroll to nearest match works
  - Filter dropdown works
  - Filtering hides/shows correct matches
  - URL parameter persists on reload
  - Polling fires every 60 seconds (check Network tab)
  - Updating a match result shows in frontend without reload (simulate with admin)

**Out of Scope**:
- Automated E2E tests (future enhancement)

**Acceptance Criteria**:
- [ ] Management command runs successfully
- [ ] Predictions page loads without errors
- [ ] Auto-scroll works on page load
- [ ] Filter works for all stage options
- [ ] Filter persists on page reload
- [ ] Polling fires every 60 seconds
- [ ] Match result update appears without page reload
- [ ] No console errors
- [ ] No visual glitches

**Required Tests**:
- Manual checklist completed

---

### Task 3.5: Code Quality and Linting

**Goal**: Ensure code quality standards

**Scope**:
- Run `ruff check predictions/` and fix issues
- Run `ruff format predictions/`
- Run `mypy predictions/` and fix type errors
- Add docstrings to all public classes and methods
- Remove unused imports
- Verify no hardcoded values (use constants)

**Out of Scope**:
- Refactoring existing code unrelated to this change

**Acceptance Criteria**:
- [x] `ruff check` passes with no errors
- [x] `ruff format` applied to all files
- [x] `mypy` passes with no errors
- [x] All public classes have docstrings
- [x] All public methods have docstrings
- [x] No unused imports
- [x] Constants used for magic numbers (e.g., GROUP_STAGE_LIMIT)

**Required Tests**:
- Run `ruff check predictions/`
- Run `mypy predictions/`
- Manual review of docstrings

---

### Task 3.6: Update Documentation

**Goal**: Document new management command and frontend features

**Scope**:
- Add section to README.md:
  - How to create test data
  - Command options explanation
  - What data is created
- Add section to developer docs:
  - Filter implementation details
  - Polling mechanism explanation
  - Auto-scroll behavior

**Out of Scope**:
- User-facing documentation (no end-users yet)

**Acceptance Criteria**:
- [x] README.md updated with test data section
- [x] Command usage examples provided
- [x] Developer docs updated with technical details
- [x] Documentation is clear and accurate

**Required Tests**:
- Manual review of documentation
- Verify examples work as described

---

## Phase 4: Integration and Final Verification

### Task 4.1: Run Full Test Suite

**Goal**: Verify all tests pass, including existing tests

**Scope**:
- Run `pytest` with full test suite
- Verify all new tests pass
- Verify all existing tests still pass
- Check test coverage for new code (> 85%)

**Out of Scope**:
- Adding tests for unrelated code

**Acceptance Criteria**:
- [ ] All new tests pass
- [ ] All existing tests pass
- [ ] No test failures or errors
- [ ] Test coverage > 85% for new code
- [ ] Test summary printed to console

**Required Tests**:
- Run `pytest -v`
- Run `pytest --cov=predictions`

---

### Task 4.2: Create Test Data on Dev Environment

**Goal**: Verify command works in real environment

**Scope**:
- Run `python manage.py create_wm2026_testdata --clear` on dev server
- Verify data created correctly
- Check match counts, user counts, prediction counts
- Verify joker distribution
- Verify scoring calculated

**Out of Scope**:
- Running on production (test data only)

**Acceptance Criteria**:
- [ ] Command completes without errors
- [ ] Summary output shows correct counts
- [ ] Data visible in Django admin
- [ ] Predictions page shows all data
- [ ] Joker limits enforced correctly

**Required Tests**:
- Manual verification of data in admin
- Manual verification of predictions page

---

### Task 4.3: Final Manual Testing Checklist

**Goal**: Complete end-to-end manual testing

**Scope**:
- Open predictions page as authenticated user
- Verify auto-scroll to nearest match
- Verify filter works for each stage
- Verify filter persists on reload
- Verify polling updates match results (simulate with admin)
- Test on multiple screen sizes (desktop, tablet, mobile)
- Test on multiple browsers (Chrome, Firefox, Safari)
- Verify no console errors
- Verify no visual glitches

**Out of Scope**:
- Automated E2E tests

**Acceptance Criteria**:
- [ ] Auto-scroll works on page load
- [ ] Filter works for all stages
- [ ] Filter persists across reloads
- [ ] Polling updates matches without reload
- [ ] Responsive design works on all screen sizes
- [ ] Works on all major browsers
- [ ] No console errors
- [ ] No visual glitches

**Required Tests**:
- Manual checklist completed

---

### Task 4.4: Commit and Document Changes

**Goal**: Commit changes with clear messages and update changelog

**Scope**:
- Create commit(s) with descriptive messages
- Follow conventional commits format:
  - `feat: add WM 2026 test data management command`
  - `feat: improve predictions page with filters and auto-scroll`
  - `feat: add live match result polling`
- Update CHANGELOG.md with new features
- Tag commit if appropriate

**Out of Scope**:
- Creating release (future step)

**Acceptance Criteria**:
- [ ] Commits follow conventional commits format
- [ ] Commit messages are descriptive
- [ ] CHANGELOG.md updated
- [ ] No sensitive data in commits
- [ ] All files committed (no WIP files left)

**Required Tests**:
- Review commit messages
- Review CHANGELOG.md

---

## Summary

**Total Tasks**: 26 tasks across 4 phases

**Estimated Effort**: 
- Phase 1: ~2-3 days (test data command)
- Phase 2: ~2-3 days (frontend improvements)
- Phase 3: ~1-2 days (testing)
- Phase 4: ~0.5-1 day (integration and verification)
- **Total**: ~6-9 days

**Dependencies**:
- Phase 2 can start after Phase 1 Task 1.3 (matches created)
- Phase 3 can run in parallel with Phase 2
- Phase 4 requires all previous phases complete

**Critical Path**:
- Task 1.3 → Task 1.5 → Task 1.6 (data creation pipeline)
- Task 2.1 → Task 2.2 → Task 2.4 (frontend UX flow)
- Task 2.5 → Task 2.6 (polling implementation)
