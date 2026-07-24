# Tasks: Match Phase Navigation

## Task 1: Add phase statistics to view context

### Goal
Calculate and provide prediction/joker counts per tournament phase to the template.

### Scope
- Add `get_phase_stats()` helper function to `predictions/views.py`
- Extend `PredictionListView.get_context_data()` to include `phase_stats`
- Include: prediction count, joker count, total matches, joker limit per phase

### Out of Scope
- Template changes
- JavaScript changes
- URL routing changes

### Acceptance Criteria
- [x] `phase_stats` dict available in template context
- [x] Stats include all 7 phases: group, r32, r16, qf, sf, 3rd, final
- [x] Each phase has: predictions, jokers, total_matches, joker_limit
- [x] Group stage has joker_limit of 0

### Required Tests
- Unit test for `get_phase_stats()` with various prediction scenarios
- Test that context contains `phase_stats` in view

---

## Task 2: Create sticky phase navigation component

### Goal
Build the sticky navigation bar with phase tabs and progress display.

### Scope
- Create `predictions/partials/phase_nav.html` partial template
- Add sticky CSS using Tailwind utility classes
- Phase tabs: Gruppe, R32, R16, VF, HF, 3., Finale
- Progress display area (content filled by JS)
- Embed `phase_stats` as JSON data attribute

### Out of Scope
- JavaScript interactivity
- Match filtering logic
- View changes

### Acceptance Criteria
- [x] Sticky navigation visible at top when scrolling
- [x] All 7 phase tabs rendered
- [x] Progress display area present
- [x] `phase_stats` accessible as JSON in DOM
- [x] Horizontal scroll on mobile (overflow-x-auto)
- [x] Proper z-index to stay above content

### Required Tests
- Visual inspection on desktop and mobile widths
- Confirm sticky positioning works

---

## Task 3: Implement phase switching JavaScript

### Goal
Enable client-side phase switching with URL persistence.

### Scope
- Read `phase_stats` from DOM
- Handle tab click events
- Filter matches by showing/hiding based on `data-match-stage`
- Update date header visibility
- Update progress display (Tipps count, Joker count)
- Sync with URL `?phase=` parameter
- Restore phase from URL on page load

### Out of Scope
- Server-side filtering
- New API endpoints
- Auto-scroll to matches

### Acceptance Criteria
- [x] Clicking tab switches to that phase
- [x] Only matches of selected phase visible
- [x] Date headers hidden if no visible matches
- [x] Progress shows correct counts for active phase
- [x] Joker display hidden for group stage
- [x] URL parameter updates on phase change
- [x] Page load respects URL parameter
- [x] Active tab visually highlighted

### Required Tests
- Manual test: click through all phases
- Test URL parameter persistence
- Test invalid URL parameter defaults to 'group'

---

## Task 4: Update prediction list template structure

### Goal
Integrate phase navigation into the main predictions template.

### Scope
- Include `phase_nav.html` partial at top of content
- Remove old filter dropdown component
- Ensure match rows have `data-match-stage` attribute
- Ensure date headers/groups have proper data attributes for JS
- Set default phase to 'group'

### Out of Scope
- Changing prediction row partial
- Modifying HTMX behavior
- Changing view logic

### Acceptance Criteria
- [x] Phase navigation rendered in template
- [x] Old filter dropdown removed
- [x] All match rows have `data-match-stage` attribute
- [x] Page loads with group phase active by default
- [x] HTMX polling still works after phase switch

### Required Tests
- Integration test: page loads successfully
- Test phase switching preserves HTMX functionality

---

## Task 5: Handle HTMX updates with phase filter

### Goal
Ensure HTMX row updates respect active phase filter.

### Scope
- After HTMX swaps new row content, re-apply phase filter
- Listen for `htmx:afterSwap` event
- Update phase stats after prediction save/delete/joker toggle
- Refresh progress display

### Out of Scope
- Changing HTMX endpoints
- Server-side stat recalculation via HTMX

### Acceptance Criteria
- [x] Saving prediction keeps phase filter active
- [x] Deleting prediction updates visible count
- [x] Toggling joker updates joker count in progress
- [x] Newly rendered rows respect current phase filter

### Required Tests
- Test: save prediction, verify filter maintained
- Test: delete prediction, verify count decrements
- Test: toggle joker, verify joker count updates

---

## Task 6: Mobile responsiveness and polish

### Goal
Ensure phase navigation works smoothly on mobile devices.

### Scope
- Horizontal scrollable tabs with momentum scroll
- Auto-scroll active tab into view
- Touch-friendly tap targets (min 44px)
- Compact progress display on mobile
- Dark mode support

### Out of Scope
- Native mobile app
- Offline support

### Acceptance Criteria
- [x] Tabs scrollable horizontally on narrow screens
- [x] Active tab scrolls into view when switched
- [x] Tap targets ≥44px for accessibility
- [x] Dark mode colors consistent
- [x] No layout shifts on phase switch
- [x] Perceived latency < 100ms for phase switch

### Required Tests
- Manual test on mobile viewport (375px width)
- Test touch scrolling of tabs
- Verify dark mode styling

---

## Implementation Order

1. Task 1 (view context) - foundation
2. Task 2 (sticky nav component) - visual structure
3. Task 4 (template integration) - connect components
4. Task 3 (JavaScript) - interactivity
5. Task 5 (HTMX handling) - dynamic updates
6. Task 6 (mobile polish) - refinement

## Estimated Effort

| Task | Effort |
|------|--------|
| Task 1 | ~30 min |
| Task 2 | ~45 min |
| Task 3 | ~1 hour |
| Task 4 | ~30 min |
| Task 5 | ~45 min |
| Task 6 | ~45 min |
| **Total** | **~4.5 hours** |
