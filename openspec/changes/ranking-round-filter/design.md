## Architecture

### Overview

Round-based ranking filtering uses **dynamic calculation** rather than pre-computed snapshots. Since `MatchPrediction.points_earned` is already cached when matches are scored, aggregating by round is fast (<50ms for typical data volumes).

```
User Request
    ↓
RankingView (users/views.py)
    ↓
RankingService.get_leaderboard_up_to_round(round_code)
    ↓
Django ORM aggregation (filter by match.round)
    ↓
Sum(points_earned), Count(exact), Count(jokers)
    ↓
Sort by (total_points DESC, exact_match_count DESC, jokers_used ASC)
    ↓
Assign rank numbers (olympic-style)
    ↓
Return leaderboard data
    ↓
Template renders with HTMX
```

### Tournament Round Progression

```python
ROUND_ORDER = ['group', 'r32', 'r16', 'qf', 'sf', '3rd', 'final']
```

When filtering by round (e.g., `'r16'`), include all matches from rounds up to and including that round:
- `'group'` → only group stage matches
- `'r16'` → group + r32 + r16 matches
- `'final'` → all matches (same as Live)

### Service Layer Design

**New method in `RankingService`:**

```python
@staticmethod
def get_leaderboard_up_to_round(round_code: str | None = None) -> list[dict]:
    """
    Generate leaderboard including matches up to a specific round.
    
    Args:
        round_code: Tournament round ('group', 'r32', 'r16', 'qf', 'sf', '3rd', 'final')
                   If None, includes all finished matches (live view)
    
    Returns:
        List of dicts with: rank, user_id, username, total_points,
        exact_match_count, jokers_used
    """
    from django.db.models import Sum, Count, Q
    from users.models import User
    
    ROUND_ORDER = ['group', 'r32', 'r16', 'qf', 'sf', '3rd', 'final']
    
    # Determine which rounds to include
    if round_code and round_code in ROUND_ORDER:
        cutoff_index = ROUND_ORDER.index(round_code)
        included_rounds = ROUND_ORDER[:cutoff_index + 1]
    else:
        # Live: all rounds
        included_rounds = ROUND_ORDER
    
    # Build filter for matches in included rounds
    match_filter = Q(
        match_predictions__match__round__in=included_rounds,
        match_predictions__match__status='finished',
        match_predictions__points_earned__isnull=False,
    )
    
    # Aggregate user statistics
    users = User.objects.filter(is_active=True).annotate(
        total_points=Sum(
            'match_predictions__points_earned',
            filter=match_filter,
            default=0,
        ),
        exact_match_count=Count(
            'match_predictions',
            filter=match_filter & Q(match_predictions__is_exact_match=True),
        ),
        jokers_used=Count(
            'match_predictions',
            filter=match_filter & Q(match_predictions__joker_active=True),
        ),
    ).order_by(
        '-total_points',
        '-exact_match_count',
        'jokers_used',  # ASC: fewer used = better
    )
    
    # Convert to list and apply rank numbers
    user_list = list(users)
    return RankingService._calculate_rank_numbers(user_list)
```

**Refactor existing method:**

Current `get_current_leaderboard()` becomes a wrapper:

```python
@staticmethod
def get_current_leaderboard() -> list[dict]:
    """Generate live leaderboard (all finished matches)."""
    return RankingService.get_leaderboard_up_to_round(round_code=None)
```

This maintains backward compatibility while reusing the filtering logic.

### View Layer Design

**Modify `RankingView.get_context_data()`:**

```python
def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
    context = super().get_context_data(**kwargs)
    
    # Get round filter from query params
    round_filter = self.request.GET.get('round', None)
    
    # Validate round parameter
    valid_rounds = ['group', 'r32', 'r16', 'qf', 'sf', '3rd', 'final']
    if round_filter and round_filter not in valid_rounds:
        round_filter = None
    
    # Get filtered leaderboard
    leaderboard = RankingService.get_leaderboard_up_to_round(round_filter)
    
    # Enrich with champion data (as before)
    if leaderboard:
        user_ids = [entry["user_id"] for entry in leaderboard]
        users_dict = {
            user.pk: user
            for user in User.objects.filter(pk__in=user_ids).select_related(
                "predicted_champion"
            )
        }
        for entry in leaderboard:
            user = users_dict.get(entry["user_id"])
            if user:
                entry["predicted_champion"] = user.predicted_champion
                entry["country_code"] = user.country_code
    
    context["leaderboard"] = leaderboard
    context["selected_round"] = round_filter
    context["available_rounds"] = [
        {'code': 'group', 'label': 'Gruppe'},
        {'code': 'r32', 'label': 'Achtelfinale'},
        {'code': 'r16', 'label': 'Achtelfinale'},
        {'code': 'qf', 'label': 'Viertelfinale'},
        {'code': 'sf', 'label': 'Halbfinale'},
        {'code': '3rd', 'label': '3. Platz'},
        {'code': 'final', 'label': 'Finale'},
    ]
    
    return context
```

