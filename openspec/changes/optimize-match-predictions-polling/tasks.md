# Tasks: Optimize Match Predictions Polling with Version Tracking

## Task 1: Extract Match Header Partial ✓

### Goal
Extract the match header section (score card) from the full page template into a reusable partial that can be independently updated via HTMX Out-of-Band swaps. Match the design pattern from `prediction_row.html` for consistency.

### Scope
- Create new file `templates/predictions/partials/match_header.html`
- Extract/create match header following `prediction_row.html` design pattern
- Header contains: time, lock icon, team names, team codes, score display (or `-:-`), match result section, live indicator, round badge
- Use Tailwind classes matching `prediction_row.html` styling
- Wrap extracted section in main template with `<div id="match-header">`
- Use `{% include %}` to render partial in main template
- Ensure partial is self-contained (only needs `match` and `is_locked` in context)

### Out of Scope
- Changing header styling or layout from `prediction_row.html` design
- Adding new information to header
- Modifying predictions content
- URL or view changes

### Acceptance Criteria
- File `templates/predictions/partials/match_header.html` exists
- Contains complete match card header HTML matching `prediction_row.html` design
- Uses same Tailwind classes as `prediction_row.html` (zinc colors, rounded-xl, dark mode support)
- Shows: time, lock icon (if locked), team names, team FIFA codes, score or `-:-`, result section, round badge
- Handles live matches with `🔴 Live` indicator and pulse animation
- Requires only `{{ match }}` and `{{ is_locked }}` in context
- `match_predictions_page.html` includes the partial via `{% include %}`
- Header wrapped with `<div id="match-header">` in main template
- Page renders identically to `prediction_row.html` match display (visual consistency)
- No template syntax errors
- No missing variables in partial

### Required Tests
- Integration test: `test_match_predictions_page_renders_with_extracted_header()`
  - Create match with score
  - Make GET request to `/predictions/match/<id>/all/`
  - Assert response 200
  - Assert HTML contains `<div id="match-header">`
  - Assert header shows correct team names
  - Assert header shows correct team codes
  - Assert header shows correct score
  - Assert header has lock icon if post-kickoff
- Integration test: `test_match_header_shows_dash_when_no_score()`
  - Create match without score (goals_home=None, goals_away=None)
  - Request page
  - Assert header displays `-:-`
- Integration test: `test_match_header_shows_live_indicator()`
  - Create match with status='live'
  - Request page
  - Assert header contains `🔴 Live`

---

## Task 2: Add Version Tracking to Update View ✓

### Goal
Modify `MatchPredictionsUpdateView` to build a version string from match score and return it in an `HX-Trigger` response header.

### Scope
- Add version calculation: `current_version = f"{match.goals_home}:{match.goals_away}"`
- Add `HX-Trigger` header to response with version: `{"version": "1:0"}`
- Parse incoming `version` query parameter: `client_version = request.GET.get("version", "")`
- Store both versions as variables (logic to be added in Task 3)
- No change to rendering logic yet (all requests still render full response)
- Add type hints for new variables

### Out of Scope
- Early exit optimization (Task 3)
- OOB swapping (Task 4)
- Template changes (Task 5)
- Changing polling interval

### Acceptance Criteria
- `MatchPredictionsUpdateView.get()` calculates `current_version` from match score
- Version format: `"{goals_home}:{goals_away}"` (e.g., `"1:0"`, `"None:None"`)
- View reads `version` from query params: `request.GET.get("version", "")`
- Response includes `HX-Trigger` header with JSON: `{"version": "<current_version>"}`
- All existing functionality preserved (still renders predictions on every request)
- Code passes mypy type checking
- Code passes ruff linting

### Required Tests
- Unit test: `test_update_view_returns_version_in_header()`
  - Create match with score 2:1
  - Make GET request to update endpoint
  - Assert response has `HX-Trigger` header
  - Parse header as JSON
  - Assert `version` key equals `"2:1"`
- Unit test: `test_update_view_version_format_with_none_score()`
  - Create match without score (goals_home=None, goals_away=None)
  - Request update endpoint
  - Assert `HX-Trigger` header contains `{"version": "None:None"}`
- Unit test: `test_update_view_reads_client_version_param()`
  - Create match with score 1:0
  - Request with `?version=0:0`
  - Assert view receives and parses version param (verify in logs or add temporary assertion)

---

## Task 3: Implement Early Exit for Unchanged Versions ✓

### Goal
Add optimization logic to `MatchPredictionsUpdateView` that returns an empty response when the match is post-kickoff and the client version matches the current version.

### Scope
- Calculate `is_locked = match.kickoff <= timezone.now()`
- Add conditional check: if `is_locked and client_version == current_version`
- When true: return `HttpResponse("")` (empty body) with `HX-Trigger` header
- When false: continue to full rendering (existing code path)
- Import `timezone` from `django.utils` if not already imported
- Add comment explaining optimization logic

