# Design: View Other Predictions

## Overview

Implement a bottom sheet component that displays all predictions for a match when clicked. Uses HTMX for dynamic loading and CSS for the slide-up animation. Predictions are only shown after match kickoff.

## Architecture

### Component Structure

```
Match Row (existing)
    │
    └─► Click triggers HTMX request
            │
            └─► GET /predictions/match/<id>/all/
                    │
                    ├─► Before kickoff: Returns "locked" partial
                    └─► After kickoff: Returns predictions list partial
                            │
                            └─► Renders into bottom sheet container
```

### Data Flow

```
User clicks match row
    │
    ├─► HTMX GET request with match ID
    │
Server (MatchPredictionsView)
    │
    ├─► Fetch all predictions for match
    │   └─► SELECT * FROM predictions WHERE match_id = X
    │
    ├─► Include match details, result, current user
    │
    └─► Return match_predictions.html partial
            │
            └─► Rendered in bottom sheet, slide-up animation triggers
```

## Implementation Details

### 1. URL Configuration (predictions/urls.py)

```python
path(
    "match/<int:match_id>/predictions/",
    views.MatchPredictionsView.as_view(),
    name="match-predictions",
),
```

### 2. View (predictions/views.py)

```python
class MatchPredictionsView(LoginRequiredMixin, View):
    """Return all predictions for a match with Olympic-style ranking."""

    def get(self, request, match_id: int):
        match = get_object_or_404(Match, pk=match_id)

        # Get all active users
        User = get_user_model()
        users = User.objects.filter(is_active=True)

        # Fetch predictions for this match
        predictions_by_user = {
            p.user_id: p
            for p in MatchPrediction.objects.filter(match=match).select_related("user")
        }

        # Build list with all users, even those without predictions
        user_predictions = []
        for user in users:
            pred = predictions_by_user.get(user.id)
            user_predictions.append({
                "user": user,
                "prediction": pred,
                "predicted_goals_home": pred.predicted_goals_home if pred else None,
                "predicted_goals_away": pred.predicted_goals_away if pred else None,
                "joker_active": pred.joker_active if pred else False,
                "points_earned": pred.points_earned if pred else None,
                "has_predicted": pred is not None,
            })

        # Sort by points (desc), has_predicted, username
        user_predictions.sort(
            key=lambda x: (
                -(x["points_earned"] if x["points_earned"] is not None else -1),
                0 if x["has_predicted"] else 1,
                x["user"].username.lower()
            )
        )

        # Calculate Olympic ranks (shared ranks for ties, skip after tie)
        current_rank = 1
        for i, item in enumerate(user_predictions):
            if i > 0:
                prev = user_predictions[i - 1]
                same_rank = (
                    item["points_earned"] == prev["points_earned"]
                    and item["has_predicted"] == prev["has_predicted"]
                )
                if not same_rank:
                    current_rank = i + 1
            item["rank"] = current_rank

        return render(request, "predictions/partials/match_predictions.html", {
            "match": match,
            "user_predictions": user_predictions,
            "current_user": request.user,
        })
```

### 3. Bottom Sheet Container (base.html or prediction_list.html)

Add a global bottom sheet container:

```html
<!-- Bottom Sheet Container -->
<div id="bottom-sheet-backdrop" 
     class="fixed inset-0 bg-black/50 z-40 hidden"
     onclick="closeBottomSheet()"></div>

<div id="bottom-sheet" 
     class="fixed inset-x-0 bottom-0 z-50 transform translate-y-full transition-transform duration-300 ease-out">
    <div class="bg-white dark:bg-zinc-800 rounded-t-2xl max-h-[70vh] overflow-hidden flex flex-col">
        <!-- Handle bar -->
        <div class="flex justify-center py-2">
            <div class="w-10 h-1 bg-zinc-300 dark:bg-zinc-600 rounded-full"></div>
        </div>
        <!-- Content loaded via HTMX -->
        <div id="bottom-sheet-content" class="overflow-y-auto px-4 pb-6">
            <!-- Dynamic content here -->
        </div>
    </div>
</div>
```

### 4. Match Row Click Handler

Update prediction_row.html to trigger bottom sheet:

```html
<div id="match-{{ match.id }}" 
     class="match-row ... cursor-pointer"
     hx-get="{% url 'predictions:match-predictions' match.id %}"
     hx-target="#bottom-sheet-content"
     hx-trigger="click"
     hx-on::after-request="openBottomSheet()">
```

### 5. Predictions List Partial (predictions/partials/match_predictions.html)