### Template Design

**Round filter UI:**

Add horizontal button bar above the ranking table, matching existing app style:

```html
<!-- Round filter controls -->
<div class="mb-6 flex flex-wrap gap-2 justify-center">
    <button 
        hx-get="{% url 'ranking' %}"
        hx-target="#ranking-content"
        hx-swap="outerHTML"
        class="px-4 py-2 rounded-lg transition-colors duration-200
               {% if not selected_round %}
                   bg-emerald-600 text-white
               {% else %}
                   bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300 
                   hover:bg-emerald-500 hover:text-white
               {% endif %}">
        Live
    </button>
    
    {% for round in available_rounds %}
    <button 
        hx-get="{% url 'ranking' %}?round={{ round.code }}"
        hx-target="#ranking-content"
        hx-swap="outerHTML"
        class="px-4 py-2 rounded-lg transition-colors duration-200
               {% if selected_round == round.code %}
                   bg-emerald-600 text-white
               {% else %}
                   bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300 
                   hover:bg-emerald-500 hover:text-white
               {% endif %}">
        {{ round.label }}
    </button>
    {% endfor %}
</div>

<!-- Ranking table (wrapped for HTMX swap) -->
<div id="ranking-content">
    {% if selected_round %}
    <div class="text-center mb-4 text-sm text-zinc-500 dark:text-zinc-400">
        Rangliste nach: <span class="font-semibold">{{ selected_round|get_round_label }}</span>
    </div>
    {% endif %}
    
    <!-- Existing table markup -->
    ...
</div>
```

**HTMX behavior:**

- Clicking a round button makes a GET request to `/ranking/?round=<code>`
- Response swaps `#ranking-content` div with updated leaderboard
- No full page reload
- URL updates to reflect filter state (browser back button works)

### Champion Prediction Display

For historical round views, display the **current** `user.predicted_champion`. This is accurate because:

1. Champion predictions lock at first match kickoff (per game rules)
2. After tournament starts, current = historical
3. Simpler than tracking champion changes over time
4. Matches admin snapshot behavior

### Performance Considerations

**Query optimization:**

```sql
-- Single aggregation query (fast due to indexed fields)
SELECT 
    user_id,
    username,
    SUM(points_earned) as total_points,
    COUNT(CASE WHEN is_exact_match THEN 1 END) as exact_count,
    COUNT(CASE WHEN joker_active THEN 1 END) as jokers
FROM users_user
LEFT JOIN predictions_matchprediction 
    ON users_user.id = predictions_matchprediction.user_id
LEFT JOIN matches_match
    ON predictions_matchprediction.match_id = matches_match.id
WHERE 
    matches_match.round IN ('group', 'r32', 'r16')
    AND matches_match.status = 'finished'
    AND predictions_matchprediction.points_earned IS NOT NULL
GROUP BY user_id
ORDER BY total_points DESC, exact_count DESC, jokers ASC
```

**Expected performance:**
- 100 users × 104 matches = 10,400 predictions
- Aggregation with indexed foreign keys: ~20-50ms
- Acceptable for interactive use

**Future optimization (if needed):**
- Add database index on `(match.round, match.status)`
- Cache round-based results with short TTL (5 minutes)

### Error Handling

- Invalid round parameter → ignore, show live view
- No finished matches in round → show empty state
- Database errors → log and show error message to user

### Testing Strategy

**Service tests (`scoring/tests/test_ranking_service.py`):**
- Test filtering by each round
- Test round progression (group < r16 < final)
- Test olympic ranking with filtered data
- Test empty results for rounds with no finished matches
- Test invalid round parameter handling

**View tests (`users/tests/test_views.py`):**
- Test GET with valid round parameter
- Test GET with invalid round parameter
- Test GET without round parameter (default live)
- Test context data contains selected_round
- Test HTMX partial response

**Integration tests:**
- Score predictions for different rounds
- Verify filtered leaderboards match expected values
- Test that live view includes all rounds

### Migration Strategy

No database migrations required. This is a pure logic and UI change.

### Rollback Plan

If issues arise:
1. Revert template changes (remove filter UI)
2. Revert view changes (remove round parameter handling)
3. Service changes are backward compatible (existing code still works)

### Future Enhancements (Out of Scope)

- Date-based filtering
- Comparison view (two rounds side-by-side)
- Per-user trend graphs
- Export filtered ranking as CSV
