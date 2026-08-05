## Context

The prediction system is in place with User, Match, MatchPrediction models. Users can make predictions with jokers, but no scoring or ranking exists yet. The Shortytipp game rules define a multi-tier scoring system (6 categories), round multipliers (x1/x2/x3), joker doubling, and Olympic-style ranking with tiebreakers. The system needs to calculate points automatically when match results are entered and maintain historical leaderboard snapshots for tracking progress over time.

## Goals / Non-Goals

**Goals:**
- Implement complete Shortytipp scoring logic as reusable service
- Calculate points automatically when match results entered
- Generate rankings with Olympic tiebreakers (points → exact matches → jokers used)
- Track historical leaderboard snapshots (daily/weekly)
- Export leaderboard as CSV and PDF
- Support manual recalculation for rule changes
- Track user statistics (total points, jokers used, exact match count)
- All rankings public (no privacy tiers)

**Non-Goals:**
- Real-time WebSocket leaderboard updates (future change)
- User notifications for rank changes (future change)
- Achievement badges system (future change)
- Round-specific leaderboards (just overall ranking)
- Head-to-head comparisons (future change)
- Prize/payout calculation automation (manual process)
- UI implementation (admin-only for now)

## Decisions

### 1. Service Layer Architecture

**Decision:** Create dedicated service modules in scoring app: `ScoringService` and `RankingService`.

**Rationale:**
- Scoring logic is complex (6 categories, precedence rules, multipliers)
- Business rules belong in service layer, not models or views
- Testable in isolation without database
- Reusable across admin, management commands, future API
- Clear separation: models store data, services calculate

**Alternatives considered:**
- Model methods: Rejected - couples business logic to data layer, hard to test
- Signals: Rejected - implicit behavior, debugging nightmare, no clear call chain
- View logic: Rejected - not reusable, violates DRY

### 2. Scoring Trigger: When to Calculate Points

**Decision:** Calculate points immediately when match `goals_home` and `goals_away` are set (via admin save).

**Rationale:**
- Immediate feedback for admins
- Avoids forgetting to run scoring
- Single source of truth (match result triggers scoring)
- Can still recalculate manually if needed

**Alternatives considered:**
- Manual command only: Rejected - error-prone, requires remembering
- Celery background task: Rejected - overengineering, adds complexity
- Scheduled cron job: Rejected - delay between result entry and score update

### 3. Scoring Service Design

**Decision:** Stateless service class with pure functions, no instance state.

```python
class ScoringService:
    @staticmethod
    def calculate_match_points(prediction, match) -> dict:
        # Returns {'points': int, 'is_exact': bool, 'base_points': int}
    
    @staticmethod
    def calculate_champion_points(user, champion_team) -> int:
    
    @staticmethod
    def score_all_predictions_for_match(match) -> int:
        # Returns count of scored predictions
```

**Rationale:**
- Pure functions easier to test
- No shared state = no threading issues
- Clear inputs/outputs = easier to reason about
- Static methods signal no instance state needed

### 4. Scoring Precedence Implementation

**Decision:** Use if-elif chain in documented precedence order (exact → tendency+diff → tendency+one_goal → tendency → one_goal → none).

**Rationale:**
- Matches Shortytipp rules exactly (section 2)
- Only one category applies (mutual exclusion)
- Early return prevents checking lower categories
- Easy to verify against rules document

**Alternatives considered:**
- Point-based system (sum all matches): Rejected - violates game rules
- Strategy pattern: Rejected - overengineering for 6 categories

### 5. Round Multiplier Mapping

**Decision:** Store multipliers as constants in `ScoringService`, map from `Match.round` field.

```python
ROUND_MULTIPLIERS = {
    'gs': 1,    # group stage
    'r32': 2,   # round of 32
    'r16': 2,   # round of 16
    'qf': 3,    # quarter-final
    'sf': 3,    # semi-final
    '3rd': 3,   # third place
    'f': 3,     # final
}
```

**Rationale:**
- Centralized configuration
- Easy to verify against rules
- No database reads for each calculation
- Can evolve to database model later if needed

**Alternatives considered:**
- Database model: Rejected - overkill for static data
- Match model method: Rejected - couples multiplier logic to data

### 6. Joker Multiplier Application

**Decision:** Formula: `final_points = base_points * round_multiplier * (2 if joker_active else 1)`

**Rationale:**
- Matches Shortytipp rules exactly (section 6)
- Joker doubles AFTER round multiplier
- Clear order of operations

### 7. Ranking Service Design

