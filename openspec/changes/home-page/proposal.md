# Proposal: Home Page with Compact Ranking and Next Matches

## Summary

Create a modern, user-centric home page that **replaces the standalone ranking page**. Shows the user's current rank prominently, displays a collapsed ranking view with nearby competitors (expandable to full ranking with filters), and presents the next 3 upcoming matches for quick tipping. The page should offer a clean, focused experience similar to modern fintech apps like Trade Republic or Revolut.

## Problem

Currently, there is no dedicated home page that gives users a quick overview of:

- Their current standing and rank
- How they compare to nearby competitors
- Upcoming matches they need to tip

Users must navigate to separate pages (ranking and predictions) to get this information, which creates friction and reduces engagement.

## Solution

Create a new home page (`/`) that consolidates the most important information:

### 1. Prominent Rank Display

At the top of the page, display the user's current rank in a large, eye-catching card:
- Large rank number
- Total points
- Champion prediction (flag emoji)
- Visual indicator (e.g., trophy icon or gradient)

### 2. Ranking Section (Replaces /ranking/ page)

Show a **collapsed ranking** by default:
- Display **5 entries total**: user's position + 4 closest ranks around them (2 above, 2 below when possible)
- Arrow icon to expand/collapse the full ranking
- When expanded:
  - Show the **complete ranking table** (IDENTICAL to old /ranking/ page)
  - All columns: Rang, Name, Champion, Exakt, Joker, Punkte
  - Include the tournament round filter (Live, Gruppenphase, Achtelfinale, etc.)
  - HTMX-powered round filtering
  - Desktop table + mobile cards
  - Same design and ALL functionality as the current ranking page
- When collapsed:
  - Hide the filter
  - Only show the 5 focused entries with minimal columns (Rang, Name, Champion, Punkte)

**Note:** The standalone `/ranking/` page will redirect to home page. All ranking functionality consolidated here.

### 3. Next 3 Matches Preview

Below the ranking section, show the next 3 upcoming matches:
- Use the same match row components from the predictions page
- Fully functional tipping interface (goals, joker toggle)
- Shows lock status (if match is no longer editable)
- HTMX-powered inline updates (no page reload)
- Link to full predictions page for more matches

### 4. Modern Design

- Clean, minimal interface inspired by Trade Republic and Revolut
- Smooth expand/collapse animations
- Card-based layout with generous spacing
- Consistent with existing Tailwind CSS styling
- Responsive (works on mobile and desktop)

## Non-Goals

- Full match history or results display
- User statistics or detailed analytics
- Social features (comments, reactions)
- Match notifications or reminders
- Profile editing (already handled in settings page)
- Keeping a separate `/ranking/` page (consolidates into home)
- Changing how ranking/scoring logic works (only UI reorganization)

## Success Criteria

- Homepage loads in under 1 second
- User's rank is displayed prominently at the top
- Ranking shows exactly 5 entries when collapsed (user + 4 nearby)
- Arrow icon smoothly expands/collapses the full ranking
- When expanded, full ranking with ALL columns (Rang, Name, Champion, Exakt, Joker, Punkte) visible
- When expanded, round filter with HTMX present and functional
- HTMX round filtering swaps ranking content without page reload
- Old `/ranking/` URL redirects to home page
- Next 3 upcoming matches are displayed and tippable
- All tipping functionality from predictions page works (goals, joker)
- Design is clean, modern, and visually appealing
- Page is fully responsive (mobile and desktop)
- HTMX updates work without page reload
