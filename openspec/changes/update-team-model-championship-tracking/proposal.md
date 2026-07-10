## Why

The current Team model includes a `group` field for tournament group assignment, but this is not needed for the World Cup 2026 tipping game rules. Instead, teams need to track championship points and whether they won the tournament. These fields are required for scoring predictions and determining tournament winners.

## What Changes

- Remove `group` field and GROUP_CHOICES from Team model
- Add `points` integer field to track championship points for each team
- Add `is_champion` boolean field to mark the tournament winner
- Update Team model tests to cover new fields
- Update migration to reflect model changes
- Update admin interface if needed

## Capabilities

### New Capabilities
<!-- No new capabilities being introduced -->

### Modified Capabilities
- `team-model`: Team data model now tracks championship points and winner status instead of group assignment

## Impact

- Team model schema changes (migration required)
- Existing Team records will need migration (group → points/is_champion)
- Tests need updates for new field validation
- Admin interface may need adjustment
- Any code referencing team.group will break (**BREAKING** if such code exists)
