## Context

The MatchPrediction model was created in the previous change to track user predictions for matches. It currently stores predicted goals, joker status, and timestamps, but doesn't cache calculated points or identify exact score matches. The scoring service (to be implemented) will need to calculate points based on prediction accuracy and update these fields when match results are entered.

## Goals / Non-Goals

**Goals:**
- Add `points_earned` field to cache calculated points for each prediction
- Add `is_exact_match` boolean to identify perfect score predictions (Sechser)
- Make both fields nullable (NULL until match result is entered)
- Update admin interface to display scoring information
- Prepare foundation for scoring service to populate these fields

**Non-Goals:**
- Implementing the scoring calculation logic (separate scoring service change)
- Automatic recalculation when points rules change (manual migration if needed)
- Storing detailed scoring breakdown (just final points)
- UI for viewing predictions (admin-only for now)

## Decisions

### 1. Points field type: IntegerField vs. DecimalField

**Decision:** Use `IntegerField` for `points_earned`.

**Rationale:**
- Shortytipp rules use whole number points (exact: 6, correct result: 3, etc.)
- No fractional points in current game rules
- Simpler queries and aggregations
- Can change to DecimalField later if rules change (non-breaking)

**Alternatives considered:**
- DecimalField: Rejected - adds unnecessary complexity for current requirements
- FloatField: Rejected - precision issues, not needed for whole numbers

### 2. Points field nullability

**Decision:** Make `points_earned` nullable (`null=True, blank=True`).

**Rationale:**
- Points can only be calculated after match result is entered
- NULL clearly indicates "not yet scored" vs. 0 points earned
- Allows creating predictions before matches finish
- Simpler queries: `points_earned__isnull=False` for scored predictions

**Alternatives considered:**
- Default to 0: Rejected - ambiguous (0 points or not scored yet?)
- Required field: Rejected - can't create predictions for future matches

### 3. Exact match field structure

**Decision:** Simple `BooleanField(null=True)` for `is_exact_match`.

**Rationale:**
- Exact match (Sechser) is binary: either exact score or not
- NULL when not yet scored, True/False after scoring
- Enables fast filtering: `MatchPrediction.objects.filter(is_exact_match=True)`
- Denormalized data (can derive from comparing goals) but worth it for query performance

**Alternatives considered:**
- No field, calculate on-the-fly: Rejected - frequent leaderboard queries would be expensive
- Computed property: Rejected - can't filter in database efficiently
- Separate ExactMatch model: Rejected - overengineering for a boolean flag

### 4. Points calculation responsibility

**Decision:** Scoring fields are write-only from scoring service, read-only everywhere else.

**Rationale:**
- Centralized scoring logic prevents inconsistencies
- Model doesn't know scoring rules → delegate to service
- Admin can view but not manually edit these fields
- Clear separation of concerns

**Alternatives considered:**
- Model-level save() hook: Rejected - can't access match results from model layer cleanly
- Signal-based calculation: Rejected - harder to test, implicit behavior
- Editable fields: Rejected - risk of manual errors, breaks audit trail

### 5. Migration strategy for existing data

**Decision:** Add fields as nullable, no data migration needed.

**Rationale:**
- Currently no production data (greenfield)
- Existing test predictions will have NULL for new fields
- Tests updated to handle NULL state
- When results entered, scoring service populates fields

**Alternatives considered:**
- Default to 0 and False: Rejected - ambiguous, harder to distinguish unscored predictions
- Require backfill migration: Rejected - no existing production data to backfill

### 6. Admin interface presentation

**Decision:** Show `points_earned` and `is_exact_match` in list_display as read-only fields.

**Rationale:**
- Useful for debugging and verification
- Read-only prevents manual editing
- List view shows scoring status at a glance
- Filter by is_exact_match enables finding all Sechser quickly

**Alternatives considered:**
- Hide from admin: Rejected - useful for verification
- Editable fields: Rejected - should only be set by scoring service
- Separate admin page: Rejected - overengineering

## Risks / Trade-offs

**Risk:** Points field might need to change if rules updated (fractional points)  
**Mitigation:** IntegerField → DecimalField migration is straightforward. Document assumption in model.

**Risk:** Denormalized data (is_exact_match can be derived) could get out of sync  
**Mitigation:** Scoring service is sole writer. Can add validation check if needed.

**Trade-off:** Nullable fields complicate queries (need NULL checks)  
**Acceptance:** Worth it for semantic clarity. Can use Q objects: `Q(points_earned__isnull=False)`

**Trade-off:** No audit trail for when points were calculated  
**Acceptance:** `updated_at` timestamp shows when prediction was last modified. Add separate audit log if needed.

**Risk:** Large-scale rescoring if rules change requires updating all predictions  
**Mitigation:** Can write management command to recalculate. Keep scoring logic parameterized.

## Migration Plan

1. Add `points_earned` (IntegerField, nullable) to MatchPrediction model
2. Add `is_exact_match` (BooleanField, nullable) to MatchPrediction model
3. Generate and review migration
4. Run migration on development database
5. Update admin to show new fields as read-only
6. Update existing tests to assert new fields are NULL on creation
7. Add tests for setting these fields (simulating scoring service behavior)

No data migration needed - existing predictions will have NULL for new fields until scored.

## Open Questions

None - design aligns with deferred decision from previous change to add points caching when needed.
