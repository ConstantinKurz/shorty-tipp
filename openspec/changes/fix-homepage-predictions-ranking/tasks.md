# Tasks: Fix Homepage Predictions and Dynamic Ranking

## Task 1: Redirect standalone ranking page to home

### Goal
Remove the standalone `/ranking/` page by redirecting it to the home page where all ranking functionality is now consolidated.

### Scope
- Update `tipapp/urls.py` to add redirect from `/ranking/` to `/`
- Use `RedirectView` with `permanent=False` (HTTP 302)
- Preserve URL name `ranking` for backward compatibility
- Test redirect works correctly

### Out of Scope
- Removing ranking view class (already not used)
- Updating navigation links (none exist that reference /ranking/)
- Modifying home page layout or functionality

### Acceptance Criteria
- [x] Accessing `/ranking/` redirects to `/` (home page)
- [x] Redirect uses HTTP 302 (temporary redirect), not 301
- [x] URL name `ranking` still resolves to the redirect view
- [x] No 404 errors when accessing `/ranking/`
- [x] Home page displays ranking section correctly after redirect

### Required Tests
- [x] Test GET request to `/ranking/` returns 302 status code
- [x] Test redirect Location header points to `/`
- [x] Test accessing redirected URL loads home page successfully
- [x] Test URL reverse lookup: `reverse('ranking')` returns `/ranking/`

---

## Task 2: Add dynamic ranking updates via HTMX polling

### Goal
Enable automatic ranking updates on the home page so users see live changes when match results are entered, without manual page refresh.

### Scope
- Create `RankingUpdatesView` in `scoring/views.py` (HTMX endpoint)
- Create `scoring/urls.py` with URL pattern for ranking updates
- Update `tipapp/urls.py` to include scoring URLs
- Add `ranking_interval` to `HomeView` context
- Create `templates/partials/ranking_updates.html` (OOB swap partial)
- Update `templates/home.html` with HTMX polling div
- Add `hx-preserve` attributes to ranking sections
- Reuse `get_polling_interval()` logic from predictions app

### Out of Scope
- Modifying ranking calculation logic
- Changing polling interval thresholds (keep 10s/60s)
- Adding WebSocket real-time updates
- Optimizing database queries in RankingService

### Acceptance Criteria
- [x] `RankingUpdatesView` exists in `scoring/views.py`
- [x] View requires login (`LoginRequiredMixin`)
- [x] View returns `ranking_updates.html` partial with OOB swaps
- [x] View preserves `?round=<code>` query param filtering
- [x] View computes both compact and full leaderboards
- [x] View enriches leaderboard with champion data (same as HomeView)
- [x] `scoring/urls.py` created with `ranking-updates` URL pattern
- [x] `tipapp/urls.py` includes `scoring.urls`
- [x] `HomeView` context includes `ranking_interval` (10 or 60 seconds)
- [x] `templates/partials/ranking_updates.html` created
- [x] Partial uses `hx-swap-oob="true"` for multi-target updates
- [x] `templates/home.html` includes hidden HTMX polling div
- [x] Polling div triggers every `{{ ranking_interval }}s`
- [ ] `#compact-ranking` and `#ranking-content` have `hx-preserve` attribute
- [ ] Ranking updates during live matches (observed manually)
- [ ] Expanded/collapsed state preserved during updates
- [ ] Round filter preserved during updates

### Required Tests
- [x] Test `RankingUpdatesView` requires authentication
- [x] Test view returns 200 with HX-Request header
- [x] Test view returns correct context keys
- [x] Test `?round=group` filters leaderboard correctly
- [x] Test compact leaderboard contains user's entry
- [x] Test full leaderboard includes all users
- [x] Test view handles user not in ranking (no error)
- [x] Test `get_polling_interval()` returns 10s during live matches
- [x] Test `get_polling_interval()` returns 60s when no live matches
- [ ] Integration test: verify HTMX polling triggers view

---

## Task 3: Enable prediction auto-save on home page

### Goal
Make prediction forms on the home page auto-submit when both scores are filled, matching the behavior on the predictions page.

