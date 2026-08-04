## Implementation Tasks

### Task 1: Add round filtering method to RankingService ✓

**Status: Complete**

**Goal:** Create service method to calculate rankings filtered by tournament round

**Scope:**
- Add `get_leaderboard_up_to_round(round_code)` method to `RankingService`
- Support filtering by round with inclusive progression (group → r32 → r16 → qf → sf → 3rd → final)
- Return same data structure as existing `get_current_leaderboard()`
- Use Django ORM aggregation with Sum/Count for performance

**Out of Scope:**
- Date-based filtering
- Caching mechanisms
- Changes to snapshot logic

**Acceptance Criteria:**
- Method accepts round_code parameter ('group', 'r32', 'r16', 'qf', 'sf', '3rd', 'final', or None)
- When round_code is None, includes all finished matches (live view)
- When round_code is valid, includes only matches from rounds up to and including that round
- Returns list of dicts with: rank, user_id, username, total_points, exact_match_count, jokers_used
- Applies olympic-style ranking (shared ranks for ties)
- Orders by: total_points DESC, exact_match_count DESC, jokers_used ASC
- Filters only finished matches with non-null points_earned
- Handles edge cases: no matches in round, invalid round code

**Required Tests:**
```python
# scoring/tests/test_ranking_service.py

class TestRankingServiceRoundFiltering:
    def test_get_leaderboard_up_to_round_group_stage(self, db, matches_by_round, predictions):
        """Test filtering by group stage only."""
        leaderboard = RankingService.get_leaderboard_up_to_round('group')
        # Verify only group stage points counted
        
    def test_get_leaderboard_up_to_round_r16(self, db, matches_by_round, predictions):
        """Test filtering includes group + r32 + r16."""
        leaderboard = RankingService.get_leaderboard_up_to_round('r16')
        # Verify cumulative points through r16
        
    def test_get_leaderboard_up_to_round_final(self, db, matches_by_round, predictions):
        """Test final round includes all matches."""
        live = RankingService.get_current_leaderboard()
        final = RankingService.get_leaderboard_up_to_round('final')
        assert live == final
        
    def test_get_leaderboard_up_to_round_none_returns_live(self, db):
        """Test None parameter returns all finished matches."""
        leaderboard = RankingService.get_leaderboard_up_to_round(None)
        # Should match get_current_leaderboard()
        
    def test_get_leaderboard_up_to_round_invalid_code(self, db):
        """Test invalid round code returns live view."""
        leaderboard = RankingService.get_leaderboard_up_to_round('invalid')
        # Should handle gracefully
        
    def test_get_leaderboard_up_to_round_no_finished_matches(self, db, scheduled_matches):
        """Test round with no finished matches returns empty."""
        leaderboard = RankingService.get_leaderboard_up_to_round('group')
        assert leaderboard == []
        
    def test_get_leaderboard_up_to_round_ranking_correctness(self, db, multi_round_data):
        """Test olympic ranking with filtered data."""
        # User A: 50pts group, 30pts r16 = 80 total through r16
        # User B: 40pts group, 50pts r16 = 90 total through r16
        leaderboard = RankingService.get_leaderboard_up_to_round('r16')
        assert leaderboard[0]['username'] == 'user_b'
        assert leaderboard[0]['total_points'] == 90
```

**Files Changed:**
- `scoring/services.py` (add method)
- `scoring/tests/test_ranking_service.py` (new test class)

---

### Task 2: Refactor get_current_leaderboard to use new method ✓

**Status: Complete**

**Goal:** Maintain backward compatibility while reusing round filtering logic

**Scope:**
- Modify `RankingService.get_current_leaderboard()` to call `get_leaderboard_up_to_round(None)`
- Ensure existing behavior unchanged
- Keep method signature identical

**Out of Scope:**
- Changes to method callers
- Changes to return structure

**Acceptance Criteria:**
- `get_current_leaderboard()` returns same results as before refactor
- All existing tests still pass
- No breaking changes to existing code
- Single source of truth for ranking logic

**Required Tests:**
```python
# scoring/tests/test_ranking_service.py

def test_get_current_leaderboard_backward_compatible(db, predictions):
    """Test that refactored method maintains existing behavior."""
    # Should still work exactly as before
    leaderboard = RankingService.get_current_leaderboard()
    assert isinstance(leaderboard, list)
    # Verify structure matches existing expectations
```

**Files Changed:**
- `scoring/services.py` (refactor method)
- `scoring/tests/test_ranking_service.py` (regression test)

---

### Task 3: Add round parameter handling to RankingView ✓

**Status: Complete**

**Goal:** Accept and validate round query parameter in ranking view

