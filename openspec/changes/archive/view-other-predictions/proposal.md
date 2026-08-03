# Proposal: View Other Predictions

## Summary

Enable users to view other players' predictions for a match by clicking on it. A mobile-friendly bottom sheet slides up showing all predictions for that match, but only after the match has started (to prevent copying).

## Problem

Currently, users can only see their own predictions. They cannot:

- See what other participants predicted for a specific match
- Compare their prediction with others
- Get a sense of the "popular" predictions in the group

This reduces engagement and the social aspect of the tipping game.

## Solution

### Bottom Sheet Component

When a user clicks/taps on a match row:

Slide up a bottom sheet panel showing:
   - Match info header (teams, actual result if available)
   - List of all users with their predictions (Olympic-style ranking)
   - Each row: Rank, Username, predicted score, points earned (if scored)
   - Users without predictions shown as "Kein Tipp"
   - Joker indicator if user used joker
   - Current user's prediction highlighted

### Olympic Ranking

- Users ranked by points earned (descending)
- Tied users share the same rank
- After a tie, next rank skips (1, 2, 2, 4 not 1, 2, 2, 3)
- Matches the global leaderboard ranking system

### Mobile-First Design

- Bottom sheet slides up from bottom (70% screen height)
- Swipe down or tap backdrop to close
- Touch-friendly spacing and tap targets
- Scrollable list for many participants
- Works equally well on desktop (modal-style)

### Visibility

- All predictions are always visible to all logged-in users
- All active users shown (even without predictions)
- No time-based restrictions

## Non-Goals

- Editing predictions from the bottom sheet
- Chat/comments on matches
- Real-time updates while sheet is open
- Filtering or sorting predictions

## Success Criteria

- Users can tap any match to see others' predictions
- Bottom sheet is smooth and responsive on mobile
- Predictions hidden before kickoff (server-enforced)
- Works on screens 320px and wider
- Close gesture works reliably (swipe down + backdrop tap)
