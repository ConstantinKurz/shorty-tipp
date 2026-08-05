# Tasks: Fix Admin and Leaderboard Improvements

## Task 1: Add champion change signal for ranking recalculation

### Goal
Automatically recalculate rankings when a user's predicted champion is changed via admin panel.

### Scope
- Add `post_save` signal handler to `User` model
- Detect when `predicted_champion` field changes
- Trigger ranking recalculation for affected user
- Add `recalculate_user_score()` method to `RankingService`

### Out of Scope
- Optimizing recalculation to only update single user (can use full recalculation for now)
- UI feedback when recalculation happens
- Signal for other field changes

### Acceptance Criteria
- [x] Signal handler added to `users/models.py`
- [x] Signal only fires when `predicted_champion` actually changes
- [x] Signal does not fire on user creation
- [x] Signal calls `RankingService.recalculate_user_score(user)`
- [x] `RankingService.recalculate_user_score()` method exists
- [x] Rankings reflect updated champion bonus after admin change

### Required Tests
- Test signal fires when champion changes via admin
- Test signal doesn't fire on user creation
- Test signal doesn't fire when champion unchanged
- Test ranking updates after champion change
- Integration test: Change champion via admin form, verify ranking updates

---

## Task 2: Audit and standardize icon usage across templates

### Goal
Identify all icon inconsistencies between prediction and ranking views and document them for fixing.

### Scope
- Audit all templates for icon usage
- Document current SVG paths, sizes, and colors for each icon type
- Identify inconsistencies
- Create list of icons that need standardization:
  - Match status icons (locked, unlocked, finished)
  - Joker icons
  - Champion icons
  - Navigation icons
- Document recommended shared icon approach

### Out of Scope
- Actually fixing the icons (done in next task)
- Creating new icon designs

### Acceptance Criteria
- [x] All icon usages documented in audit report
- [x] Inconsistencies identified and listed
- [x] Recommended approach chosen (template partials vs. template tags)
- [x] List of files that need updates created

### Required Tests
- Manual visual audit across all pages
- Screenshot comparison between views

---

## Task 3: Create shared icon partials and update templates

### Goal
Replace inconsistent icons with shared, reusable icon components.

### Scope
- Create `templates/partials/icons/` directory
- Create icon partials for:
  - `match_locked.html`
  - `match_unlocked.html`
  - `match_finished.html`
  - `joker.html`
  - `champion.html`
  - Any other icons identified in audit
- Update all templates to use shared icons:
  - `templates/predictions/prediction_row.html`
  - `templates/predictions/prediction_list.html`
  - `templates/partials/ranking_content.html`
  - `templates/partials/compact_ranking.html`
  - Any other templates with icons

### Out of Scope
- Redesigning icon appearance
- Animated icons
- Icon color theming beyond existing dark mode

### Acceptance Criteria
- [x] Icon partials directory created
- [x] All identified icons have partial templates
- [x] All templates updated to use `{% include "partials/icons/..." %}`
- [x] Icons visually identical across all views
- [x] Icons maintain proper sizing and colors
- [x] Dark mode support preserved

### Required Tests
- Manual visual test: icons consistent across prediction list
- Manual visual test: icons consistent across ranking pages
- Manual visual test: icons consistent across compact ranking
- Template rendering test: icon partials render without errors

---

## Task 4: Add admin link to navbar

### Goal
Add a "Admin" link to the main navigation bar, visible only to staff users.

### Scope
- Modify `templates/base.html`
- Add conditional admin link after "Rules" link
- Show link only to `user.is_staff`
- Link points to `/admin/`
- Match existing navbar styling
- Ensure responsive behavior

### Out of Scope
- Custom admin dashboard
- Admin link in footer
- Permission granularity beyond `is_staff`

### Acceptance Criteria
- [x] Admin link added to navbar in `base.html`
- [x] Link visible only when `user.is_staff` is True
- [x] Link not visible to non-staff users
- [x] Link points to `/admin/`
- [x] Link styling matches other navbar links
- [x] Link has hover states matching other links
- [x] Responsive design works on mobile
- [x] Link positioned after "Rules" and before user menu separator

### Required Tests
- Template test: staff user sees admin link
- Template test: non-staff user doesn't see admin link
- Template test: link has correct href
- Manual test: click link opens admin panel
- Manual test: responsive design works

---

## Task 5: Implement detailed CSV export with prediction data

### Goal
Add enhanced CSV export functionality that includes per-match prediction details for every user.