**Decision:** `RankingService` generates leaderboard by aggregating user statistics with Olympic tiebreakers.

```python
class RankingService:
    @staticmethod
    def get_current_leaderboard() -> List[dict]:
        # Returns sorted list with rank, user, points, exact_matches, jokers_used
    
    @staticmethod
    def create_snapshot() -> LeaderboardSnapshot:
        # Saves current rankings to history
```

**Rationale:**
- Ranking is derived from user statistics (no separate table needed)
- Tiebreakers: total_points → exact_match_count → jokers_used
- Shared rank for identical stats (per Shortytipp rules section 10)

### 8. User Statistics: Cached vs Calculated

**Decision:** Cache statistics on User model (`total_points`, `jokers_used`, `exact_match_count`) updated when predictions scored.

**Rationale:**
- Leaderboard queries need fast aggregations
- Avoids N+1 queries (user → predictions → sum)
- Trade-off: denormalized data for performance
- Statistics updated atomically with scoring

**Alternatives considered:**
- Calculate on-the-fly: Rejected - slow for leaderboard with many users
- Separate UserStatistics model: Rejected - 1:1 relationship, just add to User
- Materialized view: Rejected - PostgreSQL-specific, harder to test

### 9. LeaderboardSnapshot Model Design

**Decision:** Store snapshot of entire leaderboard at a point in time.

```python
class LeaderboardSnapshot(models.Model):
    created_at = DateTimeField(auto_now_add=True)
    snapshot_type = CharField(choices=['daily', 'weekly', 'final'])
    data = JSONField()  # [{rank, user_id, username, points, ...}]
```

**Rationale:**
- Historical tracking for trend analysis
- JSON field stores full rankings (no foreign keys needed)
- Immutable history (no CASCADE deletes if user deleted)
- Can query "who was #1 on 2026-06-15?"

**Alternatives considered:**
- LeaderboardEntry per user per snapshot: Rejected - creates too many rows
- No history: Rejected - user requested historical tracking
- Separate table per snapshot: Rejected - schema explosion

### 10. Snapshot Creation Strategy

**Decision:** Manual creation via management command, no automatic scheduling.

**Rationale:**
- Admins control when snapshots are taken
- No cron/Celery dependency
- Can snapshot after significant events (end of round, final)
- Simple to implement and understand

**Alternatives considered:**
- Daily cron job: Rejected - requires deployment infrastructure
- Celery periodic task: Rejected - adds heavy dependency
- Snapshot on every score change: Rejected - creates too many snapshots

### 11. Export Format Decision

**Decision:** CSV via Django's HttpResponse, PDF via ReportLab library.

**Rationale:**
- CSV: native Python, no dependencies, Excel-compatible
- PDF: ReportLab is standard Django choice, mature library
- Both generate on-the-fly (no file storage needed)
- Downloadable via admin or management command

**Alternatives considered:**
- Excel (xlsx): Rejected - requires openpyxl dependency, CSV sufficient
- HTML + print: Rejected - formatting issues, not portable
- Store generated files: Rejected - adds storage complexity

### 12. Champion Prediction Scoring

**Decision:** Score champion predictions automatically when final match is scored, after admin sets Team.is_champion.

**Context:**
- Shortytipp rules award champion prediction points: Category A (20 pts), Category B (30 pts)
- Team model has `is_champion` boolean field set by admin after final match result
- Final match is played in regular time (90 min) or extra time (120 min)
- For extra-time draws, `is_champion` field determines winner for scoring purposes
- Champion points awarded to users whose `predicted_champion` matches the team where `is_champion = True`

**Process:**
1. Admin enters final match result (goals_home, goals_away)
2. Admin determines final match winner:
   - If home team won (after 120 min): set home team `is_champion = True`
   - If away team won (after 120 min): set away team `is_champion = True`
   - If draw after 120 min: set `is_champion = True` on designated winner (if applicable)
3. Final match scoring triggered, which includes:
   - Score final match predictions (6-category scoring + x3 multiplier)
   - Query users where `User.predicted_champion.is_champion = True`
   - Award champion points based on team category (A: 20 pts, B: 30 pts)
   - Update user statistics

**Rationale:**
- Champion scoring depends on final match result AND admin designation
- Points only awarded once per tournament per user
- Final match scoring already triggers via Match.save() override
- No separate trigger needed; final match scoring encompasses both match + champion points
- Team.is_champion single source of truth

**Alternatives considered:**
- Manual separate command: Rejected - too many steps, error-prone
- Automatic from final match alone: Rejected - doesn't account for admin winner designation
- Separate admin action: Rejected - complicates workflow