### Out of Scope
- OOB swapping (Task 4)
- Template changes (Task 5)
- Pre-kickoff behavior changes (already renders on all requests)
- Changing response format for full renders

### Acceptance Criteria
- View calculates `is_locked` based on `match.kickoff <= timezone.now()`
- If post-kickoff AND version matches: return empty response
- Empty response has status 200
- Empty response has `HX-Trigger: {"version": "<current_version>"}`
- Empty response has body `b""`
- If pre-kickoff OR version mismatch: render full response (existing behavior)
- No change to rendering logic or output when full render happens
- Code passes mypy type checking

### Required Tests
- Unit test: `test_update_view_returns_empty_when_version_unchanged_post_kickoff()`
  - Create match after kickoff with score 1:0
  - Request with `?version=1:0` (matching version)
  - Assert response status 200
  - Assert response body is empty (`b""`)
  - Assert `HX-Trigger` header contains `{"version": "1:0"}`
- Unit test: `test_update_view_renders_when_version_changed_post_kickoff()`
  - Create match after kickoff with score 2:1
  - Request with `?version=1:0` (old version)
  - Assert response status 200
  - Assert response body is NOT empty (contains HTML)
  - Assert `HX-Trigger` header contains `{"version": "2:1"}`
- Unit test: `test_update_view_always_renders_pre_kickoff()`
  - Create match before kickoff (no score)
  - Request with `?version=None:None` (matching version)
  - Assert response status 200
  - Assert response body is NOT empty (full render)
  - Pre-kickoff predictions can change, so always render
- Unit test: `test_update_view_handles_missing_version_param()`
  - Create match after kickoff with score 1:0
  - Request without version param (client_version = "")
  - Assert full render (mismatch with empty string)

---

## Task 4: Add OOB Header Swap to Response ✓

### Goal
Modify `MatchPredictionsUpdateView` to include the match header as an Out-of-Band swap in full render responses.

### Scope
- Import `render_to_string` from `django.template.loader`
- When full render happens (version mismatch or pre-kickoff):
  - Render `predictions/partials/match_header.html` using `render_to_string()`
  - Render `predictions/partials/match_predictions_content.html` (existing)
  - Combine: `f'<div id="match-header" hx-swap-oob="true">{header_html}</div>{content_html}'`
- Return combined HTML as response body
- Keep `HX-Trigger` header with version
- Empty responses (Task 3) unchanged (no OOB swap needed)

### Out of Scope
- Template structure changes (Task 1 already extracted partial)
- Version tracking logic (Tasks 2-3)
- Changing polling interval or URL params

### Acceptance Criteria
- When full render occurs, response includes both:
  - Match header with OOB directive: `<div id="match-header" hx-swap-oob="true">...</div>`
  - Predictions content: existing HTML
- Header rendered using `match_header.html` partial (from Task 1)
- OOB directive is exactly: `hx-swap-oob="true"`
- Header HTML appears BEFORE predictions content in response
- Empty responses (unchanged version post-kickoff) don't include OOB directive
- Full render response structure: `{oob_header}{content}`
- Code passes mypy type checking

### Required Tests
- Unit test: `test_update_view_includes_oob_header_in_full_render()`
  - Create match after kickoff with score 2:1
  - Request with old version `?version=1:0`
  - Assert response contains `<div id="match-header" hx-swap-oob="true">`
  - Assert response contains match header HTML (team names, score)
  - Assert response contains predictions content HTML
  - Assert header appears before content in response
- Unit test: `test_update_view_oob_header_shows_current_score()`
  - Create match with score 3:2
  - Request with old version
  - Parse response HTML
  - Assert header section contains "3 : 2"
- Unit test: `test_update_view_empty_response_has_no_oob_directive()`
  - Create match after kickoff with score 1:0
  - Request with matching version `?version=1:0`
  - Assert response body is empty
  - Assert response does NOT contain "hx-swap-oob"

---

## Task 5: Update Template with Version Tracking and 30s Polling ✓

### Goal
Update `match_predictions_page.html` to include the version parameter in HTMX polling URL, set explicit 30s polling interval, and add JavaScript to update version from response headers.

### Scope
- Add `hx-trigger="every 30s"` to `#predictions-content` div
- Include version in hx-get URL: `?version={{ current_version }}`
- Add `<script>` block with HTMX event listener:
  - Listen to `htmx:afterOnLoad` on `#predictions-content`
  - Parse `HX-Trigger` header for `version` value
  - Update `hx-get` attribute with new version param
- Ensure script runs after HTMX is loaded
- Keep existing `hx-swap="innerHTML"` behavior

### Out of Scope
- Header extraction (Task 1 already done)
- View changes (Tasks 2-4 already done)
- Changing other polling parameters (swap strategy, etc.)
- Adding loading indicators

