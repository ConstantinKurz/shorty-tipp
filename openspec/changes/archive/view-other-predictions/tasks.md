# Tasks: View Other Predictions

## Task 1: Add MatchPredictionsView

### Goal
Create the view that returns predictions for a match with Olympic-style ranking.

### Scope
- Add `MatchPredictionsView` to `predictions/views.py`
- Return predictions list partial
- Show all active users (even without predictions)
- Calculate Olympic ranking (shared ranks for ties, skip after tie)
- Order by points earned (desc), then has_predicted, then username

### Out of Scope
- Templates
- URL routing
- JavaScript

### Acceptance Criteria
- [x] View returns 404 for non-existent match
- [x] View requires authentication
- [x] Returns predictions partial with all active users
- [x] Users without predictions shown with status
- [x] Olympic-style rank calculation
- [x] Predictions include user, rank, score, points, joker status

### Required Tests
- Test anonymous user redirected
- Test 404 for invalid match ID
- Test predictions response returned
- Test predictions ordered correctly
- Test Olympic ranking with ties
- Test rank skipping after ties

---

## Task 2: Add URL route for match predictions

### Goal
Wire up the view to a URL.

### Scope
- Add path to `predictions/urls.py`
- URL pattern: `match/<int:match_id>/predictions/`
- Name: `match-predictions`

### Out of Scope
- View logic
- Templates

### Acceptance Criteria
- [x] URL resolves to MatchPredictionsView
- [x] URL accepts integer match_id parameter
- [x] Reverse lookup works with match ID

### Required Tests
- Test URL resolution
- Test reverse lookup

---

## Task 3: Create bottom sheet container in base template

### Goal
Add the global bottom sheet HTML structure.

### Scope
- Add backdrop div with click handler
- Add bottom sheet container with slide-up styling
- Add handle bar and content container
- Position fixed, z-index layering
- Hidden by default (translate-y-full)

### Out of Scope
- JavaScript logic
- Content partials
- Match row modifications

### Acceptance Criteria
- [x] Bottom sheet container exists in DOM
- [x] Backdrop covers full screen
- [x] Sheet has rounded top corners
- [x] Max height 70vh
- [x] Content area scrollable
- [x] Hidden by default

### Required Tests
- Visual inspection

---

## Task 4: Create match predictions partial template

### Goal
Build the template showing all predictions for a match with Olympic-style ranking.

### Scope
- Create `templates/predictions/partials/match_predictions.html`
- Sticky header with match info
- List of predictions with rank, user, score, points
- Olympic ranking (shared ranks for ties, skip after tie)
- All users shown, even without predictions
- Current user row highlighted
- Joker indicator
- Summary count at bottom

### Out of Scope
- View logic
- JavaScript
- Locked state template

### Acceptance Criteria
- [x] Shows match teams and result
- [x] Lists all users (active users)
- [x] Shows Olympic-style rank numbers (1, 2, 2, 4...)
- [x] Users without predictions shown as "Kein Tipp"
- [x] Current user highlighted with different background
- [x] Joker shown with star icon
- [x] Points shown if scored
- [x] Dark mode support

### Required Tests
- Visual test with mock data
- Test empty state
- Test Olympic ranking with ties
- Test rank skipping after ties

---

## Task 5: Add bottom sheet JavaScript

### Goal
Implement open/close logic for the bottom sheet.

### Scope
- `openBottomSheet()` function
- `closeBottomSheet()` function
- Backdrop click to close
- ESC key to close
- Swipe down gesture to close (touch)
- Body scroll lock when open

### Out of Scope
- HTMX integration
- Templates

### Acceptance Criteria
- [x] Sheet slides up smoothly when opened
- [x] Sheet slides down when closed
- [x] Backdrop tap closes sheet
- [x] ESC key closes sheet
- [x] Swipe down closes sheet on mobile
- [x] Body scroll locked when open

### Required Tests
- Manual test on mobile and desktop

---

## Task 6: Make match rows clickable with HTMX

### Goal
Connect match row clicks to load predictions.

### Scope
- Update `prediction_row.html`
- Add `hx-get` for predictions URL
- Add `hx-target` to bottom sheet content
- Add `hx-on::after-request` to open sheet
- Add cursor-pointer class
- Prevent click on form inputs from triggering

### Out of Scope
- View logic
- Bottom sheet templates

### Acceptance Criteria
- [x] Clicking match row loads predictions
- [x] Bottom sheet opens after content loads
- [x] Input fields don't trigger sheet
- [x] Save/delete buttons don't trigger sheet
- [x] Joker button doesn't trigger sheet

### Required Tests
- Manual test of click behavior
- Verify form interactions still work

---

## Task 7: Mobile polish and testing

### Goal
Ensure smooth experience on mobile devices.

### Scope
- Test on various screen sizes (320px - 768px)
- Verify swipe gesture works reliably
- Check touch target sizes (min 44px)
- Test with many predictions (scrolling)
- Handle bar visual feedback

### Out of Scope
- Desktop-specific styling
- New features

### Acceptance Criteria
- [x] Works on 320px width screens
- [x] Swipe to close is reliable
- [x] All tap targets ≥ 44px
- [x] Scrolling works with many predictions
- [x] No layout shifts on open/close
- [x] Animations are smooth (no jank)

### Required Tests
- Manual test on mobile device or emulator

---

## Implementation Order

1. Task 1 (view) - backend logic
2. Task 2 (URL) - wire up endpoint
3. Task 3 (bottom sheet container) - HTML structure
4. Task 4 (predictions partial) - main content
5. Task 5 (JavaScript) - interactivity
6. Task 6 (HTMX integration) - connect it all
7. Task 7 (mobile polish) - refinement

## Estimated Effort

| Task | Effort |
|------|--------|
| Task 1 | ~30 min |
| Task 2 | ~10 min |
| Task 3 | ~20 min |
| Task 4 | ~30 min |
| Task 5 | ~30 min |
| Task 6 | ~30 min |
| Task 7 | ~30 min |
| **Total** | **~2.5 hours** |
