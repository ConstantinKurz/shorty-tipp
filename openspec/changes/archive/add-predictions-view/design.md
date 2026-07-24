# Design: Add Predictions View

## Overview

This design describes a single-page predictions interface with inline editing, auto-save via HTMX, and server-side enforcement of joker/prediction limits. Following Django patterns established in the codebase (see `users/views.py` for `RankingView`).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         URL ROUTING                                  │
├─────────────────────────────────────────────────────────────────────┤
│  /predictions/                      → PredictionListView            │
│  /predictions/<match_id>/save/      → PredictionSaveView (HTMX)     │
│  /predictions/<match_id>/delete/    → PredictionDeleteView (HTMX)   │
│  /predictions/<match_id>/joker/     → PredictionJokerView (HTMX)    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           VIEWS                                      │
├─────────────────────────────────────────────────────────────────────┤
│  PredictionListView (LoginRequiredMixin, TemplateView)              │
│  ├─ Lists ALL matches ordered by kickoff                            │
│  ├─ Shows match results (if finished)                               │
│  ├─ Shows user predictions with points earned                       │
│  └─ Inline forms for each match                                     │
│                                                                     │
│  PredictionSaveView (LoginRequiredMixin, View)                      │
│  ├─ POST only, HTMX endpoint                                        │
│  ├─ Validates locktime, joker limit, group-stage limit              │
│  └─ Returns updated match row partial                               │
│                                                                     │
│  PredictionDeleteView (LoginRequiredMixin, View)                    │
│  ├─ POST only, HTMX endpoint                                        │
│  ├─ Validates locktime                                              │
│  └─ Returns cleared match row partial                               │
│                                                                     │
│  PredictionJokerView (LoginRequiredMixin, View)                     │
│  ├─ POST only, HTMX endpoint                                        │
│  ├─ Validates locktime and joker limit                              │
│  └─ Returns updated match row partial                               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SERVICES                                     │
├─────────────────────────────────────────────────────────────────────┤
│  PredictionLimitService                                             │
│  ├─ can_add_group_stage_prediction(user) → bool                     │
│  ├─ get_group_stage_prediction_count(user) → int                    │
│  ├─ can_add_joker(user, round) → bool                               │
│  ├─ get_joker_count_for_round(user, round) → int                    │
│  └─ get_joker_limit_for_round(round) → int                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          MODELS                                      │
├─────────────────────────────────────────────────────────────────────┤
│  MatchPrediction (existing)                                         │
│  ├─ user, match, predicted_goals_home/away                          │
│  ├─ joker_active, points_earned, is_exact_match                     │
│  └─ created_at, updated_at                                          │
│                                                                     │
│  Match (existing)                                                   │
│  ├─ team_home, team_away, kickoff, round                            │
│  └─ goals_home, goals_away, is_finished                             │
└─────────────────────────────────────────────────────────────────────┘
```

## User Interaction Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PREDICTION FLOW                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  User types goals         Both fields filled?                       │
│       │                         │                                   │
│       ▼                         ▼                                   │
│  [2] [_]  ──────────────▶  No  (wait)                               │
│  [2] [1]  ──────────────▶  Yes ──▶ HTMX POST /save/                 │
│                                         │                           │
│                                         ▼                           │
│                               Server validates:                     │
│                               ├─ Locktime OK?                       │
│                               ├─ Group limit OK?                    │
│                               └─ Save prediction                    │
│                                         │                           │
│                                         ▼                           │
│                               Return updated row                    │
│                               (show points, status)                 │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                       JOKER TOGGLE FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  User clicks joker toggle                                           │
│       │                                                             │
│       ▼                                                             │
│  HTMX POST /joker/                                                  │
│       │                                                             │
│       ▼                                                             │
│  Server validates:                                                  │
│  ├─ Locktime OK?                                                    │
│  ├─ Prediction exists?                                              │
│  ├─ Joker limit for round OK? (if enabling)                         │
│  └─ Toggle joker_active                                             │
│       │                                                             │
│       ▼                                                             │
│  Return updated row (show ⭐ indicator)                              │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                       DELETE FLOW                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  User clicks 🗑️ icon                                                 │
│       │                                                             │
│       ▼                                                             │
│  HTMX POST /delete/                                                 │
│       │                                                             │
│       ▼                                                             │
│  Server validates:                                                  │
│  ├─ Locktime OK?                                                    │
│  └─ Delete prediction                                               │
│       │                                                             │
│       ▼                                                             │
│  Return cleared row (empty inputs)                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. PredictionListView

**Purpose**: Display all matches with inline prediction forms.

**Template**: `predictions/prediction_list.html`

**Context Data**:
- `matches`: List of all matches ordered by kickoff, annotated with:
  - Match data (teams, kickoff, round, result if finished)
  - User's prediction (if exists) with points earned
  - `is_locked`: Boolean if kickoff has passed
  - `can_add_joker`: Boolean if joker limit not reached for this round
  - `joker_count_for_round`: Current joker usage
  - `joker_limit_for_round`: Max jokers allowed
- `group_stage_count`: Current group stage predictions
- `group_stage_limit`: 36

**Query Strategy**:
```python
# Get all matches ordered by kickoff
matches = Match.objects.all().select_related(
    'team_home', 'team_away'
).order_by('kickoff')

