# Design: HTMX Auto-Updates for Match Predictions Page

## Overview

Implement HTMX polling on the match predictions page by:
1. Creating a new update endpoint that returns a partial template
2. Extracting the predictions list into a reusable partial
3. Adding HTMX polling attributes to the full page template
4. Reusing existing polling interval logic from predictions list

## Architecture

### Request Flow

```
User loads /predictions/match/<id>/all/
    ↓
Full page rendered with initial data
    ↓
HTMX polling starts (every 1s or 60s)
    ↓
GET /predictions/match/<id>/updates/?sort=<mode>&from=<origin>
    ↓
Server re-queries predictions and rankings
    ↓
Returns HTML partial with updated content
    ↓
HTMX swaps content in place (preserves scroll)
    ↓
Repeat polling
```

### URL Structure

**Full page:**
```
GET /predictions/match/<int:match_id>/all/
Query params: ?sort=match|total&from=home|predictions
```

**Update endpoint:**
```
GET /predictions/match/<int:match_id>/updates/
Query params: ?sort=match|total
Returns: HTML partial (predictions list only)
```

## Component Changes

### 1. New Update View

**File:** `predictions/views.py`

Add a new view class after `MatchPredictionsView`:

```python
class MatchPredictionsUpdateView(LoginRequiredMixin, View):
    """
    Return updated predictions list for HTMX polling.
    
    Returns only the predictions content partial, not the full page.
    Used for live updates on the match predictions page.
    """
    
    def get(self, request: HttpRequest, match_id: int) -> HttpResponse:
        match = get_object_or_404(
            Match.objects.select_related("team_home", "team_away"),
            pk=match_id,
        )
        
        # Get sort mode from query params
        sort_mode = request.GET.get("sort", "match")
        if sort_mode not in ("match", "total"):
            sort_mode = "match"
        
        # Build user predictions list (same logic as MatchPredictionsView)
        # ... [reuse existing logic from MatchPredictionsView.get_context_data] ...
        
        context = {
            "match": match,
            "user_predictions": user_predictions,
            "sort_mode": sort_mode,
            "current_user": request.user,
            "origin": request.GET.get("from", "predictions"),  # Preserve origin
        }
        
        return render(
            request,
            "predictions/partials/match_predictions_content.html",
            context,
        )
```

**Refactoring note:** The prediction list building logic should be extracted into a shared helper function to avoid duplication between `MatchPredictionsView` and `MatchPredictionsUpdateView`.

### 2. Extract Shared Logic Helper

**File:** `predictions/views.py`

Add helper function before the view classes:

```python
def build_match_predictions_list(
    match: Match,
    sort_mode: str,
    current_user: "User",
) -> list[dict[str, Any]]:
    """
    Build the predictions list for a match with rankings.
    
    Args:
        match: The match to get predictions for
        sort_mode: "match" (sort by match points) or "total" (sort by total points)
        current_user: The authenticated user viewing the list
    
    Returns:
        List of prediction dicts with: user, rank, prediction data, points, stats
    """
    User = get_user_model()
    
    # Get all users with their predictions for this match
    users = User.objects.filter(is_active=True).select_related("profile")
    
    # Prefetch predictions for this match
    predictions = MatchPrediction.objects.filter(match=match).select_related("user")
    prediction_by_user = {p.user_id: p for p in predictions}
    
    # Calculate scores and stats for each user
    user_predictions = []
    for user in users:
        prediction = prediction_by_user.get(user.id)
        
        # Get user's total points and exact match count across all matches
        profile = user.profile
        
        item = {
            "user": user,
            "has_predicted": prediction is not None,
            "predicted_goals_home": prediction.predicted_goals_home if prediction else None,
            "predicted_goals_away": prediction.predicted_goals_away if prediction else None,
            "joker_active": prediction.is_joker if prediction else False,
            "points_earned": prediction.points_earned if prediction else 0,
            "champion": profile.champion_team,
            "exact_matches": profile.exact_match_count,
            "joker_count": profile.jokers_used,
            "total_points": profile.total_points,
        }
        
        user_predictions.append(item)
    
    # Sort by selected mode
    if sort_mode == "total":
        # Sort by total points (descending), then by username
        user_predictions.sort(
            key=lambda x: (-x["total_points"], x["user"].username.lower())
        )
    else:  # sort_mode == "match"
        # Sort by match points (descending), then by username
        user_predictions.sort(
            key=lambda x: (-x["points_earned"], x["user"].username.lower())
        )
    
    # Assign ranks (handle ties)
    for rank, item in enumerate(user_predictions, start=1):
        item["rank"] = rank
    
    return user_predictions
```

