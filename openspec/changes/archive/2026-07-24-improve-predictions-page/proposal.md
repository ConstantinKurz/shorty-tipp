# Improve Predictions Page

## Summary

Enhance the predictions page with a single scrollable list of all matches, stage-based filtering, auto-scroll to the nearest match, and live updates when match results change. Additionally, create comprehensive test data including all WM 2026 matches and multiple tippers with realistic predictions.

## Problem

Current state of the predictions page:

1. **No stage navigation**: Users cannot see all matches at once or filter by stage
2. **No auto-scroll**: When opening the page, users don't automatically land at the most relevant match (next upcoming match)
3. **No live updates**: When match results change, the frontend doesn't reflect changes without manual page reload
4. **Insufficient test data**: Only basic test data exists, making it impossible to properly test ranking behavior, joker distribution across knockout stages, and realistic user scenarios

Missing features prevent effective testing and user experience:
- No visibility into how rankings behave with multiple tippers
- Cannot test joker behavior in knockout stages (no knockout matches exist yet)
- Cannot verify filtering and navigation with realistic match counts
- Cannot test auto-scroll behavior with mixed past/future matches

## Solution

### 1. Test Data Enhancement

Create a Django management command to populate the database with:

- **All 104 WM 2026 matches** with realistic kickoff times
  - 48 group stage matches (16 groups × 3 matches)
  - 32 round of 32 matches
  - 16 round of 16 matches
  - 8 quarter-final matches
  - 4 semi-final matches (including third-place playoff)
  - 1 final match
- **6+ test users (tippers)** with varied prediction patterns
- **Realistic predictions** for each tipper:
  - Varied prediction coverage (some users predict all matches, some partial)
  - Correct joker distribution:
    - 0 jokers in group stage
    - 3 jokers in R32
    - 3 jokers in R16
    - 2 jokers in QF
    - 2 jokers combined for SF/Final/Third-place
  - Mix of correct and incorrect predictions to show varied scoring
  - Some matches with results, some without

### 2. Predictions Page UX Improvements

Transform the predictions page from static tabs to a dynamic scrollable experience:

- **Single scrollable list**: Display all matches in chronological order (no tabs)
- **Stage filter**: Add a filter icon/dropdown to toggle stage visibility
  - Filter options: All, Group Stage, R32, R16, QF, SF, Final
  - Filters persist in URL/session for deep linking
- **Auto-scroll on load**: Automatically scroll to the first upcoming match (kickoff > now)
  - If all matches are finished, scroll to the last match
  - If no matches exist, show empty state
- **Live result updates**: Use HTMX polling or WebSocket to refresh match rows when results change
  - Poll every 30-60 seconds during active match times
  - Show visual indicator when data is updating
  - Update only changed rows to minimize DOM manipulation

## Scope

### In Scope

- Management command to create test data:
  - All 104 WM 2026 matches with correct teams, dates, and stages
  - 6-10 test users with profiles
  - Predictions for each user following joker rules
  - Some matches with results to show scoring
- Single scrollable match list on predictions page
- Stage filter UI component with icon/dropdown
- Auto-scroll to nearest upcoming match on page load
- HTMX polling for live match result updates
- Visual loading states during updates
- Filter state persistence (URL parameters or session)
- Update existing prediction_list.html template
- Update prediction_row.html partial for polling compatibility
- Tests for management command data creation
- Tests for auto-scroll JavaScript behavior
- Tests for filter functionality

### Out of Scope

- Real-time WebSocket implementation (use polling initially)
- Admin interface for match management (future change)
- Prediction statistics dashboard (future change)
- Notifications when matches finish (future change)
- Match detail page (future change)
- Editing existing test data (command will create fresh data)
- Automatic kickoff time generation based on real WM 2026 schedule (use simplified dates)

## Business Rules (from wm2026-rules.md)

### Tournament Structure
- 48 teams in 16 groups of 3 teams each
- Each group plays round-robin (3 matches per group = 48 group matches)
- Top 2 from each group advance (32 teams to knockout)
- Knockout stages: R32 (32→16), R16 (16→8), QF (8→4), SF (4→2), Final + Third-place

### Joker Distribution
| Round | Max Jokers |
|-------|-----------|
| Group stage (gs) | 0 (no jokers) |
| Round of 32 (r32) | 3 |
| Round of 16 (r16) | 3 |
| Quarter-final (qf) | 2 |
| Semi-final + Final + Third-place (sf, final, third) | 2 combined |

### Group Stage Prediction Limit
- Maximum 36 predictions for group stage matches (user chooses which 36 of 48)
- Enforcement is already implemented in PredictionLimitService

## Success Criteria

- [ ] Management command `python manage.py create_wm2026_testdata` exists
- [ ] Command creates 104 matches with correct stages and teams
- [ ] Command creates 6-10 test users
- [ ] Command creates predictions following joker rules for each user
- [ ] Some matches have results populated for testing scoring
- [ ] Predictions page shows single scrollable list of all matches
- [ ] Stage filter UI visible and functional
- [ ] Clicking filter options shows/hides matches by stage
- [ ] Page auto-scrolls to nearest upcoming match on load
- [ ] HTMX polling refreshes match results every 60 seconds
- [ ] Visual indicator shows when updates are loading
- [ ] Filter state persists across page reloads
- [ ] Tests verify data creation correctness
- [ ] Tests verify filter behavior
- [ ] Tests verify auto-scroll logic
- [ ] No breaking changes to existing prediction functionality
- [ ] All existing tests still pass
