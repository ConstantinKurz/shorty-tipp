## Context

We have User, Team, and Match models implemented. Users need to make predictions for matches and select a champion before the tournament starts. The prediction system must support the WM 2026 tipping game rules including jokers, group stage limits (36 matches max), and champion predictions with category-based scoring.

## Goals / Non-Goals

**Goals:**
- Add champion prediction to User model (one per user)
- Create MatchPrediction model for match result predictions
- Support joker functionality (double points)
- Enable unique constraint (one prediction per user per match)
- Prepare data structure for scoring calculations

**Non-Goals:**
- Implementing scoring logic (separate change)
- Enforcing joker limits per round (view-level validation, not model)
- Enforcing 36 group-stage prediction limit (view-level validation)
- Champion prediction deadlines (view-level enforcement)
- UI for entering predictions (admin-only for now)

## Decisions

### 1. Champion Prediction: ForeignKey on User vs. Separate Model

**Decision:** Add `predicted_champion` as ForeignKey on User model.

**Rationale:**
- One champion prediction per user → natural 1:1 relationship
- Simpler than separate ChampionPrediction model
- Easy queries: `user.predicted_champion` and `team.champion_predictions.all()`
- Nullable field allows users who haven't predicted yet

**Alternatives considered:**
- Separate ChampionPrediction model with OneToOneField: Rejected - adds unnecessary complexity for 1:1 data
- ManyToMany: Rejected - game rules allow only one champion prediction per user

### 2. MatchPrediction unique constraint

**Decision:** Use `unique_together = ['user', 'match']` at database level.

**Rationale:**
- Prevents duplicate predictions
- Database enforces integrity
- Clear error message for duplicates

### 3. Joker tracking

**Decision:** Simple BooleanField on MatchPrediction, no separate JokerUsage model.

**Rationale:**
- Jokers are per-prediction, not global counters
- Can query joker usage: `MatchPrediction.objects.filter(user=user, match__round='qf', joker_active=True).count()`
- Limits enforced in views/forms, not database
- Game rules might change (8 vs 10 jokers unclear) → keep flexible

**Alternatives considered:**
- Separate JokerUsage model tracking limits per round: Rejected - overengineering, can calculate dynamically
- IntegerField counting jokers used: Rejected - doesn't show which matches have jokers

### 4. Points caching

**Decision:** No points_earned field on MatchPrediction initially.

**Rationale:**
- Keep models simple
- Calculate on-the-fly for now
- Can add caching later if performance requires it
- Easier to recalculate if rules change

**Alternatives considered:**
- Cache points_earned as IntegerField: Deferred - premature optimization, can add later

### 5. Timestamp tracking

**Decision:** Add created_at and updated_at to MatchPrediction.

**Rationale:**
- Track when prediction was made (useful for deadline enforcement)
- Track when prediction was last changed
- Standard Django pattern

### 6. Cascade behavior

**Decision:**
- User deleted → CASCADE (delete predictions)
- Match deleted → CASCADE (delete predictions)
- Team deleted (for predicted_champion) → SET_NULL (keep user, clear champion)

**Rationale:**
- User predictions belong to user → delete with user
- Match predictions for deleted match are meaningless → delete
- Champion prediction is optional → can be null if team deleted (edge case)

## Risks / Trade-offs

**Risk:** No validation preventing user from predicting after match start  
**Mitigation:** Enforced in views/forms, not model-level. Can add model clean() later if needed.

**Risk:** No validation on joker limits per round  
**Mitigation:** Enforced in views when creating/updating predictions. Business logic, not data integrity.

**Risk:** No validation on 36 group-stage prediction limit  
**Mitigation:** Enforced in views. Can query count before allowing new prediction.

**Trade-off:** predicted_champion nullable on User  
**Acceptance:** Not all users will predict champion immediately. Nullable is correct semantics.

**Trade-off:** No champion prediction deadline tracking  
**Acceptance:** Deadline is global (before first match), not per-user. View-level check.

## Migration Plan

1. Create migration adding predicted_champion to User model
2. Create migration for MatchPrediction model
3. Run migrations on development database
4. No data migration needed (greenfield)
5. Populate via admin for testing

## Open Questions

None - design is clear and aligned with game rules.
