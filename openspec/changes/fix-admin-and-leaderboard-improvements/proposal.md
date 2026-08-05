# Proposal: Fix Admin and Leaderboard Improvements

## Summary

Fix critical admin-related bugs and improve leaderboard export functionality. Address champion prediction ranking updates, icon consistency, admin navigation access, and enhanced leaderboard exports with full prediction details.

## Problem

### 1. Champion Ranking Update Bug
When an admin manually sets a user's champion prediction (e.g., after the tournament started and user can't change it themselves), the ranking does not automatically recalculate. This causes incorrect leaderboard standings until a manual recalculation is triggered.

**Impact**: Users see outdated rankings that don't reflect champion prediction bonuses.

### 2. Icon Inconsistency
Icons display differently between the "all tips" view and the ranking/leaderboard view. This creates a confusing and inconsistent user experience.

**Impact**: Users may misinterpret predictions or match states due to visual inconsistency.

### 3. Missing Admin Navigation Link
Staff users have no quick way to access the Django admin panel from the main site navigation. They must manually type `/admin/` in the URL bar.

**Impact**: Poor admin UX; increases friction for content management tasks.

### 4. Limited Leaderboard Export
The current CSV export only includes ranking summary data (rank, username, total points, exact matches, jokers used). Admins need detailed prediction data for analysis, auditing, and reporting:
- Who predicted what for each match
- When predictions were made
- Which predictions used jokers
- Full prediction details per user

**Impact**: Admins cannot perform detailed analysis or audits without database access.

### 5. Unused Weekly Leaderboard Mode
The system supports "daily", "weekly", and "final" snapshot types, but "weekly" is not actively used and adds unnecessary complexity.

**Impact**: Code maintenance burden; confusing options in admin interface.

### 6. No Manual Leaderboard Download
Admins must use the management command or admin panel actions to create snapshots. There's no quick way to download the current leaderboard state on demand.

**Impact**: Extra steps required for common administrative tasks.

## Solution

### 1. Fix Champion Ranking Recalculation
- Add signal handler that triggers ranking recalculation when `User.predicted_champion` is changed
- Use Django's `post_save` signal with field change detection
- Ensure recalculation only fires when champion actually changes (not on every user save)
- Call `RankingService.recalculate_all_user_scores()` after champion change

### 2. Standardize Icons Across Views
- Audit icon usage in templates (ranking vs. predictions views)
- Identify inconsistencies (different SVG paths, colors, sizes)
- Create shared icon partial templates or template tags
- Apply consistent icons throughout the application

### 3. Add Admin Link to Navbar
- Add conditional admin link to `templates/base.html` navigation
- Show link only to staff users (`user.is_staff`)
- Position link appropriately in navbar (after Rules, before user menu)
- Match existing navbar styling and responsive behavior

### 4. Enhanced CSV Export with Prediction Details
- Extend `scoring/exports.py` to include prediction-level data
- New export format includes:
  - User information (rank, username, total points)
  - Per-match predictions (match, predicted score, actual score, points earned, joker used, prediction timestamp)
- Provide both summary and detailed export options
- Add admin action to export detailed leaderboard

### 5. Remove Weekly Snapshot Type
- Remove "weekly" from `snapshot_type` choices in:
  - `scoring/models.py` (LeaderboardSnapshot.SNAPSHOT_TYPE_CHOICES)
  - `scoring/admin.py` (remove `create_weekly_snapshot` action)
  - `scoring/management/commands/create_snapshot.py` (remove weekly option)
- Keep "daily" and "final" snapshot types
- Update documentation and help text
- Add migration to remove existing weekly snapshots (optional, or keep historic data)

### 6. Admin Manual Leaderboard Download Button
- Add view in `scoring/views.py` for on-demand leaderboard download
- Accessible via URL `/admin/leaderboard-export/` (staff-only)
- Returns CSV with current leaderboard state
- Optionally add link in admin panel or navbar for quick access

## Non-Goals

- Multi-language support for admin interface
- Automated weekly snapshot scheduling (removing the feature entirely)
- Visual redesign of leaderboard or ranking pages
- Real-time ranking updates (existing polling behavior is sufficient)
- Historical prediction editing by admins
- Bulk prediction import/export for users

## Success Criteria

### Champion Ranking Update
- [x] Changing user's predicted_champion via admin triggers ranking recalculation
- [x] Rankings reflect champion bonus points immediately after admin change
- [x] Signal handler only fires when champion actually changes
- [x] Tests verify recalculation on champion change

### Icon Consistency
- [x] All match state icons (locked, unlocked, finished) are visually identical across views
- [x] Joker icons are consistent across all views
- [x] Champion icons are consistent across all views
- [x] Manual visual audit confirms consistency

### Admin Navbar Link
- [x] Staff users see "Admin" link in navbar
- [x] Non-staff users do not see the link
- [x] Link points to `/admin/`
- [x] Link styling matches existing navbar items
- [x] Responsive design works on mobile

### Enhanced CSV Export
- [x] Admin can download CSV with full prediction details
- [x] Export includes: user, match, prediction, actual result, points, joker, timestamp
- [x] Export is downloadable via admin action or dedicated view
- [x] CSV format is clear and usable for analysis

### Weekly Mode Removal
- [x] "weekly" removed from all snapshot type choices
- [x] Admin panel does not show "Create weekly snapshot" action
- [x] Management command does not accept "weekly" option
- [x] Help text and documentation updated
- [x] Existing code that references "weekly" is cleaned up

### Manual Leaderboard Download
- [x] Admin can download current leaderboard via direct link
- [x] Download returns CSV with current rankings
- [x] View requires staff permissions
- [x] Link is accessible from admin or navbar
