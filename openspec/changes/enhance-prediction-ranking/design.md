# Design: Enhanced Prediction Ranking View

## Overview

Extend the existing `MatchPredictionsView` to include aggregated user statistics (champion prediction, exact predictions count, jokers used, total points) and add a sorting parameter to toggle between match-specific and total points ranking. Use HTMX for dynamic re-sorting without full page reloads.

## Architecture

### Data Flow

```
User clicks match row
    │
    └─► HTMX GET /predictions/match/<id>/?sort=match (default)
            │
            ├─► Fetch match predictions
            ├─► Aggregate user statistics (champion, exact count, jokers, total points)
            ├─► Apply Olympic-style ranking based on sort parameter
            └─► Return match_predictions.html partial
                    │
                    └─► Bottom sheet displays with statistics and sort toggle
                            │
User clicks sort toggle
    │
    └─► HTMX GET /predictions/match/<id>/?sort=total
            │
            └─► Re-rank and re-render with new sort order
```

### Query Optimization

All user statistics must be fetched efficiently to avoid N+1 queries:

```python
# Single query to get all necessary data
users_with_stats = User.objects.filter(is_active=True).annotate(
    total_points=Coalesce(Sum('matchprediction__points_earned'), 0),
    exact_predictions_count=Count(
        'matchprediction',
        filter=Q(matchprediction__points_earned=6)
    ),
    jokers_used_count=Count(
        'matchprediction',
        filter=Q(matchprediction__joker_used=True)
    )
).select_related('predicted_champion')
```

## Implementation Details

### 1. Update MatchPredictionsView (predictions/views.py)

Extend the view to:

- Accept `sort` query parameter (`match` or `total`, default `match`)
- Annotate users with aggregated statistics
- Apply ranking based on sort mode
- Pass sort mode to template for toggle state

```python
class MatchPredictionsView(LoginRequiredMixin, View):
    """Return all predictions for a match with user statistics and flexible sorting."""

    def get(self, request, match_id: int):
        match = get_object_or_404(Match, pk=match_id)
        sort_mode = request.GET.get('sort', 'match')  # 'match' or 'total'
        
        User = get_user_model()
        
        # Fetch users with aggregated statistics
        users_with_stats = User.objects.filter(is_active=True).annotate(
            total_points=Coalesce(Sum('matchprediction__points_earned'), 0),
            exact_predictions_count=Count(
                'matchprediction',
                filter=Q(matchprediction__points_earned=6)
            ),
            jokers_used_count=Count(
                'matchprediction',
                filter=Q(matchprediction__joker_used=True)
            )
        ).select_related('predicted_champion')
        
        # Fetch predictions for this match
        predictions_by_user = {
            p.user_id: p
            for p in MatchPrediction.objects.filter(match=match).select_related('user')
        }
        
        # Build user list with predictions and stats
        user_predictions = []
        for user in users_with_stats:
            pred = predictions_by_user.get(user.id)
            user_predictions.append({
                'user': user,
                'prediction': pred,
                'match_points': pred.points_earned if pred else 0,
                'champion': user.predicted_champion.name if user.predicted_champion else '—',
                'exact_count': user.exact_predictions_count,
                'jokers_count': user.jokers_used_count,
                'total_points': user.total_points,
            })
        
        # Sort based on mode
        if sort_mode == 'total':
            # Sort by total points (desc), then username
            user_predictions.sort(
                key=lambda x: (-x['total_points'], x['user'].username)
            )
        else:
            # Sort by match points (desc), then has_predicted, then username
            user_predictions.sort(
                key=lambda x: (
                    -x['match_points'],
                    x['prediction'] is not None,
                    x['user'].username
                )
            )
        
        # Apply Olympic-style ranking based on sort criterion
        current_rank = 1
        prev_value = None
        users_at_rank = 0
        
        sort_key = 'total_points' if sort_mode == 'total' else 'match_points'
        
        for entry in user_predictions:
            value = entry[sort_key]
            
            if prev_value is not None and value < prev_value:
                current_rank += users_at_rank
                users_at_rank = 1
            else:
                users_at_rank += 1
            
            entry['rank'] = current_rank
            prev_value = value
        
        context = {
            'match': match,
            'user_predictions': user_predictions,
            'current_user': request.user,
            'sort_mode': sort_mode,
        }
        
        return render(
            request,
            'predictions/partials/match_predictions.html',
            context
        )
```

### 2. Update Template (templates/predictions/partials/match_predictions.html)

