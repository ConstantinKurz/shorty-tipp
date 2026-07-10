## Why

The tipping game needs to track teams and matches for the World Cup 2026 tournament. Without these core models, users cannot make predictions or see the tournament structure. This is the foundational data layer that enables all game functionality.

## What Changes

- Create Team model to represent countries/teams in the tournament
- Create Match model to represent games between teams with results
- Establish ForeignKey relationships (Match → Team for home/away teams)
- Add admin interfaces for managing teams and matches
- Create migrations for both models
- Add comprehensive tests for model creation and relationships

## Capabilities

### New Capabilities
- `team-model`: Team data model representing tournament participants with name, FIFA code, and group assignment
- `match-model`: Match data model representing games between teams with date, round, scores, and status

### Modified Capabilities
<!-- No existing capabilities modified -->

## Impact

- New models in `matches` app: `Team` and `Match`
- New database tables: `matches_team` and `matches_match`
- Admin interface extended for team and match management  
- User model unchanged (predictions relationship deferred to later change)
- No UI changes (admin-only for now)
