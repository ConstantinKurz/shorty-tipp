# Proposal: Enhanced Prediction Ranking View

## Summary

Enhance the match predictions bottom sheet to display comprehensive user statistics (champion prediction, exact predictions count, jokers used, total points) and add flexible sorting options to compare users by match-specific points or overall performance.

## Problem

Currently, when viewing other users' predictions for a match, the display only shows:

- Username
- Predicted score for this match
- Points earned for this match
- Joker indicator (if used on this match)
- Rank based on this match's points

Users cannot:

- See which champion each user predicted using country flag
- Know how many exact predictions a user has made overall
- See how many jokers a user has used across all matches
- View each user's total accumulated points
- Sort/compare users by their overall performance instead of just this match

This limits the ability to understand the broader context of each user's tipping strategy and overall standing while viewing match-specific predictions.

## Solution

### Enhanced User Statistics Display

Add comprehensive statistics for each user in the predictions list:

- **Champion Prediction**: Show which team the user predicted as tournament champion
- **Exact Predictions**: Count of exact result predictions (6-point scores) across all matches
- **Jokers Used**: Total number of jokers used across all matches
- **Total Points**: User's cumulative points from all matches

Display these as additional columns or an expandable info section on each user row.

### Flexible Sorting

Add a sorting toggle/slider control above the predictions list:

- **Match Points** (default): Current behavior - rank users by points earned on this specific match
- **Total Points**: Sort users by their overall tournament points
- Persist the Olympic-style ranking system (shared ranks for ties, skip after tie)
- Sort order applies to whichever metric is selected

The toggle should be:
- Simple and touch-friendly (mobile-first)
- Visual indication of active sorting mode
- Instant re-ranking without page reload (HTMX)

### Mobile-First Design

- Compact display of statistics (icons + numbers)
- Statistics visible but not overwhelming
- Sorting toggle easily accessible at top of sheet
- All information scannable on small screens

## Non-Goals

- Filtering users (show/hide specific users)
- Multiple simultaneous sort criteria
- Historical comparison across different matches
- Exporting or sharing rankings
- Chart/graph visualizations of statistics

## Success Criteria

- Each user row displays champion, exact count, jokers count, and total points
- Sorting toggle switches between match points and total points
- Olympic-style ranking applied to whichever sort mode is active
- Statistics are accurate and performant (no N+1 queries)
- Layout remains clean and scannable on mobile devices
- Current user's row remains highlighted regardless of sort mode