### 3. Refactor Existing View to Use Helper

**File:** `predictions/views.py`

Update `MatchPredictionsView.get_context_data()` to use the shared helper:

```python
class MatchPredictionsView(LoginRequiredMixin, TemplateView):
    template_name = "predictions/match_predictions_page.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match_id = self.kwargs["match_id"]
        match = get_object_or_404(
            Match.objects.select_related("team_home", "team_away"),
            pk=match_id,
        )
        
        # Get parameters
        origin = self.request.GET.get("from", "predictions")
        if origin not in ("home", "predictions"):
            origin = "predictions"
        
        sort_mode = self.request.GET.get("sort", "match")
        if sort_mode not in ("match", "total"):
            sort_mode = "match"
        
        # Build predictions list using shared helper
        user_predictions = build_match_predictions_list(
            match=match,
            sort_mode=sort_mode,
            current_user=self.request.user,
        )
        
        # Calculate polling interval
        polling_interval = get_polling_interval()
        
        context.update({
            "match": match,
            "user_predictions": user_predictions,
            "sort_mode": sort_mode,
            "origin": origin,
            "current_user": self.request.user,
            "polling_interval": polling_interval,
        })
        
        return context
```

### 4. Create Partial Template

**File:** `templates/predictions/partials/match_predictions_content.html`

Extract the sort toggle and predictions list from the full page template:

```django
{# Partial template for HTMX updates - contains only the dynamic content #}

<!-- Sort Toggle -->
<div class="bg-white dark:bg-zinc-800 rounded-lg shadow-sm p-4 mb-4">
    <div class="flex justify-center">
        <div class="inline-flex rounded-lg p-1 bg-zinc-100 dark:bg-zinc-700" role="group">
            <a href="?sort=match&from={{ origin }}"
                class="px-4 py-2 text-sm font-medium rounded-md transition-colors min-w-[120px] text-center min-h-[44px] flex items-center justify-center
                {% if sort_mode == 'match' %}bg-white dark:bg-zinc-600 text-zinc-900 dark:text-white shadow-sm{% else %}text-zinc-600 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white{% endif %}">
                Spielpunkte
            </a>
            <a href="?sort=total&from={{ origin }}"
                class="px-4 py-2 text-sm font-medium rounded-md transition-colors min-w-[120px] text-center min-h-[44px] flex items-center justify-center
                {% if sort_mode == 'total' %}bg-white dark:bg-zinc-600 text-zinc-900 dark:text-white shadow-sm{% else %}text-zinc-600 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white{% endif %}">
                Gesamtpunkte
            </a>
        </div>
    </div>
</div>

<!-- Predictions List -->
<div class="bg-white dark:bg-zinc-800 rounded-lg shadow-sm divide-y divide-zinc-100 dark:divide-zinc-700">
    {% for item in user_predictions %}
    <div class="p-4 {% if item.user == current_user %}bg-emerald-50 dark:bg-emerald-900/20{% endif %}">
        <!-- Main row: rank, username, joker, prediction, points -->
        <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-3 min-w-0">
                <span class="text-zinc-500 dark:text-zinc-400 text-sm font-medium w-6 flex-shrink-0 text-right">
                    {{ item.rank }}.
                </span>
                <span class="font-medium text-zinc-900 dark:text-white truncate">
                    {{ item.user.username }}
                </span>
                {% if item.joker_active %}
                <span class="text-yellow-500 flex-shrink-0" title="Joker">⭐</span>
                {% endif %}
            </div>
            <div class="flex items-center gap-3 flex-shrink-0">
                {% if item.has_predicted %}
                <span class="font-bold text-lg text-zinc-900 dark:text-white">
                    {{ item.predicted_goals_home }}:{{ item.predicted_goals_away }}
                </span>
                {% if item.points_earned is not None %}
                <span
                    class="text-sm min-w-[3rem] text-right {% if item.points_earned > 0 %}text-emerald-600 dark:text-emerald-400{% else %}text-zinc-400{% endif %}">
                    +{{ item.points_earned }}
                </span>
                {% else %}
                <span class="text-sm min-w-[3rem] text-right text-zinc-400">0 Pkt.</span>
                {% endif %}
                {% else %}
                <span class="text-sm text-zinc-400 italic">
                    Kein Tipp
                </span>
                <span class="text-sm min-w-[3rem] text-right text-zinc-400">0 Pkt.</span>
                {% endif %}
            </div>
        </div>
        <!-- Statistics row -->
        <div class="flex items-center gap-4 mt-1 ml-9 text-xs text-zinc-500 dark:text-zinc-400">
            {% if item.champion %}
            <span class="inline-flex items-center gap-1" title="Weltmeister-Tipp">
                <span>🏆</span>
                <span>{{ item.champion.short_name }}</span>
            </span>
            {% endif %}
            <span title="Exakte Ergebnisse">
                ✓ {{ item.exact_matches }}
            </span>
            <span title="Joker verwendet">
                ⭐ {{ item.joker_count }}
            </span>
            <span title="Gesamtpunkte" class="font-medium">
                {{ item.total_points }} Pkt.
            </span>
        </div>
    </div>
    {% empty %}
    <div class="p-8 text-center text-zinc-500 dark:text-zinc-400">
        <p class="text-2xl mb-2">📋</p>
        <p>Noch keine Tipps abgegeben.</p>
    </div>
    {% endfor %}
</div>
```

