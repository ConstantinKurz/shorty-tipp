# Proposal: HTMX Auto-Updates for Match Predictions Page

## Summary

Add HTMX polling to the dedicated match predictions page (`/predictions/match/<id>/all/`) so it automatically refreshes when predictions or rankings change, without requiring manual page reload.

## Problem

The dedicated "Alle Tipps" page currently shows a static snapshot of all predictions for a match. When users are viewing this page:

- New predictions submitted by other users don't appear
- Changes to existing predictions (edits, deletions) aren't reflected
- Ranking changes (match points, total points) don't update
- Match results entered by admins don't trigger recalculation
- Points earned calculations remain stale

This creates a poor user experience during active matches or when multiple users are tipping simultaneously. Users must manually reload the page to see current data, which breaks the flow of comparing predictions and checking rankings.

The main predictions list page (`/predictions/`) already has HTMX polling that handles live updates elegantly. The match predictions page should provide the same real-time experience.

## Solution

### HTMX Polling Implementation

Add HTMX polling to `match_predictions_page.html` that:

1. **Polls for changes** at dynamic intervals (fast during matches, slow otherwise)
2. **Detects updates** to predictions, rankings, or match results
3. **Swaps content** only when changes are detected (partial DOM updates)
4. **Preserves scroll position** so users aren't disrupted
5. **Adjusts polling rate** based on match activity (same logic as predictions list)

### Polling Endpoint

Create a new view endpoint: `MatchPredictionsUpdateView`

- URL: `/predictions/match/<id>/updates/`
- Returns: HTML partial with updated predictions list
- Parameters: `sort` (match/total), `from` (origin tracking)
- Logic: Re-queries predictions, recalculates rankings, renders partial template

### Partial Template

Extract the predictions list section into a reusable partial:

- File: `templates/predictions/partials/match_predictions_content.html`
- Contains: sort toggle + predictions list
- Used by: both full page and update endpoint
- Ensures: identical markup in both contexts

### Polling Configuration

Reuse existing polling logic from `predictions.views`:

- Active matches: 1 second interval (during kickoff + 160 minutes)
- Idle periods: 60 seconds interval
- Polling interval passed to template context
- JavaScript can dynamically adjust interval via HX-Trigger header

### User Experience

**During active matches:**
- Page polls every 1 second for near-real-time updates
- Users see new predictions appear immediately
- Rankings recalculate as predictions come in
- Match results update when admin enters final score

**During idle periods:**
- Page polls every 60 seconds (light server load)
- Still catches late predictions or manual edits
- Minimal network overhead

**Visual feedback:**
- No loading spinners (updates are seamless)
- Smooth transitions (no flash/flicker)
- Current user's prediction stays highlighted
- Sort mode and scroll position preserved

## Non-Goals

- Real-time WebSocket connections (polling is sufficient)
- Push notifications when predictions change
- Live chat or commenting features
- Optimistic UI updates before server confirmation
- Differential/delta updates (full list refresh is acceptable)
- Caching or service workers for offline support

## Success Criteria

- Match predictions page auto-updates without manual reload
- Polling interval adapts to match activity (1s active, 60s idle)
- New predictions appear within polling interval
- Rankings recalculate correctly on each update
- Scroll position maintained during updates
- Sort toggle preserved during updates
- No JavaScript errors in browser console
- Server load remains reasonable (same as predictions list)
- Users can view predictions during active matches with current data

## Impact

### User Benefits
- Better experience when watching live matches
- No need to refresh page to see latest predictions
- More engaging during group viewing sessions
- Confidence that data is current

### Technical Benefits
- Reuses existing polling infrastructure
- Consistent behavior with predictions list page
- No new backend dependencies
- Graceful degradation if JavaScript disabled

### Risks
- Slightly increased server load (minimal, same pattern as existing page)
- Potential scroll jump if not handled carefully (mitigated by HTMX swap)
- User editing their own prediction might conflict (not applicable - edits happen on different page)