# Get user's predictions
predictions = MatchPrediction.objects.filter(
    user=request.user
).select_related('match')

# Build prediction lookup
prediction_map = {p.match_id: p for p in predictions}
```

### 2. PredictionSaveView (HTMX)

**Purpose**: Create or update prediction via HTMX.

**URL**: `POST /predictions/<match_id>/save/`

**Request Data** (form-encoded):
- `predicted_goals_home`: int
- `predicted_goals_away`: int

**Validation**:
1. Match exists (404 if not)
2. Locktime not passed (400 if locked)
3. Goals valid (>= 0, <= 99)
4. Group stage limit not exceeded (if new prediction for group match)

**Response**: HTML partial of updated match row.

### 3. PredictionDeleteView (HTMX)

**Purpose**: Delete existing prediction.

**URL**: `POST /predictions/<match_id>/delete/`

**Validation**:
1. Match exists (404 if not)
2. Locktime not passed (400 if locked)
3. Prediction exists (404 if not)

**Response**: HTML partial of cleared match row.

### 4. PredictionJokerView (HTMX)

**Purpose**: Toggle joker on existing prediction.

**URL**: `POST /predictions/<match_id>/joker/`

**Validation**:
1. Match exists (404 if not)
2. Locktime not passed (400 if locked)
3. Prediction exists (400 if not - must have prediction first)
4. If enabling: joker limit for round not exceeded
5. If round is 'gs': jokers not allowed (400)

**Response**: HTML partial of updated match row.

### 5. PredictionLimitService

**Location**: `predictions/services.py`

```python
class PredictionLimitService:
    """Service for checking prediction and joker limits."""
    
    # Joker limits per round (configurable)
    JOKER_LIMITS = {
        'gs': 0,      # No jokers in group stage
        'r32': 3,
        'r16': 3,
        'qf': 2,
        'sf': 2,      # sf + final + third share pool of 2
        'final': 2,   # Combined with sf
        'third': 2,   # Combined with sf
    }
    
    # Combined rounds that share joker pool
    COMBINED_ROUNDS = {'sf', 'final', 'third'}
    
    GROUP_STAGE_LIMIT = 36
    
    @classmethod
    def get_joker_limit_for_round(cls, round_code: str) -> int:
        """Get max jokers allowed for a round."""
        return cls.JOKER_LIMITS.get(round_code, 0)
    
    @classmethod
    def get_joker_count_for_round(cls, user, round_code: str) -> int:
        """Count jokers user has set in a round (or combined rounds)."""
        if round_code in cls.COMBINED_ROUNDS:
            rounds = list(cls.COMBINED_ROUNDS)
        else:
            rounds = [round_code]
        
        return MatchPrediction.objects.filter(
            user=user,
            match__round__in=rounds,
            joker_active=True
        ).count()
    
    @classmethod
    def can_add_joker(cls, user, round_code: str) -> bool:
        """Check if user can add another joker in this round."""
        limit = cls.get_joker_limit_for_round(round_code)
        current = cls.get_joker_count_for_round(user, round_code)
        return current < limit
    
    @classmethod
    def get_group_stage_prediction_count(cls, user) -> int:
        """Count user's group stage predictions."""
        return MatchPrediction.objects.filter(
            user=user,
            match__round='gs'
        ).count()
    
    @classmethod
    def can_add_group_stage_prediction(cls, user) -> bool:
        """Check if user can add another group stage prediction."""
        return cls.get_group_stage_prediction_count(user) < cls.GROUP_STAGE_LIMIT
