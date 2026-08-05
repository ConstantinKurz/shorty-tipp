# Proposal: Fix Homepage Predictions and Dynamic Ranking

## Summary

Fix three critical issues with the newly implemented home page:
1. **Remove standalone ranking page** – redirect `/ranking/` to home since ranking is now consolidated on the homepage
2. **Add dynamic ranking updates** – implement HTMX polling to auto-refresh ranking when match results change
3. **Fix prediction saving** – enable auto-save functionality for predictions on the homepage (currently only works on predictions page)

## Problem

The home page was recently implemented but has three missing pieces:

### 1. Standalone Ranking Page Still Exists
The `/ranking/` URL still exists as a separate page, even though the design intent was to consolidate all ranking functionality into the home page. This creates confusion and duplication.

### 2. Ranking is Static
The ranking display on the home page never updates without manually reloading the page. When match results change during live games, users must refresh to see updated rankings. This is particularly frustrating during tournament days when multiple matches are in progress.

### 3. Predictions Don't Save from Homepage
The "Next Matches" section on the home page displays match prediction forms, but entering scores does nothing. The POST request is never triggered, so predictions aren't saved. This same prediction form works correctly on the `/predictions/` page.

**Root cause**: The predictions page includes JavaScript that auto-submits forms when both score inputs are filled (with 500ms debounce). This JavaScript is scoped to the predictions page template and not available on the home page.

## Solution

### 1. Redirect Ranking Page to Home
- Update `tipapp/urls.py` to redirect `/ranking/` to home page (`/`)
- Use `RedirectView` with `permanent=False` (302 redirect) since this is a soft migration
- All ranking functionality remains accessible via home page (both compact and expanded views)

### 2. Implement Dynamic Ranking Updates via HTMX
Add HTMX polling to the ranking section that:
- Polls for ranking updates when match results change
- Uses smart interval: frequent during live matches (10s), infrequent otherwise (60s)
- Only updates the ranking content without affecting prediction inputs or expanded/collapsed state
- Leverages existing `get_polling_interval()` logic from predictions app
- Swaps only the ranking tables (compact and full), preserving toggle state

### 3. Enable Auto-Save for Homepage Predictions
Move the auto-submit JavaScript from predictions page to a shared location:
- Extract auto-save logic into `base.html` or a shared JavaScript file
- Make it globally available so both predictions page and home page can use it
- Keep the same behavior: debounced 500ms, triggers HTMX form submit when both scores filled
- Ensure it works with the `prediction-input` class used in `prediction_row.html`

## Non-Goals

- Modifying the ranking calculation logic
- Changing the visual design or layout of the home page
- Adding real-time WebSocket updates (polling is sufficient)
- Optimizing database queries for ranking service
- Changing the prediction form layout or validation
- Adding ranking update notifications or alerts
- Modifying the expanded/collapsed ranking behavior

## Success Criteria

- `/ranking/` URL redirects to home page (`/`)
- No broken links or 404 errors when accessing old ranking URL
- Ranking on home page updates automatically during match days (no manual refresh needed)
- Compact ranking and full ranking both update via HTMX
- Expanded/collapsed state is preserved during HTMX updates
- Prediction forms on home page auto-save when both scores are entered
- Auto-save has 500ms debounce to avoid excessive server requests
- Predictions page continues to work exactly as before
- No console errors or JavaScript conflicts