```html
<!-- Match Header -->
<div class="sticky top-0 bg-white dark:bg-zinc-800 pb-4 border-b border-zinc-200 dark:border-zinc-700">
    <h3 class="text-lg font-bold text-center text-zinc-900 dark:text-white">
        {{ match.team_home.name }} vs {{ match.team_away.name }}
    </h3>
    {% if match.goals_home is not None %}
    <p class="text-center text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
        {{ match.goals_home }} : {{ match.goals_away }}
    </p>
    {% endif %}
</div>

<!-- Predictions List with Olympic Ranking -->
<div class="divide-y divide-zinc-100 dark:divide-zinc-700 mt-4">
    {% for item in user_predictions %}
    <div class="py-3 flex items-center justify-between gap-3 {% if item.user == current_user %}bg-emerald-50 dark:bg-emerald-900/20 -mx-4 px-4{% endif %}">
        <div class="flex items-center gap-3">
            <span class="text-zinc-500 text-sm font-medium w-6 text-right">
                {{ item.rank }}.
            </span>
            <span class="font-medium text-zinc-900 dark:text-white">
                {{ item.user.username }}
            </span>
            {% if item.joker_active %}
                <span class="text-yellow-500">⭐</span>
            {% endif %}
        </div>
        <div class="flex items-center gap-3">
            {% if item.has_predicted %}
                <span class="font-bold text-lg">
                    {{ item.predicted_goals_home }}:{{ item.predicted_goals_away }}
                </span>
                <span class="text-sm">
                    {% if item.points_earned is not None %}+{{ item.points_earned }}{% else %}-{% endif %}
                </span>
            {% else %}
                <span class="text-sm text-zinc-400 italic">Kein Tipp</span>
                <span class="text-sm text-zinc-400">0 Pkt.</span>
            {% endif %}
        </div>
        <div class="flex items-center gap-3">
            <span class="font-bold text-lg text-zinc-900 dark:text-white">
                {{ pred.predicted_goals_home }}:{{ pred.predicted_goals_away }}
            </span>
            {% if pred.points_earned is not None %}
                <span class="text-sm {% if pred.points_earned > 0 %}text-emerald-600 dark:text-emerald-400{% else %}text-zinc-400{% endif %}">
                    +{{ pred.points_earned }}
                </span>
            {% endif %}
        </div>
    </div>
    {% empty %}
    <p class="py-4 text-center text-zinc-500">Keine Tipps für dieses Spiel.</p>
    {% endfor %}
</div>

<!-- Summary -->
<div class="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-700 text-sm text-zinc-500 dark:text-zinc-400 text-center">
    {{ predictions|length }} Tipper
</div>
```

### 6. Locked Predictions Partial (predictions/partials/locked_predictions.html)

```html
<div class="py-12 text-center">
    <div class="text-4xl mb-4">🔒</div>
    <h3 class="text-lg font-medium text-zinc-900 dark:text-white mb-2">
        Tipps noch nicht sichtbar
    </h3>
    <p class="text-zinc-500 dark:text-zinc-400">
        Die Tipps der anderen werden nach Spielbeginn angezeigt.
    </p>
    <p class="text-sm text-zinc-400 dark:text-zinc-500 mt-2">
        Anpfiff: {{ match.kickoff|date:"d.m.Y H:i" }} Uhr
    </p>
</div>
```

### 7. JavaScript for Bottom Sheet

```javascript
function openBottomSheet() {
    document.getElementById('bottom-sheet-backdrop').classList.remove('hidden');
    document.getElementById('bottom-sheet').classList.remove('translate-y-full');
    document.body.classList.add('overflow-hidden');
}

function closeBottomSheet() {
    document.getElementById('bottom-sheet').classList.add('translate-y-full');
    document.getElementById('bottom-sheet-backdrop').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
}

// Swipe down to close (touch devices)
let touchStartY = 0;
document.getElementById('bottom-sheet').addEventListener('touchstart', (e) => {
    touchStartY = e.touches[0].clientY;
});

document.getElementById('bottom-sheet').addEventListener('touchmove', (e) => {
    const touchY = e.touches[0].clientY;
    const diff = touchY - touchStartY;
    if (diff > 100) {
        closeBottomSheet();
    }
});

// ESC key to close
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeBottomSheet();
});
```

## Edge Cases

1. **No predictions yet**: Show "Keine Tipps" message
2. **User has no prediction**: Still show others' predictions
3. **Many participants**: Scrollable list with sticky header
4. **Very long usernames**: Truncate with ellipsis

## Mobile Responsiveness

- Bottom sheet takes 70% viewport height max
- Full width with rounded top corners
- Touch-friendly spacing (min 44px tap targets)
- Swipe-down gesture to close
- Backdrop tap to close
- Handle bar visual indicator

## Security

- Requires authentication (LoginRequiredMixin)
- No mutation possible through this view (read-only)

## Dependencies

- HTMX (already in use)
- No new packages required
- CSS transitions for animations