**Scope:**
- Modify `RankingView.get_context_data()` to read `round` query parameter
- Validate parameter against allowed values
- Pass validated round to service layer
- Add round metadata to template context

**Out of Scope:**
- Template changes (separate task)
- Champion data enrichment changes

**Acceptance Criteria:**
- View reads `?round=<code>` from request.GET
- Valid round codes: 'group', 'r32', 'r16', 'qf', 'sf', '3rd', 'final'
- Invalid or missing parameter defaults to None (live view)
- Context includes `selected_round` (str or None)
- Context includes `available_rounds` (list of dicts with code and label)
- Leaderboard data reflects round filter

**Required Tests:**
```python
# users/tests/test_views.py

class TestRankingViewRoundFiltering:
    def test_ranking_view_with_valid_round_parameter(self, client, django_user_model):
        """Test view with valid round parameter."""
        user = django_user_model.objects.create_user(username='test', password='pass')
        client.force_login(user)
        
        response = client.get('/ranking/?round=group')
        assert response.status_code == 200
        assert response.context['selected_round'] == 'group'
        
    def test_ranking_view_with_invalid_round_parameter(self, client, django_user_model):
        """Test view ignores invalid round parameter."""
        user = django_user_model.objects.create_user(username='test', password='pass')
        client.force_login(user)
        
        response = client.get('/ranking/?round=invalid')
        assert response.status_code == 200
        assert response.context['selected_round'] is None
        
    def test_ranking_view_without_round_parameter(self, client, django_user_model):
        """Test default view without parameter."""
        user = django_user_model.objects.create_user(username='test', password='pass')
        client.force_login(user)
        
        response = client.get('/ranking/')
        assert response.status_code == 200
        assert response.context['selected_round'] is None
        
    def test_ranking_view_available_rounds_in_context(self, client, django_user_model):
        """Test available_rounds provided to template."""
        user = django_user_model.objects.create_user(username='test', password='pass')
        client.force_login(user)
        
        response = client.get('/ranking/')
        assert 'available_rounds' in response.context
        assert len(response.context['available_rounds']) == 7
```

**Files Changed:**
- `users/views.py` (modify `RankingView.get_context_data()`)
- `users/tests/test_views.py` (add test class)

---

### Task 4: Add round filter UI to ranking template ✓

**Status: Complete**

**Goal:** Add horizontal button bar for round filtering with HTMX updates

**Scope:**
- Add round filter buttons above ranking table
- Style buttons to match existing app aesthetic (zinc/emerald colors)
- Highlight selected round button
- Use HTMX for partial page updates
- Add indicator text when viewing filtered round
- Wrap ranking table in `#ranking-content` div for HTMX target

**Out of Scope:**
- Dropdown or tab-based UI (using buttons)
- Mobile-specific layout changes
- Animations or transitions beyond CSS

**Acceptance Criteria:**
- Button bar appears above ranking table
- Buttons: "Live", "Gruppe", "Achtelfinale", "Viertelfinale", "Halbfinale", "3. Platz", "Finale"
- Selected button has emerald background, others have zinc background
- Clicking button updates ranking without full page reload (HTMX)
- URL updates to reflect filter (browser back button works)
- Shows indicator text "Rangliste nach: [Round]" when filtered
- Desktop and mobile layouts work correctly
- Dark mode colors applied correctly
- Buttons wrap on small screens

**Template Structure:**
```html
<!-- Round filter controls -->
<div class="mb-6 flex flex-wrap gap-2 justify-center">
    <button hx-get="{% url 'ranking' %}" ...>Live</button>
    {% for round in available_rounds %}
        <button hx-get="{% url 'ranking' %}?round={{ round.code }}" ...>
            {{ round.label }}
        </button>
    {% endfor %}
</div>

<!-- Ranking content (HTMX swap target) -->
<div id="ranking-content">
    {% if selected_round %}
        <div class="text-center mb-4 text-sm text-zinc-500">
            Rangliste nach: <span class="font-semibold">{{ selected_round|round_label }}</span>
        </div>
    {% endif %}
    
    <!-- Existing table markup -->
</div>
```

**Required Manual Testing:**
- [ ] Click each round button and verify ranking updates
- [ ] Verify URL changes in address bar
- [ ] Test browser back button functionality
- [ ] Test in light and dark mode
- [ ] Test on mobile screen size (buttons wrap)
- [ ] Verify HTMX swap only updates content, not full page
- [ ] Test with network throttling (loading states)

**Files Changed:**
- `templates/ranking.html` (add filter UI)

---

### Task 5: Add German round label template filter ✓

**Status: Complete**

**Goal:** Create template filter to display German round names

