# Proposal: Match Phase Navigation

## Summary

Reorganize the predictions page to display matches grouped by tournament phase (Gruppenphase, Achtelfinale, Viertelfinale, etc.) with a sticky navigation bar showing prediction progress and joker usage. Enable easy phase switching on both desktop and mobile.

## Problem

Currently, matches are displayed in a single chronological list grouped by date. Users cannot:

- Quickly navigate to a specific tournament phase
- See at a glance how many matches they've tipped per phase
- Track joker usage per phase while scrolling
- Easily switch between phases on mobile devices

With 104 matches in the tournament (72 group stage + 32 knockout), the current list becomes unwieldy.

## Solution

1. **Phase-based grouping**: Display matches grouped by tournament round instead of date
2. **Sticky progress bar**: A persistent header showing:
   - Current phase name
   - Predictions count (e.g., "12/36 Tipps" for group stage)
   - Joker count (e.g., "2/3 Joker" for knockout rounds)
3. **Phase navigation**: Tab-based navigation for quick phase switching
4. **Responsive design**: Horizontal scrollable tabs on mobile, full tab bar on desktop

## Non-Goals

- Changing the underlying prediction logic or scoring
- Adding new database models
- Modifying the prediction row component behavior
- Server-side filtering (use client-side for instant response)

## Success Criteria

- Users can switch between phases with one click/tap
- Progress indicators remain visible while scrolling
- Phase switching works smoothly on mobile (< 500ms perceived latency)
- Current phase persists via URL parameter for shareability