```

## Template Design

### prediction_list.html (Main View)

```
┌─────────────────────────────────────────────────────────────────────┐
│  🎯 Meine Tipps                          Gruppenphase: 12/36        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ── 15. Juni 2026 ─────────────────────────────────────────────     │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 18:00  🇩🇪 Germany  [2]:[1]  Brazil 🇧🇷   ⭐ 🗑️              │  │
│  │        Ergebnis: 2:1  │  +12 Punkte (6×1×2)                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 21:00  🇫🇷 France   [_]:[_]  Spain 🇪🇸    ☐ 🗑️               │  │
│  │        Noch nicht gespielt                                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ── 16. Juni 2026 ─────────────────────────────────────────────     │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 🔒 15:00  🇮🇹 Italy  [1]:[1]  England 🏴󠁧󠁢󠁥󠁮󠁧󠁿                    │  │
│  │           Ergebnis: 0:2  │  +1 Punkt                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Match Row Partial (prediction_row.html)

Used for HTMX swap responses:

```html
<div id="match-{{ match.id }}" class="...">
  <span class="time">{{ match.kickoff|time:"H:i" }}</span>
  
  <!-- Teams -->
  <span>{{ match.team_home.flag }} {{ match.team_home.name }}</span>
  
  <!-- Prediction inputs (disabled if locked) -->
  <input name="goals_home" value="{{ prediction.predicted_goals_home }}"
         hx-post="/predictions/{{ match.id }}/save/"
         hx-trigger="change delay:500ms"
         hx-target="#match-{{ match.id }}"
         hx-swap="outerHTML"
         {% if is_locked %}disabled{% endif %}>
  <span>:</span>
  <input name="goals_away" ...>
  
  <span>{{ match.team_away.name }} {{ match.team_away.flag }}</span>
  
  <!-- Joker toggle (if not group stage) -->
  {% if match.round != 'gs' %}
  <button hx-post="/predictions/{{ match.id }}/joker/"
          hx-target="#match-{{ match.id }}"
          {% if is_locked %}disabled{% endif %}>
    {% if prediction.joker_active %}⭐{% else %}☆{% endif %}
  </button>
  {% endif %}
  
  <!-- Delete button -->
  {% if prediction and not is_locked %}
  <button hx-post="/predictions/{{ match.id }}/delete/"
          hx-target="#match-{{ match.id }}">🗑️</button>
  {% endif %}
  
  <!-- Result and points (if finished) -->
  {% if match.is_finished %}
  <div>Ergebnis: {{ match.goals_home }}:{{ match.goals_away }}</div>
  {% if prediction.points_earned is not None %}
  <div>+{{ prediction.points_earned }} Punkte</div>
  {% endif %}
  {% endif %}
</div>
```

## HTMX Integration

**Auto-save Logic** (JavaScript):
```javascript
// Only trigger save when BOTH fields have values
document.querySelectorAll('.prediction-input').forEach(input => {
  input.addEventListener('change', function() {
    const row = this.closest('.match-row');
    const homeInput = row.querySelector('[name="goals_home"]');
    const awayInput = row.querySelector('[name="goals_away"]');
    
    if (homeInput.value !== '' && awayInput.value !== '') {
      // Trigger HTMX request
      htmx.trigger(this, 'save');
    }
  });
});
```

## Error Handling

| Scenario | Response |
|----------|----------|
| Match not found | 404 Not Found |
| Match locked (kickoff passed) | 400 with error message partial |
| Group stage limit exceeded | 400 with error message partial |
| Joker limit exceeded | 400 with error message partial |
| Joker on group stage | 400 with error message partial |
| No prediction for joker toggle | 400 with error message |
| Invalid goal values | 400 with validation error |

Error responses return HTMX-compatible partials that show inline error messages.

## Security Considerations

1. **Authentication**: All views require `LoginRequiredMixin`
2. **Authorization**: Users can only modify their own predictions
3. **Locktime**: Server-side enforcement on every request
4. **Limits**: Server-side enforcement of joker and prediction limits
5. **CSRF**: HTMX requests include CSRF token
6. **Input Validation**: All inputs validated server-side

## Testing Strategy

1. **Service Tests** (`test_services.py`):
   - Joker limit calculation per round
   - Combined rounds (sf/final/third) share limit
   - Group stage prediction count
   - Limit enforcement edge cases

2. **View Tests** (`test_views.py`):
   - Authentication required
   - List shows all matches ordered by kickoff
   - Save creates new prediction
   - Save updates existing prediction
   - Save rejected after locktime
   - Save rejected when group limit exceeded
   - Delete removes prediction
   - Delete rejected after locktime
   - Joker toggle works
   - Joker rejected in group stage
   - Joker rejected when limit exceeded
   - Points displayed correctly

3. **Integration Tests**:
   - Full HTMX flow simulation