### Scope
- Add `generate_detailed_leaderboard_csv()` function to `scoring/exports.py`
- Export includes: rank, username, total points, match info, predictions, results, points earned, joker status, timestamps
- Update `csv_response()` to support `detailed` parameter
- Export covers all matches and all users in leaderboard
- Format is CSV-compatible for Excel/Google Sheets

### Out of Scope
- Excel/XLSX format
- PDF export with prediction details
- Filtering by match or round
- User-specific prediction export (admin only)

### Acceptance Criteria
- [x] `generate_detailed_leaderboard_csv()` function exists in `scoring/exports.py`
- [x] Function includes all required fields (rank, username, match, predictions, points, joker, timestamp)
- [x] `csv_response()` accepts `detailed` parameter
- [x] Detailed export includes row for each user-match combination
- [x] Empty predictions show as blank values (not errors)
- [x] CSV is well-formatted and importable to Excel
- [x] Function handles missing predictions gracefully
- [x] Function handles matches without results

### Required Tests
- Unit test: detailed CSV structure is correct
- Unit test: CSV includes all matches
- Unit test: CSV includes all users
- Unit test: Joker status correctly displayed
- Unit test: Empty predictions handled correctly
- Integration test: generate CSV, verify content
- Manual test: open CSV in Excel, verify readability

---

## Task 6: Add admin action for detailed CSV export

### Goal
Add Django admin action to export detailed leaderboard with predictions.

### Scope
- Add `export_detailed_csv` admin action to `LeaderboardSnapshotAdmin`
- Action generates detailed CSV export
- Action returns downloadable CSV file
- Action shows success message
- Add to actions list in admin

### Out of Scope
- Scheduled exports
- Email exports
- Custom export filters

### Acceptance Criteria
- [x] `export_detailed_csv` action added to `scoring/admin.py`
- [x] Action appears in admin interface dropdown
- [x] Action generates detailed CSV using `generate_detailed_leaderboard_csv()`
- [x] Action returns CSV as downloadable file
- [x] Filename includes current date
- [x] Action works from LeaderboardSnapshot admin list view

### Required Tests
- Admin test: action appears in admin dropdown
- Integration test: execute action, verify CSV download
- Integration test: verify CSV content matches expected format

---

## Task 7: Remove weekly snapshot type from model and admin

### Goal
Remove "weekly" snapshot type from LeaderboardSnapshot model and all related code.

### Scope
- Remove "weekly" from `SNAPSHOT_TYPE_CHOICES` in `scoring/models.py`
- Remove `create_weekly_snapshot` admin action from `scoring/admin.py`
- Update actions list in `LeaderboardSnapshotAdmin`
- Remove "weekly" choice from `create_snapshot` management command
- Update help text and documentation

### Out of Scope
- Removing existing weekly snapshot data (done in migration)
- Changing snapshot creation logic

### Acceptance Criteria
- [x] "weekly" removed from `SNAPSHOT_TYPE_CHOICES` in `scoring/models.py`
- [x] `create_weekly_snapshot` action removed from `scoring/admin.py`
- [x] Actions list updated (only daily and export_csv remain)
- [x] `create_snapshot` command only accepts "daily" or "final"
- [x] Help text updated in command
- [x] No references to "weekly" remain in code (except tests being removed)

### Required Tests
- Unit test: weekly not in choices
- Admin test: weekly action not in dropdown
- Command test: weekly raises error or is not accepted
- Manual test: admin interface shows only daily/final options

---

## Task 8: Add migration to remove existing weekly snapshots

### Goal
Create and run data migration to remove existing weekly snapshot records.

### Scope
- Create new migration in `scoring/migrations/`
- Migration deletes all `LeaderboardSnapshot` objects where `snapshot_type="weekly"`
- Migration logs count of deleted snapshots
- Migration is reversible (noop on reverse)

### Out of Scope
- Archiving weekly snapshots before deletion
- Selective weekly snapshot preservation

### Acceptance Criteria
- [x] Migration file created (`0002_remove_weekly_snapshots.py`)
- [x] Migration uses `RunPython` to delete weekly snapshots
- [x] Migration logs count of deleted records
- [x] Migration is reversible (reverse is noop)
- [x] Migration runs successfully
- [x] No weekly snapshots remain after migration

### Required Tests
- Migration test: create weekly snapshot, run migration, verify deletion
- Migration test: verify non-weekly snapshots untouched
- Manual test: run migration, check database

---