**Scope:**
- Create template filter `round_label` to convert round codes to German labels
- Register filter in `user_tags` templatetag module
- Handle all valid round codes
- Return code unchanged if invalid

**Out of Scope:**
- Internationalization (i18n) framework
- Multiple language support
- Admin interface changes

**Acceptance Criteria:**
- Filter converts: group→Gruppe, r32→Achtelfinale, r16→Achtelfinale, qf→Viertelfinale, sf→Halbfinale, 3rd→3. Platz, final→Finale
- Invalid codes return unchanged
- Filter registered and available in templates
- Can be used as: `{{ round_code|round_label }}`

**Required Tests:**
```python
# users/tests/test_templatetags.py

def test_round_label_filter_valid_codes():
    """Test round_label filter converts codes to German labels."""
    from users.templatetags.user_tags import round_label
    
    assert round_label('group') == 'Gruppe'
    assert round_label('r32') == 'Achtelfinale'
    assert round_label('r16') == 'Achtelfinale'
    assert round_label('qf') == 'Viertelfinale'
    assert round_label('sf') == 'Halbfinale'
    assert round_label('3rd') == '3. Platz'
    assert round_label('final') == 'Finale'
    
def test_round_label_filter_invalid_code():
    """Test round_label filter handles invalid codes."""
    from users.templatetags.user_tags import round_label
    
    assert round_label('invalid') == 'invalid'
    assert round_label('') == ''
    assert round_label(None) == ''
```

**Files Changed:**
- `users/templatetags/user_tags.py` (add filter)
- `users/tests/test_templatetags.py` (new or add to existing)

---

### Task 6: Integration testing and documentation ✓

**Status: Complete**

**Goal:** Verify end-to-end functionality and update documentation

**Scope:**
- Create integration test covering full user flow
- Test with realistic multi-round dataset
- Verify ranking progression (points increase from group → final)
- Update README or docs if needed
- Manual testing checklist

**Out of Scope:**
- Performance benchmarking
- Load testing
- API documentation

**Acceptance Criteria:**
- Integration test creates matches across all rounds
- Test scores predictions and verifies filtered rankings
- Test verifies round progression (group < r16 < final in points)
- Manual testing passes on dev server
- All unit tests pass
- No regressions in existing functionality

**Required Tests:**
```python
# scoring/tests/test_integration.py

def test_round_based_ranking_full_flow(db, django_user_model):
    """Integration test for round-based ranking filtering."""
    # Setup: Create teams, matches across rounds, users, predictions
    # Score matches in different rounds
    # Verify:
    # - Leaderboard for 'group' shows only group points
    # - Leaderboard for 'r16' shows cumulative points
    # - Leaderboard for None (live) shows all points
    # - Rankings change appropriately based on round
    # - Olympic ranking maintained in all views
```

**Manual Testing Checklist:**
- [ ] Start dev server
- [ ] Create test data with matches in multiple rounds
- [ ] Score some predictions
- [ ] Visit /ranking/
- [ ] Click each round filter button
- [ ] Verify rankings update correctly
- [ ] Check browser console for errors
- [ ] Test HTMX behavior (no full page reload)
- [ ] Test URL parameter directly: /ranking/?round=group
- [ ] Test browser back/forward navigation
- [ ] Test with no finished matches (empty state)
- [ ] Test dark mode rendering

**Files Changed:**
- `scoring/tests/test_integration.py` (add test)
- `README.md` or `docs/` (if documentation update needed)

---

## Implementation Order

1. **Task 1** → Service layer foundation
2. **Task 2** → Refactor for backward compatibility
3. **Task 3** → View layer parameter handling
4. **Task 5** → Template filter (needed by Task 4)
5. **Task 4** → UI implementation
6. **Task 6** → Integration and verification

## Estimated Effort

- Task 1: 2-3 hours (service logic + tests)
- Task 2: 30 minutes (refactor + regression test)
- Task 3: 1-2 hours (view changes + tests)
- Task 4: 2-3 hours (template + styling + manual testing)
- Task 5: 30 minutes (filter + tests)
- Task 6: 1-2 hours (integration test + manual testing)

**Total: ~8-12 hours**

## Dependencies

- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 4 depends on Task 3 and Task 5
- Task 6 depends on all previous tasks

## Risk Assessment

**Low Risk:**
- No database changes
- No breaking changes to existing API
- HTMX already in use in project
- Points are pre-calculated (performance not a concern)

**Medium Risk:**
- Template changes might affect mobile layout (requires testing)
- HTMX behavior needs browser compatibility check

**Mitigation:**
- Thorough testing across devices
- Graceful degradation (buttons work without HTMX via full reload)
- Keep existing non-filtered view as default