### Scope
- Extract auto-save JavaScript from `predictions/prediction_list.html`
- Move JavaScript to `templates/base.html` (global availability)
- Remove duplicate auto-save code from `prediction_list.html`
- Test auto-save works on both home page and predictions page
- Verify debounce behavior (500ms delay)

### Out of Scope
- Changing auto-save timing or debounce duration
- Modifying prediction form validation
- Adding manual submit buttons
- Changing HTMX swap behavior

### Acceptance Criteria
- [x] Auto-save JavaScript moved from `prediction_list.html` to `base.html`
- [x] JavaScript placed before closing `</body>` tag (after HTMX loads)
- [x] Uses event delegation (`document.addEventListener('input', ...)`)
- [x] Targets `.prediction-input` class elements
- [x] Checks both `predicted_goals_home` and `predicted_goals_away` filled
- [x] 500ms debounce before submission
- [x] Triggers HTMX form submit via `htmx.trigger(form, 'submit')`
- [x] Duplicate code removed from `prediction_list.html`
- [ ] Predictions page still works (all existing functionality preserved)
- [ ] Home page predictions now auto-save
- [ ] No JavaScript console errors
- [ ] No duplicate form submissions

### Required Tests
- Browser test: Enter score on home page → prediction saves after 500ms
- Browser test: Enter score on predictions page → still saves after 500ms
- Browser test: Clear input before 500ms → form not submitted
- Browser test: Enter home score only → form not submitted
- Browser test: Rapid typing → only one submission after last keystroke
- Test predictions page JavaScript still functional (phase nav, etc.)
- Test no console errors on home page load
- Test no console errors on predictions page load

---

## Task 4: Manual testing and verification

### Goal
Verify all three fixes work correctly together through comprehensive manual testing.

### Scope
- Test ranking redirect
- Test dynamic ranking updates during live matches
- Test prediction auto-save on home page
- Test no regressions on predictions page
- Test edge cases (expanded state, round filters, rapid input)

### Out of Scope
- Automated browser tests (separate task if needed)
- Performance testing
- Load testing

### Acceptance Criteria
- [ ] Navigate to `/ranking/` → redirects to `/` correctly
- [ ] Home page loads without errors
- [ ] Ranking section displays correctly (compact and full)
- [ ] Toggle expand/collapse → state preserved during HTMX updates
- [ ] Filter by round → ranking updates preserve selected round
- [ ] During live match, ranking updates every 10 seconds (observed)
- [ ] When no live matches, ranking updates every 60 seconds (observed)
- [ ] Enter prediction on home page → saves automatically after 500ms
- [ ] Enter prediction on predictions page → still saves automatically
- [ ] Rapid typing in prediction input → debounce works (one submit)
- [ ] Locked match on home page → input disabled, no save attempted
- [ ] Delete prediction on home page → works correctly
- [ ] Toggle joker on home page → works correctly
- [ ] No JavaScript console errors on any page
- [ ] No broken layouts or styling issues
- [ ] Browser back button works correctly (no duplicate history entries)

### Required Tests
This task is primarily manual verification. Document findings in implementation notes.

**Test Scenarios**:
1. Ranking redirect flow
2. Dynamic updates during live match
3. Dynamic updates with no live matches
4. Ranking updates with round filter active
5. Ranking updates while expanded
6. Prediction auto-save on home page
7. Prediction auto-save on predictions page
8. Debounce behavior with rapid typing
9. Cross-browser compatibility (Chrome, Firefox, Safari)

---

## Implementation Order

1. **Task 1** (Redirect) - Simplest, no dependencies
2. **Task 3** (Auto-save) - Independent, high user value
3. **Task 2** (Dynamic ranking) - Most complex, depends on understanding polling
4. **Task 4** (Manual testing) - After all code changes complete

## Dependencies

- Task 1: None (standalone)
- Task 2: Requires HomeView already implemented (✓ done)
- Task 3: Requires prediction_row.html partial (✓ done)
- Task 4: Requires Tasks 1-3 complete
