## Context

The Django tipping app currently has empty `matches` app. We need to add Team and Match models to represent the WM 2026 tournament structure. The User model already exists from initial setup. Prediction model will come in a future change.

## Goals / Non-Goals

**Goals:**
- Create Team model for tournament participants
- Create Match model with proper relationships to teams
- Enable admin data entry for teams and matches
- Prepare structure for future Prediction model (User → Predictions relationship)

**Non-Goals:**
- Prediction model implementation (separate change)
- Frontend UI for users (admin-only for now)
- Scoring logic
- Match schedule generation
- Real-time updates

## Decisions

### 1. Model Location: matches app

**Decision:** Put Team and Match models in the `matches` app.

**Rationale:**
- Teams only exist in context of matches
- Logical grouping: tournament structure belongs together
- Matches app was created in initial setup for this purpose

**Alternatives considered:**
- Separate `tournament` app: Rejected - adds unnecessary complexity
- `teams` app: Rejected - teams are just part of match structure

### 2. Team Model Fields

**Decision:** Minimal fields - name, FIFA code, group.

**Rationale:**
- Enough to identify teams
- Group assignment needed for game rules (36-match limit per group)
- Can extend later if needed (flags, rankings, etc.)

**Fields:**
```python
name: CharField(max_length=100) # e.g., "Germany"
fifa_code: CharField(max_length=3, unique=True) # e.g., "GER"  
group: CharField(max_length=1, choices=A-H) # e.g., "A"
```

### 3. Match Model Relationships

**Decision:** Use ForeignKey for team relationships, not ManyToMany.

**Rationale:**
- A match has exactly 2 teams (home/away)
- ForeignKey makes this explicit
- Related name allows Team → matches queryset

**Relationships:**
```python
team_home: ForeignKey(Team, related_name='home_matches')
team_away: ForeignKey(Team, related_name='away_matches')
```

**Alternatives considered:**
- ManyToMany: Rejected - doesn't enforce "exactly 2 teams"
- Generic relationship: Rejected - overkill for simple case

### 4. Match Result Storage

**Decision:** Nullable integer fields for goals, status field for match state.

**Rationale:**
- Simple and clear
- NULL means "not played yet"
- Supports game rules (extra time counted, penalties not)

**Fields:**
```python
goals_home: IntegerField(null=True, blank=True)
goals_away: IntegerField(null=True, blank=True)
status: CharField(choices=['scheduled', 'finished', 'live'])
```

### 5. Tournament Round Tracking

**Decision:** CharField with choices for round.

**Rationale:**
- Game rules have different multipliers per round
- Explicit choices prevent typos
- Easy to query "all group stage matches"

**Choices:**
```python
ROUND_CHOICES = [
    ('group', 'Group Stage'),
    ('r32', 'Round of 32'),
    ('r16', 'Round of 16'),  
    ('qf', 'Quarter-Final'),
    ('sf', 'Semi-Final'),
    ('3rd', 'Third Place'),
    ('final', 'Final'),
]
```

### 6. Match DateTime Handling

**Decision:** Use DateTimeField with timezone support.

**Rationale:**
- USE_TZ=True already set in settings
- Handles different timezones correctly
- Can display in user's local time later

**Field:**
```python
kickoff: DateTimeField() # Match start time
```

## Risks / Trade-offs

**Risk:** Model schema changes after users start making predictions  
**Mitigation:** Keep models simple, use migrations carefully, test thoroughly before predictions

**Risk:** Missing fields discovered later (e.g., venue, referee)  
**Mitigation:** Acceptable - can add fields in future migrations without breaking existing data

**Trade-off:** No validation that team_home != team_away  
**Mitigation:** Add model clean() method or database constraint in future if needed

**Trade-off:** Round choices hardcoded  
**Acceptance:** WM 2026 structure is fixed, no need for dynamic configuration

## Migration Plan

1. Create models
2. Generate migrations
3. Run migrations on dev database
4. Populate via admin (48 teams, matches TBD)
5. No data migration needed (greenfield)

## Open Questions

None - design is clear for this focused change.