### Acceptance Criteria
- `#predictions-content` div has `hx-trigger="every 30s"` attribute
- `hx-get` URL includes `version` query param: `?sort={{ sort_mode }}&version={{ current_version }}`
- JavaScript event listener attached to `htmx:afterOnLoad` event
- Listener filters for `event.detail.elt.id === 'predictions-content'`
- Listener parses `HX-Trigger` response header as JSON
- If `trigger.version` exists, updates `hx-get` URL with new version
- Script handles missing `HX-Trigger` header gracefully (JSON.parse with fallback)
- No JavaScript errors in browser console
- Template still renders correctly without JavaScript (graceful degradation)

### Required Tests
- Integration test: `test_match_predictions_page_has_30s_polling()`
  - Load match predictions page
  - Parse HTML
  - Assert `#predictions-content` has `hx-trigger="every 30s"`
- Integration test: `test_match_predictions_page_includes_version_in_url()`
  - Create match with score 1:0
  - Load page
  - Parse HTML
  - Assert `hx-get` attribute contains `version=1:0`
- Integration test: `test_match_predictions_page_has_version_update_script()`
  - Load page
  - Assert HTML contains `<script>` tag
  - Assert script listens to `htmx:afterOnLoad`
  - Assert script updates `hx-get` attribute
- Manual test: Open page in browser, check console for JavaScript errors

---

## Task 6: Add Initial Version to Full Page View Context ✓

### Goal
Modify `MatchPredictionsView` to include `current_version` in the template context so the template can initialize polling with the correct version.

### Scope
- Update `MatchPredictionsView.get_context_data()` method
- Add `current_version` calculation: `f"{match.goals_home}:{match.goals_away}"`
- Add to context: `context["current_version"] = current_version`
- No other changes to view logic

### Out of Scope
- Update view changes (different view class)
- Template changes (Task 5)
- Polling logic changes

### Acceptance Criteria
- `MatchPredictionsView.get_context_data()` includes `current_version` in context
- Version calculated from match score: `f"{match.goals_home}:{match.goals_away}"`
- Context key is exactly `"current_version"`
- Value type is `str`
- All existing context variables preserved
- Code passes mypy type checking

### Required Tests
- Unit test: `test_match_predictions_view_includes_version_in_context()`
  - Create match with score 2:0
  - Make GET request to `/predictions/match/<id>/all/`
  - Assert response context contains `current_version`
  - Assert `current_version` equals `"2:0"`
- Unit test: `test_match_predictions_view_version_with_none_score()`
  - Create match without score (goals_home=None, goals_away=None)
  - Request page
  - Assert context `current_version` equals `"None:None"`

---

## Task 7: Add Performance and Integration Tests ✓

### Goal
Add comprehensive tests to verify the optimization works end-to-end and measure performance improvements.

### Scope
- Add integration test: full polling cycle simulation
- Add performance test: measure response time difference
- Add test: verify OOB swapping in browser context (if possible)
- Add test: verify version propagation across multiple polls
- Document expected performance gains in test docstrings

### Out of Scope
- Load testing with real users
- Production monitoring setup
- A/B testing infrastructure

### Acceptance Criteria
- Integration test simulates: load page → poll with version → score changes → poll again
- Performance test compares:
  - Response time for version-match empty response (should be <10ms)
  - Response time for full render (baseline)
- Test verifies OOB swap replaces header without re-rendering predictions
- Test verifies version updates correctly after score change
- All tests pass reliably (no flakiness)
- Tests are documented with clear purpose

### Required Tests
- Integration test: `test_full_polling_cycle_with_score_change()`
  - Create match with score 0:0 post-kickoff
  - Load page, extract initial version
  - Poll with version=0:0 → expect empty response
  - Update match score to 1:0
  - Poll with version=0:0 → expect full render with new score
  - Poll with version=1:0 → expect empty response
- Performance test: `test_empty_response_is_fast()`
  - Create match with score 1:0 post-kickoff
  - Measure time for request with matching version
  - Assert response time < 50ms (generous, should be <10ms)
  - Measure time for request with mismatched version (full render)
  - Assert empty response is faster
- Integration test: `test_version_persists_across_multiple_polls()`
  - Poll 10 times with matching version post-kickoff
  - All should return empty responses
  - All should return same version in header

---

## Implementation Order

1. Task 1: Extract Match Header Partial (foundation for OOB)
2. Task 6: Add Initial Version to Full Page View Context (needed for Task 5)
3. Task 2: Add Version Tracking to Update View (foundation for optimization)
4. Task 3: Implement Early Exit for Unchanged Versions (core optimization)
5. Task 4: Add OOB Header Swap to Response (header independence)
6. Task 5: Update Template with Version Tracking and 10s Polling (client-side)
7. Task 7: Add Performance and Integration Tests (verification)

## Success Metrics

After all tasks complete:

- **Server load:** 90% reduction in rendering work during stable match periods
- **Network usage:** 99% reduction in bandwidth during stable periods
- **Response time:** <10ms for version-match responses (was 50-200ms for full render)
- **Polling frequency:** Reduced from implied 1s to explicit 30s (30x fewer requests)
- **User experience:** Unchanged (page still updates automatically, just more efficiently)