### 13. Recalculation Strategy

**Decision:** Management command `recalculate_scores` that:
1. Clears all prediction points and user statistics
2. Iterates finished matches and recalculates
3. Scores champion predictions if champion set

**Rationale:**
- Clean slate prevents inconsistencies
- Idempotent (same result if run multiple times)
- Useful for rule changes or bug fixes
- Testable with fixtures

### 14. Admin Integration

**Decision:** Automatically score when Match.goals_home/goals_away saved in admin.

**Rationale:**
- No extra admin action needed
- Immediate visual feedback
- Override save() method in Match model to call scoring service
- Minimal code, maximum convenience

**Alternatives considered:**
- Admin action button: Rejected - extra click, easy to forget
- Signal on Match save: Rejected - implicit, harder to debug
- Separate admin view: Rejected - splits workflow

### 15. Tiebreaker Implementation

**Decision:** Use Django ORM ordering with multiple fields: `order_by('-total_points', '-exact_match_count', '-jokers_used')`.

**Rationale:**
- Database handles sorting efficiently
- Correct Olympic ranking naturally emerges
- Shared ranks handled by comparing adjacent users
- No manual sorting logic needed

### 16. Exact Match Count Tracking

**Decision:** Increment User.exact_match_count when prediction.is_exact_match = True.

**Rationale:**
- Needed for tiebreaker
- Cached for performance (leaderboard queries)
- Single source of truth (derived from predictions)
- Updated atomically with scoring

### 17. Jokers Used Count Tracking

**Decision:** Count via User.match_predictions.filter(joker_active=True, points_earned__isnull=False).count().

**Rationale:**
- Only count scored predictions with jokers (unscored don't affect tiebreaker)
- Not cached initially (query acceptable for tiebreaker edge case)
- Can cache later if performance issue

**Alternatives considered:**
- Cache on User model: Deferred - added complexity, tiebreaker is rare
- Recalculate every time: Accepted - query is fast

## Risks / Trade-offs

**Risk:** Scoring service complexity makes it hard to test all 6 categories  
**Mitigation:** Comprehensive test suite with edge cases from rules document. Each category has dedicated test.

**Risk:** Denormalized statistics (User.total_points) could get out of sync  
**Mitigation:** Recalculation command resets everything. Atomic updates when scoring. Can add integrity check.

**Risk:** Round multiplier misconfiguration breaks scoring  
**Mitigation:** Validate against rules document. Unit tests for each round. Constants are clear and documented.

**Risk:** Joker count tracking query might be slow  
**Mitigation:** Acceptable initially (tiebreaker is rare). Can cache on User model later if needed. Add index on joker_active.

**Risk:** LeaderboardSnapshot JSON field makes querying historical data hard  
**Mitigation:** Trade-off accepted - snapshots are for display, not complex queries. Can export snapshots for analysis.

**Trade-off:** Manual snapshot creation vs automatic  
**Acceptance:** Manual gives admins control. Tournament has clear milestones (end of round) for snapshots.

**Risk:** Scoring on Match save in admin could fail silently  
**Mitigation:** Wrap in try-except, log errors, show admin message if scoring fails.

**Risk:** Large number of predictions makes scoring slow  
**Mitigation:** Batch process per match (score_all_predictions_for_match). Can add progress indicator later.

**Trade-off:** CSV/PDF export in-memory vs file storage  
**Acceptance:** In-memory keeps it simple. Leaderboard is small (<100 users typically). Can add caching later.

## Migration Plan

1. Add fields to User model (total_points, jokers_used, exact_match_count)
2. Create LeaderboardSnapshot model
3. Generate and run migrations
4. Implement ScoringService with comprehensive tests
5. Implement RankingService with comprehensive tests
6. Add Match.save() override to trigger scoring
7. Create management commands (recalculate_scores, create_snapshot, export_leaderboard)
8. Update admin interfaces
9. Test with sample data and sample match results
10. Run recalculate_scores to populate existing data (if any)

No breaking changes - all additive.

## Open Questions

1. **Joker limit enforcement**: 8 or 10 total jokers? (PDF has discrepancy) → Keep configurable, don't hardcode
2. **Champion category assignment**: Who assigns teams to category A/B? → Admin decision, needs admin interface
3. **Snapshot frequency**: Daily, weekly, or on-demand only? → Start with on-demand, add scheduling later if needed
4. **Export permissions**: Admin-only or all users? → Start admin-only, can open later
