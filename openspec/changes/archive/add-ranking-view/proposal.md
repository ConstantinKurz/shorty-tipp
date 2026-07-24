## Why

Users need to see the current tournament standings to understand their competitive position and track other participants' performance. This is a core feature of any tipping game. Currently, users can log in and predict matches, but there's no way to view the rankings.

The ranking view should display all relevant information to understand standings: placement, points, chosen champion, prediction accuracy (exact matches), and strategic joker usage.

## What Changes

- Create a new ranking view accessible to all authenticated users
- Display comprehensive ranking table with olympic-style placement (shared rank for ties)
- Show username, rank, total points, predicted champion with country flag
- Display exact match count and number of jokers used
- Sort by total points (descending), with alphabetical ordering as tiebreaker
- Style with existing fintech aesthetic (dark mode, zinc colors, Tailwind CSS)
- Add URL route and navigation link in base template
- **Write view tests to verify ranking logic and display**

## Capabilities

### New Capabilities
- `ranking-view`: Public ranking page showing all users' standings and stats
- `ranking-url`: New route `/ranking/` accessible to authenticated users

### Modified Capabilities
- `base-template`: Add navigation link to ranking view

## Impact

- New view: `users/views.py` or dedicated `ranking/views.py`
- New template: `templates/ranking.html`
- New URL route in `tipapp/urls.py` or app-specific urls
- New test file for ranking view tests
- Base template update (navigation)
- No model changes (uses existing User fields)
- No migrations
