## Context

The Team model was just created with a `group` field (A-H) for tournament group assignment. After reviewing the WM 2026 tipping game requirements, the group assignment is not needed. Instead, teams need to track championship points and whether they became the tournament champion.

Current Team model has:
- name (CharField)
- fifa_code (CharField, unique)
- group (CharField with A-H choices) ← to be removed

Need to add:
- points (IntegerField) for championship/ranking points
- is_champion (BooleanField) to mark the tournament winner

## Goals / Non-Goals

**Goals:**
- Remove unused group field from Team model
- Add points tracking for championship standings
- Add champion flag to identify tournament winner
- Update tests to validate new fields
- Migrate existing data (if any)

**Non-Goals:**
- Implementing scoring logic (separate change)
- Adding match result tracking (already exists)
- Changing Match model
- UI changes beyond admin

## Decisions

### 1. Field Type for Points: IntegerField

**Decision:** Use IntegerField for points with default=0.

**Rationale:**
- Championship points are whole numbers
- Default to 0 for newly created teams
- Allows negative points if needed for penalties
- Simple and performant

**Alternatives considered:**
- PositiveIntegerField: Rejected - may need negative for penalties
- DecimalField: Rejected - unnecessary complexity for whole numbers

### 2. Champion Flag: BooleanField with default=False

**Decision:** Use BooleanField with default=False, allow only one champion.

**Rationale:**
- Clear boolean: team is champion or not
- Default False for all teams initially
- Can add validation later to ensure only one champion per tournament

**Alternatives considered:**
- Multiple champions: Rejected - only one winner per tournament
- Nullable field: Rejected - every team has champion status (True/False)

### 3. Migration Strategy: Remove group, add new fields

**Decision:** Create migration that:
1. Removes group field
2. Adds points field (default=0)
3. Adds is_champion field (default=False)

**Rationale:**
- Simple migration for newly created model
- Since just implemented, likely no production data
- If sample data exists, it will get default values

**Data handling:**
- Existing teams lose group assignment (acceptable - not needed)
- All teams start with points=0 and is_champion=False

### 4. Admin Interface Updates

**Decision:** Update TeamAdmin list_display to show points and is_champion instead of group.

**Rationale:**
- Show relevant fields for championship tracking
- Remove unused group from display
- Add list_filter for is_champion to easily find winner

## Risks / Trade-offs

**Risk:** Breaking change if code references team.group  
**Mitigation:** Just implemented, unlikely external code exists. Tests will catch any internal references.

**Risk:** Migration might fail if many teams exist with group data  
**Mitigation:** Just created model, minimal data. If needed, can preserve in migration.

**Trade-off:** No validation preventing multiple champions  
**Acceptance:** Can add model validation later if needed. Keep simple for now.

## Migration Plan

1. Create migration removing group, adding points/is_champion
2. Run migration on development database
3. Update tests to remove group references
4. Add new tests for points and is_champion
5. Update admin configuration
6. Verify in admin interface

No production deployment concerns - model just created.

## Open Questions

None - requirements are clear.
