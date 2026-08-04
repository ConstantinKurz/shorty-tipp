## Why

Users need to view tournament standings at different stages of the competition to understand progression and track performance over time. Currently, the ranking view only shows the live leaderboard based on all finished matches. Users cannot answer questions like:

- "How was I ranking after the group stage?"
- "Where did I stand going into the quarter-finals?"
- "How much did that semi-final prediction change the standings?"

This historical context is valuable for understanding tournament flow, analyzing prediction strategy effectiveness across different phases, and engaging with the competition's progression.

The existing `LeaderboardSnapshot` model provides admin-created snapshots, but these are unreliable (only exist when manually created) and not user-facing. Users need a self-service way to explore historical rankings.

Since `points_earned` is already cached on each `MatchPrediction`, dynamic calculation is fast enough (<50ms) to provide on-demand historical rankings without pre-computation.

## What Changes

Add round-based filtering to the existing ranking view, allowing users to view standings calculated up to and including any tournament round.

- Add round filter buttons to ranking template (Group, R32, R16, QF, SF, Final)
- Default view: "Live" (all finished matches)
- Use HTMX for dynamic updates without full page reload
- Create new service method to calculate rankings filtered by round
- Leverage existing cached `points_earned` values for fast computation
- Display current `predicted_champion` for all historical views (accurate after first match)
- Match existing horizontal button bar style used elsewhere in the app
- Add view tests for round filtering logic
- Maintain backward compatibility (no breaking changes to existing ranking view)

## Capabilities

### New Capabilities
- `ranking-round-filter`: Filter ranking by tournament round using dynamic calculation

### Modified Capabilities
- `ranking-view`: Extended to support optional round parameter for historical views
- `ranking-service`: New method to calculate rankings up to a specific round

## Impact

- Modified view: `users/views.py` (`RankingView`)
- Modified service: `scoring/services.py` (`RankingService.get_leaderboard_up_to_round()`)
- Modified template: `templates/ranking.html` (add round filter UI)
- New tests: `scoring/tests/test_ranking_service.py` (round filtering tests)
- Modified tests: `users/tests/test_views.py` (view parameter handling)
- No model changes
- No migrations
- No changes to URL structure (uses query params)

## Non-Goals

- Date-based filtering (out of scope for this change)
- Snapshot-based historical views (keeping snapshots for admin use only)
- Comparison views (side-by-side rankings)
- Champion prediction history tracking (use current value)
- Per-user historical trend graphs