Add:

- Sort toggle above the predictions list
- Additional columns/fields for champion, exact count, jokers, total points
- HTMX attributes on toggle for dynamic re-sorting
- Visual indication of active sort mode

Structure:

```html
<div class="bottom-sheet-content">
    <!-- Match header (existing) -->
    <div class="match-header">
        <h3>{{ match.home_team }} vs {{ match.away_team }}</h3>
        {% if match.result %}
            <p>Result: {{ match.home_goals }}:{{ match.away_goals }}</p>
        {% endif %}
    </div>
    
    <!-- Sort toggle (new) -->
    <div class="sort-toggle" role="group">
        <button
            class="sort-btn {% if sort_mode == 'match' %}active{% endif %}"
            hx-get="{% url 'match-predictions' match.id %}?sort=match"
            hx-target="#bottom-sheet-content"
            hx-swap="innerHTML"
        >
            Match Points
        </button>
        <button
            class="sort-btn {% if sort_mode == 'total' %}active{% endif %}"
            hx-get="{% url 'match-predictions' match.id %}?sort=total"
            hx-target="#bottom-sheet-content"
            hx-swap="innerHTML"
        >
            Total Points
        </button>
    </div>
    
    <!-- Predictions list with enhanced statistics -->
    <div class="predictions-list">
        {% for entry in user_predictions %}
            <div class="prediction-row {% if entry.user.id == current_user.id %}current-user{% endif %}">
                <div class="rank">{{ entry.rank }}</div>
                <div class="user-info">
                    <div class="username">{{ entry.user.username }}</div>
                    <div class="stats-line">
                        <span class="stat" title="Champion">🏆 {{ entry.champion }}</span>
                        <span class="stat" title="Exact predictions">✓ {{ entry.exact_count }}</span>
                        <span class="stat" title="Jokers used">⭐ {{ entry.jokers_count }}</span>
                        <span class="stat" title="Total points">Σ {{ entry.total_points }}</span>
                    </div>
                </div>
                <div class="prediction-info">
                    {% if entry.prediction %}
                        <div class="prediction-score">
                            {{ entry.prediction.home_goals }}:{{ entry.prediction.away_goals }}
                            {% if entry.prediction.joker_used %}⭐{% endif %}
                        </div>
                        <div class="points">{{ entry.match_points }} pts</div>
                    {% else %}
                        <div class="no-prediction">No prediction</div>
                    {% endif %}
                </div>
            </div>
        {% endfor %}
    </div>
</div>
```

### 3. Styling Updates (static/css or inline)

Add styles for:

- Sort toggle buttons (pill-style, active state)
- Statistics line layout (compact icons + numbers)
- Mobile-responsive layout adjustments
- Subtle visual differentiation when sorted by total vs match

```css
.sort-toggle {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    padding: 0.5rem;
    background: var(--bg-secondary);
    border-radius: 0.5rem;
}

.sort-btn {
    flex: 1;
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 0.25rem;
    background: transparent;
    cursor: pointer;
    transition: all 0.2s;
}

.sort-btn.active {
    background: var(--primary);
    color: white;
}

.stats-line {
    display: flex;
    gap: 0.75rem;
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
}

.stat {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}
```

### 4. HTMX Configuration

The sort toggle uses HTMX attributes:

- `hx-get`: URL with sort query parameter
- `hx-target`: Container to update
- `hx-swap`: Replace innerHTML for smooth transition

No custom JavaScript needed beyond HTMX.

## Data Model Changes

No database schema changes required. All statistics are computed via Django ORM aggregation.

## Performance Considerations

- Single annotated query fetches all user statistics efficiently
- Predictions for the match fetched separately (already filtered)
- Sorting done in Python (small dataset: active users only)
- No additional queries inside loops

Expected query count:
1. Fetch users with aggregated stats (1 query)
2. Fetch match predictions (1 query)
3. Fetch match details (already in view, 1 query)

Total: 3 queries regardless of user count.

## Testing Strategy

- Unit tests for ranking algorithm with both sort modes
- View tests for sort parameter handling
- Template tests for correct display of statistics
- Integration tests for HTMX re-sorting behavior

## Migration Path

This is a non-breaking enhancement:

- Existing match predictions view URL remains unchanged
- Default sort mode (`match`) preserves current behavior
- New statistics displayed additively
- No data migration required

## Security Considerations

- All statistics are public to logged-in users (per existing design)
- No new data access concerns
- Sort parameter validated (only `match` or `total` accepted)
