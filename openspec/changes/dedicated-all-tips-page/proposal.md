# Proposal: Dedicated All Tips Page

## Summary

Convert the current bottom sheet for viewing match predictions into a dedicated full-page view. Users click a button to navigate to a standalone page showing all tips for a match, with proper back navigation that returns them to their origin (home or predictions page).

## Problem

The current implementation uses a bottom sheet overlay to display all predictions for a match. While functional, this approach has limitations:

- Limited screen space on mobile (70% viewport height)
- Cannot be bookmarked or shared
- No proper browser history integration
- Back button doesn't work as expected
- Difficult to deep-link to specific match predictions
- Scrolling can feel constrained on smaller screens

For a feature that users may want to spend time reviewing and comparing predictions, a dedicated page provides a better user experience.

## Solution

### Dedicated Page View

Replace the bottom sheet overlay with a full-page view at `/predictions/match/<id>/all/`:

- Full-screen page dedicated to showing all predictions
- Responsive design optimized for both desktop and mobile
- Proper page title and meta information
- Browser back button works naturally
- Can be bookmarked and shared
- Scrolling uses the full viewport

### Navigation Flow

**From Predictions Page:**
- User clicks "Alle Tipps" button on match row
- Navigate to `/predictions/match/<id>/all/?from=predictions`
- Back button returns to predictions page at same scroll position

**From Home Page:**
- User clicks "Alle Tipps" button on match card
- Navigate to `/predictions/match/<id>/all/?from=home`
- Back button returns to home page

### Referrer Detection

Use query parameter `?from=predictions` or `?from=home` to track origin:
- Close/back button uses browser history or explicit redirect
- Preserve user context and scroll position
- Default fallback to predictions page if referrer unknown

### Icon Consistency

Standardize icons across the entire application:
- 👥 "Alle Tipps" button (view all predictions)
- 🔙 Back navigation button
- ⭐ Joker indicator
- 🏆 Champion prediction
- ✓ Exact match count
- Ensure same icons used in home, predictions, ranking pages

### Mobile-First Responsive Design

- Touch-friendly tap targets (min 44x44px)
- Optimized spacing for small screens
- Sticky header with match info
- Smooth scrolling on long lists
- Works well on screens 320px and wider
- Desktop view uses wider layout with more information density

## Non-Goals

- Editing predictions from the all-tips page (still done on main predictions page)
- Real-time updates (keep current polling on parent pages)
- Filtering or searching predictions
- Adding comments or discussion features
- Changing the ranking/sorting algorithm

## Success Criteria

- Users can navigate to dedicated page showing all match predictions
- Back navigation returns to correct origin page (home vs predictions)
- Page is fully responsive on mobile and desktop
- Icons are consistent across all pages (home, predictions, ranking, all-tips)
- Page can be bookmarked and shared via URL
- Browser back button works as expected
- No bottom sheet component remains in codebase

## Impact

### Users
- Better viewing experience for comparing predictions
- Natural browser navigation
- Shareable links to match predictions
- More screen space on mobile

### Code
- Remove bottom sheet JavaScript and CSS
- Simplify HTMX usage (full page navigation instead of partial swaps)
- Cleaner separation between list views and detail views
- Better alignment with Django conventions (template views instead of partials)

## Migration Notes

- Existing `MatchPredictionsView` can be refactored to render full page
- Bottom sheet styles and JavaScript can be removed
- Update links in home and predictions templates
- No database changes required
