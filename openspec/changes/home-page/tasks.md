# Tasks: Home Page with Compact Ranking and Next Matches

## Task 1: Create HomeView in scoring app

### Goal
Implement the view that gathers all data for the home page: user rank, compact/full leaderboard, and next 3 matches. This view REPLACES the standalone ranking page.

### Scope
- Add `HomeView` class to `scoring/views.py`
- Inherit from `LoginRequiredMixin` and `TemplateView`
- Implement `get_context_data()` method
- Handle `?round=<code>` query param for HTMX round filtering (same as old RankingView)
- Query full leaderboard using `RankingService.get_leaderboard(round_code=selected_round)`
- Find user's entry and extract nearby entries (5 total: user + 4 around them)
- Query next 3 upcoming matches (`kickoff > now`)
- Get user's predictions for those matches
- Calculate joker availability for each match
- Build match data dictionaries (match, prediction, form, lock status, joker info)
- Pass all context to template including `selected_round`

### Out of Scope
- URL configuration (separate task)
- Template creation (separate task)
- Modifying RankingService
- New database models or migrations

### Acceptance Criteria
- [x] `HomeView` class exists in `scoring/views.py`
- [x] View requires login
- [x] Handles `?round=<code>` query param for filtering
- [x] Context includes `selected_round` (None for Live, or round code)
- [x] Context includes `user_rank_entry` (user's ranking data)
- [x] Context includes `compact_leaderboard` (5 entries: user + nearby)
- [x] Context includes `full_leaderboard` (all users, filtered by round if param present)
- [x] Context includes `available_rounds` (for filter in expanded state)
- [x] Context includes `matches_data` (up to 3 upcoming matches with full data)
- [x] Match data includes: match, prediction, form, is_locked, joker info
- [x] Handles edge cases: user at top/bottom, fewer than 5 users
- [x] No errors when user has no ranking entry yet
- [x] HTMX requests (with HX-Request header) work correctly

### Required Tests
- Test authenticated user can access view
- Test anonymous user redirected to login
- Test context contains all required keys
- Test `?round=group` filters leaderboard correctly
- Test `selected_round` in context matches query param
- Test compact_leaderboard contains exactly 5 entries (or fewer if not enough users)
- Test user's entry is included in compact_leaderboard
- Test matches_data contains at most 3 upcoming matches
- Test matches ordered by kickoff ascending
- Test edge case: user at rank 1
- Test edge case: user at last rank
- Test edge case: only 3 users in ranking

---

## Task 2: Create home page template

### Goal
Build the main home.html template with hero rank card, compact/full ranking sections, and next matches preview.

### Scope
- Create `templates/home.html`
- Extend `base.html`
- Add hero card displaying user's rank, points, and champion
- Add ranking section with expand/collapse button
- Include compact ranking div (default visible)
- Include full ranking div with `#ranking-content` HTMX swap target (default hidden)
- Full ranking must be IDENTICAL to old ranking page (all columns, filter, HTMX)
- Add next matches section with header and link to full predictions
- Loop through `matches_data` and include `prediction_row.html` partial
- Add client-side JavaScript for expand/collapse toggle
- Use modern Tailwind styling (gradients, shadows, rounded corners)
- Ensure responsive design (mobile and desktop)

### Out of Scope
- Creating compact_ranking.html partial (separate task)
- Modifying prediction_row.html
- Modifying ranking_content.html
- Backend view logic

### Acceptance Criteria
- [x] Template extends `base.html`
- [x] Hero card shows rank number, total points, champion flag
- [x] Hero card has gradient background (emerald to sky)
- [x] Ranking section has header and toggle button (arrow icon)
- [x] Compact ranking div has id `compact-ranking`
- [x] Full ranking div has id `full-ranking` and nested `#ranking-content` (initially hidden)
- [x] Full ranking includes complete `ranking_content.html` partial (all columns + filter)
- [x] HTMX round filter buttons swap `#ranking-content` only
- [x] JavaScript toggles visibility and rotates arrow icon
- [x] Next matches section shows up to 3 matches
- [x] Each match uses `prediction_row.html` include
- [x] Empty state shown when no upcoming matches
- [x] Link to full predictions page present
- [x] Design is clean, modern, and matches existing style
- [x] Page is responsive (works on mobile)

### Required Tests
- Render template with full context (manual/integration test)
- Verify all context variables are used
- Test expand/collapse JavaScript in browser
- Test responsive layout on mobile device
- Verify match tipping works via HTMX

---

## Task 3: Create compact ranking partial template

### Goal
Build the compact_ranking.html partial that displays 5 ranking entries with minimal columns.

### Scope
- Create `templates/partials/compact_ranking.html`
- Use `user_tags` template tag library
- Render desktop table with columns: Rang, Name, Champion, Punkte
- Render mobile card layout
- Highlight current user's row (different background color, "(Du)" label)
- Use flag emoji for champion display
- Handle empty champion gracefully
- Match styling from existing ranking_content.html

### Out of Scope
- Full ranking table (already exists in ranking_content.html)
- Round filter display
- Backend logic for determining nearby entries
- JavaScript for expand/collapse

### Acceptance Criteria
- [x] Partial template created at `templates/partials/compact_ranking.html`
- [x] Loads `user_tags` template tag library
- [x] Desktop table shows: Rang, Name, Champion, Punkte (4 columns only)
- [x] Mobile shows compact cards
- [x] Current user's row highlighted (emerald background)
- [x] Current user's name includes "(Du)" indicator
- [x] Champion shown as flag emoji
- [x] Empty champion shows "–"
- [x] Styling consistent with ranking_content.html
- [x] No exact match count or joker columns (keep it minimal)

### Required Tests
- Render partial with compact_leaderboard context
- Verify current user is highlighted
- Verify all 5 entries are displayed
- Test mobile layout renders correctly

---

## Task 4: Configure URLs and login redirect

### Goal
Add URL route for the home page, redirect old ranking URL, and update login redirect.

### Scope
- Update `tipapp/urls.py` to add home route (`/`)
- Import `HomeView` from `scoring.views`
- Import `RedirectView` from `django.views.generic`
- Add URL pattern: `path('', HomeView.as_view(), name='home')`
- Change ranking URL to redirect: `path('ranking/', RedirectView.as_view(url='/', permanent=False), name='ranking')`
- Update `LOGIN_REDIRECT_URL` in `tipapp/settings/base.py` to `'/'`
- Ensure URL doesn't conflict with existing routes

### Out of Scope
- Creating new URL namespace
- Modifying predictions or ranking URLs
- Authentication view changes

### Acceptance Criteria
- [x] `tipapp/urls.py` includes route for `/` pointing to `HomeView`
- [x] Route is named `'home'`
- [x] `/ranking/` URL redirects to `/` (302 redirect)
- [x] Redirect is non-permanent (permanent=False)
- [x] `LOGIN_REDIRECT_URL` set to `'/'` in base settings
- [x] Home page accessible at root URL
- [x] After login, user redirected to home page
- [x] No conflicts with other URL patterns

### Required Tests
- Test GET request to `/` returns 200 for authenticated user
- Test GET request to `/` redirects to login for anonymous user
- Test GET request to `/ranking/` redirects to `/`
- Test `reverse('ranking')` still works (now redirects)
- Test login redirects to `/` after success
- Test home URL reverse resolves correctly: `reverse('home')`

---

## Task 5: Update navigation links

### Goal
Update existing page templates to remove standalone ranking links and add home page links.

### Scope
- Add home page link to navigation in `base.html` (if nav exists)
- Update predictions page to link back to home
- Remove or replace standalone "Ranking" nav links (since ranking now in home)
- Update user settings page to link back to home
- Update any template footers that link to ranking
- Use consistent "Home" or "🏠 Home" label
- Ensure current page is highlighted in navigation

### Out of Scope
- Creating a complex navigation component
- Adding breadcrumbs
- Mobile menu implementation (unless already exists)

### Acceptance Criteria
- [x] Navigation includes link to home page (`{% url 'home' %}`)
- [x] Link visible on predictions and settings pages
- [x] Standalone ranking nav links removed (ranking now in home)
- [x] Current page highlighted in navigation (if applicable)
- [x] Link accessible and functional
- [x] Styling consistent with existing design
- [x] No broken links to old `/ranking/` page

### Required Tests
- Navigate from home → predictions → home
- Navigate from home → settings → home
- Verify no standalone ranking nav links exist
- Verify old ranking template (if kept) has updated nav
- Verify links work on mobile layout

---

## Task 6: Handle edge cases and error states

### Goal
Ensure the home page handles edge cases gracefully: no ranking data, no upcoming matches, user not in ranking.

### Scope
- Add checks in `HomeView` for when user has no ranking entry
- Show placeholder or friendly message if user not yet ranked
- Handle case where fewer than 5 users exist in ranking
- Handle case where user is at rank 1 or last rank (adjust nearby entries)
- Show empty state when no upcoming matches exist
- Ensure no crashes when `compact_leaderboard` is empty
- Add defensive checks for None values

### Out of Scope
- Creating new ranking entries automatically
- Generating fake data for testing
- Complex error logging

### Acceptance Criteria
- [x] If user not in ranking, show placeholder in hero card
- [x] If fewer than 5 users, show all available users in compact view
- [x] If user at rank 1, show user + 4 below (or all available below)
- [x] If user at last rank, show user + 4 above (or all available above)
- [x] If no upcoming matches, show "Keine anstehenden Spiele" message
- [x] If no leaderboard data, show empty state
- [x] No crashes or 500 errors in any edge case

### Required Tests
- Test view with user not in ranking (new user)
- Test view with only 1 user in ranking
- Test view with user at rank 1
- Test view with user at last rank
- Test view with no upcoming matches
- Test view with empty leaderboard
- Verify all edge cases render without errors

---

## Task 7: Add HTMX integration for live match updates (optional enhancement)

### Goal
Enable live updates for match predictions on the home page without page reload, similar to the predictions page.

### Scope
- Reuse existing HTMX polling from predictions page
- Add polling trigger for match updates on home page
- Ensure match row partials update correctly
- Use same polling interval logic as predictions view
- No new backend endpoints needed (reuse existing)

### Out of Scope
- Creating new HTMX endpoints
- Modifying predictions views
- Real-time WebSocket updates

### Acceptance Criteria
- [ ] Match rows on home page update automatically
- [ ] Polling interval matches predictions page behavior
- [ ] Locked matches update when they become locked
- [ ] HTMX updates don't cause page flicker
- [ ] Updates only affect match section, not entire page

### Required Tests
- Manually verify match updates work
- Test polling starts on page load
- Test locked state updates correctly
- Verify performance (no excessive requests)

---

## Task 8: Style and polish the home page

### Goal
Refine the visual design to match modern fintech apps (Trade Republic, Revolut) with clean aesthetics and smooth animations.

### Scope
- Fine-tune hero card gradient and typography
- Add smooth transition for expand/collapse animation
- Ensure consistent spacing and padding throughout
- Add hover states to interactive elements
- Verify dark mode styling
- Test responsive breakpoints
- Add loading states if needed
- Ensure accessibility (focus states, ARIA labels)

### Out of Scope
- Complete redesign of existing components
- Adding complex animations or interactions
- Implementing skeleton loaders
- Adding illustrations or custom graphics

### Acceptance Criteria
- [x] Hero card has smooth gradient (emerald to sky)
- [x] Expand/collapse arrow rotates smoothly (CSS transition)
- [x] Spacing is consistent (gap-6 between sections)
- [x] Hover states present on buttons and links
- [x] Dark mode looks good (tested manually)
- [x] Responsive on mobile (320px to tablet)
- [x] Focus states visible for keyboard navigation
- [x] ARIA label on expand/collapse button
- [x] Overall aesthetic matches Trade Republic/Revolut style

### Required Tests
- Manual browser testing (Chrome, Safari, Firefox)
- Test dark mode toggle
- Test mobile responsiveness (iPhone, Android)
- Test keyboard navigation
- Test with screen reader (basic check)
- Verify animations are smooth (60fps)

---

## Summary

**Total tasks**: 8

**Implementation order**:
1. Task 1: Create HomeView
2. Task 3: Create compact ranking partial
3. Task 2: Create home template
4. Task 4: Configure URLs
5. Task 5: Add navigation links
6. Task 6: Handle edge cases
7. Task 8: Style and polish
8. Task 7: HTMX integration (optional)

**Estimated effort**: 4-6 hours

**Dependencies**:
- Existing `RankingService`
- Existing `PredictionForm` and match row partial
- HTMX and Tailwind CSS already in use

**Testing strategy**:
- Unit tests for view logic
- Template rendering tests
- Integration tests for URL routing
- Manual browser testing for UI/UX
- Edge case scenario tests