## Task 9: Implement manual leaderboard download view

### Goal
Create a staff-only view that allows on-demand download of current leaderboard as CSV.

### Scope
- Add `DownloadLeaderboardView` class to `scoring/views.py`
- View requires staff permissions (`@staff_member_required`)
- View generates current leaderboard CSV
- View supports `?detailed=true` query parameter for detailed export
- View returns CSV as downloadable file
- Filename includes current date

### Out of Scope
- Scheduled downloads
- Historical leaderboard downloads
- UI page with download button (direct link only)

### Acceptance Criteria
- [x] `DownloadLeaderboardView` class added to `scoring/views.py`
- [x] View decorated with `@staff_member_required`
- [x] View calls `RankingService.get_current_leaderboard()`
- [x] View returns CSV using `csv_response()`
- [x] View respects `?detailed=true` parameter
- [x] Filename format: `leaderboard_YYYY-MM-DD.csv`
- [x] Non-staff users get 403/redirect

### Required Tests
- View test: staff user can access view
- View test: non-staff user gets 403
- View test: returns CSV response
- View test: filename includes date
- Integration test: download CSV, verify structure
- Integration test: detailed parameter works

---

## Task 10: Add URL routing for manual leaderboard download

### Goal
Add URL pattern for the manual leaderboard download view.

### Scope
- Add URL pattern to `scoring/urls.py`
- Pattern: `admin/download-leaderboard/`
- Name: `download-leaderboard`
- Route to `DownloadLeaderboardView`

### Out of Scope
- Adding link to navbar (optional, can be done later)
- Custom admin integration

### Acceptance Criteria
- [x] URL pattern added to `scoring/urls.py`
- [x] Pattern is `admin/download-leaderboard/`
- [x] URL name is `download-leaderboard`
- [x] URL resolves to `DownloadLeaderboardView`
- [x] URL is accessible at `/scoring/admin/download-leaderboard/`

### Required Tests
- URL test: pattern resolves to correct view
- URL test: reverse lookup works
- Integration test: access URL, get CSV

---

## Task 11: Update tests for weekly snapshot removal

### Goal
Remove or update tests that reference "weekly" snapshot type.

### Scope
- Update `scoring/tests/test_leaderboard_snapshot.py`
- Update `scoring/tests/test_management_commands.py`
- Remove tests for `create_weekly_snapshot` admin action
- Remove tests for weekly snapshot creation via command
- Update any other tests that reference weekly snapshots

### Out of Scope
- Adding new test coverage beyond cleanup

### Acceptance Criteria
- [x] `test_weekly_snapshot` removed or updated in `test_leaderboard_snapshot.py`
- [x] `test_create_weekly_snapshot` removed from `test_management_commands.py`
- [x] No test references "weekly" snapshot type
- [x] All remaining tests pass
- [x] Test suite runs without errors

### Required Tests
- Run full test suite, verify no failures
- Verify no tests reference weekly snapshots

---

## Task 12: Add tests for champion change signal

### Goal
Comprehensive test coverage for champion change signal handler.

### Scope
- Test signal fires when champion changes
- Test signal doesn't fire on user creation
- Test signal doesn't fire when champion unchanged
- Test ranking recalculation triggered
- Integration test with admin form

### Out of Scope
- Performance testing
- Concurrent update testing

### Acceptance Criteria
- [x] Test: signal fires when predicted_champion changes
- [x] Test: signal doesn't fire on new user creation
- [x] Test: signal doesn't fire when champion remains the same
- [x] Test: `recalculate_user_score()` called when champion changes
- [x] Integration test: admin change updates ranking
- [x] All tests pass

### Required Tests
- `test_champion_change_triggers_recalculation()`
- `test_champion_change_on_creation_does_not_trigger_signal()`
- `test_no_change_does_not_trigger_signal()`
- `test_recalculation_updates_ranking()`
- `test_admin_champion_change_integration()`

---

## Task 13: Documentation updates

### Goal
Update project documentation to reflect all changes.

### Scope
- Update README if needed
- Update any admin documentation
- Add notes about weekly snapshot removal
- Document new CSV export features
- Document manual download view

### Out of Scope
- Full documentation rewrite
- API documentation

### Acceptance Criteria
- [x] Changes documented in appropriate files
- [x] Weekly snapshot removal noted
- [x] Enhanced CSV export documented
- [x] Manual download view URL documented
- [x] Admin users aware of new features

### Required Tests
- Manual review of documentation
- Verify accuracy of documented features