### 5. Update Full Page Template

**File:** `templates/predictions/match_predictions_page.html`

Replace the inline predictions list with the partial and add HTMX polling:

```django
{% extends "base.html" %}

{% block title %}{{ match.team_home.name }} vs {{ match.team_away.name }} - Alle Tipps{% endblock %}

{% block content %}
<div class="min-h-screen bg-zinc-50 dark:bg-zinc-900">
    <main class="max-w-4xl mx-auto px-4 py-6">
        <!-- Match Info Card (unchanged) -->
        <div class="bg-white dark:bg-zinc-800 rounded-lg shadow-sm p-6 mb-6">
            <!-- ... existing match info markup ... -->
        </div>

        <!-- Predictions Content (now uses partial) -->
        <div id="predictions-content" 
             hx-get="{% url 'predictions:match-predictions-updates' match.id %}?sort={{ sort_mode }}&from={{ origin }}"
             hx-trigger="every {{ polling_interval }}s"
             hx-swap="innerHTML"
             hx-select="#predictions-content > *">
            {% include "predictions/partials/match_predictions_content.html" %}
        </div>
    </main>
</div>
{% endblock %}
```

**HTMX attributes explained:**
- `hx-get`: URL to poll for updates
- `hx-trigger="every Xs"`: Poll every X seconds (dynamic based on match activity)
- `hx-swap="innerHTML"`: Replace the content inside #predictions-content
- `hx-select`: Select only the inner content from the response (filters out wrapper div)

### 6. URL Configuration

**File:** `predictions/urls.py`

Add new URL pattern:

```python
urlpatterns = [
    # ... existing patterns ...
    
    # Match predictions page
    path(
        "match/<int:match_id>/all/",
        views.MatchPredictionsView.as_view(),
        name="match-predictions",
    ),
    
    # HTMX update endpoint for match predictions
    path(
        "match/<int:match_id>/updates/",
        views.MatchPredictionsUpdateView.as_view(),
        name="match-predictions-updates",
    ),
]
```

## Template Structure

```
templates/predictions/
├── match_predictions_page.html      (Full page with HTMX polling)
└── partials/
    └── match_predictions_content.html  (Reusable content for updates)
```

## Polling Behavior

### Interval Calculation

Reuse existing `get_polling_interval()` from `predictions/views.py`:

- **Active matches** (kickoff to kickoff + 160 min): 1 second
- **Idle periods**: 60 seconds

### Server Load

- Same load pattern as existing predictions list page
- No additional database queries per user
- Efficient query with select_related and prefetch_related

### Network Traffic

- Active match: ~60 requests/minute per user viewing the page
- Idle: 1 request/minute per user
- Response size: ~5-20 KB (depends on number of users)

## Error Handling

### HTMX Failures

If polling request fails:
- HTMX automatically retries
- User sees last successful state
- No error messages shown (graceful degradation)

### Missing Data

If match is deleted:
- View returns 404
- HTMX stops polling
- User sees error page

### Concurrent Updates

No conflicts possible:
- This is a read-only view
- Users edit predictions on different page
- Race conditions not applicable

## Browser Compatibility

- HTMX requires modern browsers (ES6+)
- Graceful degradation: page works without JavaScript (no auto-updates)
- Tested browsers: Chrome, Firefox, Safari, Edge

## Performance Considerations

### Database Queries

Per request:
1. Get match (with team relations): 1 query
2. Get all active users: 1 query  
3. Get predictions for match: 1 query
4. Get user profiles (via select_related): included in user query

Total: ~3 queries per poll (efficient)

### Caching Opportunities

Future optimization (not in scope):
- Cache match data (rarely changes)
- Cache user list (changes infrequently)
- Only invalidate on prediction save/delete

### Scroll Position

HTMX preserves scroll by default with `innerHTML` swap.
No custom JavaScript needed.
