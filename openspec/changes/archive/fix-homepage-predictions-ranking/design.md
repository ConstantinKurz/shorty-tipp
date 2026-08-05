# Design: Fix Homepage Predictions and Dynamic Ranking

## Overview

This change addresses three functional gaps in the newly implemented home page by:
1. Redirecting the standalone ranking page to home
2. Adding HTMX-based polling for dynamic ranking updates
3. Enabling prediction auto-save on the home page

## Architecture

### 1. Redirect Ranking Page

**File**: `tipapp/urls.py`

```python
from django.views.generic import RedirectView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('ranking/', RedirectView.as_view(url='/', permanent=False), name='ranking'),
    # ... rest of urls
]
```

- Use Django's `RedirectView` to redirect `/ranking/` → `/`
- `permanent=False` issues HTTP 302 (temporary redirect) instead of 301
- Preserves the `ranking` URL name for any existing template references

### 2. Dynamic Ranking Updates

**Architecture Flow**:

```
Home Page Template
    │
    ├─► HTMX polling div (hidden)
    │   hx-get="/ranking/updates/"
    │   hx-trigger="load, every {{ ranking_interval }}s"
    │   hx-target="#compact-ranking, #ranking-content"
    │   hx-swap="outerHTML"
    │
HomeView.get_context_data()
    │
    ├─► Determine polling interval
    │   (10s during live matches, 60s otherwise)
    └─► Pass to template context
```

**Implementation Details**:

1. **Add polling interval to HomeView context**
   - Reuse `get_polling_interval()` from `predictions.views`
   - Add `ranking_interval` to context dict
   - Same logic: 10s during active matches, 60s otherwise

2. **Add HTMX polling endpoint for rankings**
   - Create `RankingUpdatesView` in `scoring/views.py`
   - Returns partial templates for both compact and full ranking
   - Requires `HX-Request` header
   - Preserves round filter (`?round=group`) from query params

3. **Update home.html template**
   - Add hidden polling div after ranking section
   - Configure HTMX to swap both `#compact-ranking` and `#ranking-content`
   - Use multi-target HTMX swap (requires HTMX 1.9+)
   - Preserve expanded/collapsed state via `hx-preserve` attribute

**Template Changes**:

`templates/home.html`:
```html
<!-- Ranking Section -->
<div class="bg-white dark:bg-zinc-800 rounded-2xl shadow-xl border border-zinc-200 dark:border-zinc-700 p-6 sm:p-8">
    <!-- Header with toggle button (unchanged) -->
    
    <!-- Compact Ranking -->
    <div id="compact-ranking" hx-preserve="true">
        {% include "partials/compact_ranking.html" %}
    </div>
    
    <!-- Full Ranking -->
    <div id="full-ranking" class="hidden" hx-preserve="true">
        <div id="ranking-content">
            {% include "partials/ranking_content.html" %}
        </div>
    </div>
</div>

<!-- HTMX Polling for ranking updates -->
<div hx-get="{% url 'scoring:ranking-updates' %}"
     hx-trigger="load, every {{ ranking_interval }}s"
     hx-swap="none"
     class="hidden">
</div>
```

**New View**:

`scoring/views.py`:
```python
class RankingUpdatesView(LoginRequiredMixin, View):
    """
    HTMX endpoint for polling ranking updates.
    
    Returns updated ranking partials (both compact and full).
    Triggered by client-side polling on home page.
    """
    
    def get(self, request: HttpRequest) -> HttpResponse:
        # Get round filter from query params
        selected_round = request.GET.get("round")
        
        # Compute rankings (same logic as HomeView)
        full_leaderboard = RankingService.get_leaderboard_up_to_round(
            round_code=selected_round
        )
        
        # Enrich with champion data
        # ... same as HomeView ...
        
        # Extract compact leaderboard (5 entries around user)
        # ... same as HomeView ...
        
        context = {
            'compact_leaderboard': compact_leaderboard,
            'full_leaderboard': full_leaderboard,
            'user_rank_entry': user_rank_entry,
            'selected_round': selected_round,
            'available_rounds': get_available_rounds(),
        }
        
        return render(request, 'partials/ranking_updates.html', context)
```

**New Partial Template**:

`templates/partials/ranking_updates.html`:
```html
<!-- This template returns BOTH compact and full ranking partials -->
<!-- HTMX will swap each by matching their IDs -->

<div id="compact-ranking" hx-swap-oob="true" hx-preserve="true">
    {% include "partials/compact_ranking.html" %}
</div>

<div id="ranking-content" hx-swap-oob="true" hx-preserve="true">
    {% include "partials/ranking_content.html" %}
</div>
```

**Note**: Using `hx-swap-oob="true"` (out-of-band swap) allows updating multiple targets from a single response. The `hx-preserve="true"` attribute preserves expanded/collapsed state by keeping the DOM element's visibility.

### 3. Enable Prediction Auto-Save on Homepage

**Problem**: Auto-save JavaScript is currently embedded in `predictions/prediction_list.html`, making it unavailable on the home page.

**Solution**: Move JavaScript to `base.html` so it's globally available.

**Implementation**:

1. **Extract auto-save JavaScript from prediction_list.html**
   - Cut the input event listener that handles `.prediction-input` fields
   - Keep debounce logic (500ms delay before submit)
   - Keep HTMX trigger (`htmx.trigger(form, 'submit')`)

2. **Add to base.html in a new `<script>` block**
   - Place before closing `</body>` tag
   - Ensure it runs after HTMX is loaded
   - Use same event delegation pattern (`document.addEventListener`)

3. **Remove from prediction_list.html**
   - Delete duplicate auto-save code
   - Keep all other JavaScript (phase navigation, etc.)

**Code to Move**:

```javascript
// Auto-save: Submit prediction form when both home + away goals filled
// Debounced to avoid spamming server while user types
document.addEventListener('input', function(e) {
    if (!e.target.classList.contains('prediction-input')) return;
    
    const form = e.target.closest('.prediction-form');
    if (!form) return;
    
    const homeInput = form.querySelector('[name="predicted_goals_home"]');
    const awayInput = form.querySelector('[name="predicted_goals_away"]');
    
    // Clear previous timer (debounce)
    if (form.debounceTimer) clearTimeout(form.debounceTimer);
    
    // Wait 500ms after last keystroke, then submit if both fields filled
    form.debounceTimer = setTimeout(function() {
        if (homeInput.value !== '' && awayInput.value !== '') {
            htmx.trigger(form, 'submit');  // Trigger HTMX form submission
        }
    }, 500);
});
```

**Target Location**: `templates/base.html`, inside `{% block extra_js %}` or at the end of the body.

## Data Flow

### Ranking Updates Flow

```
1. User visits home page
2. HomeView computes ranking_interval (10s or 60s)
3. Template includes hidden HTMX polling div
4. After page load, HTMX starts polling RankingUpdatesView
5. RankingUpdatesView fetches current rankings
6. Returns ranking_updates.html partial with OOB swaps
7. HTMX swaps #compact-ranking and #ranking-content in place
8. Expanded/collapsed state preserved via hx-preserve
9. Repeat every interval
```

### Prediction Auto-Save Flow

```
1. User enters score in home page prediction input
2. Input event fires (event delegation from document)
3. JavaScript finds parent .prediction-form
4. Checks if both home and away scores filled
5. Waits 500ms (debounce)
6. If still filled after 500ms, triggers HTMX form submission
7. POST to /predictions/<match_id>/save/
8. PredictionSaveView validates and saves
9. Returns updated prediction_row.html partial
10. HTMX swaps #match-<id> with new HTML
11. Process repeats for next score entry
```

## URL Configuration

### New URL Pattern

**File**: `scoring/urls.py` (create if doesn't exist)

```python
from django.urls import path
from scoring.views import HomeView, RankingUpdatesView

app_name = "scoring"

urlpatterns = [
    path("ranking/updates/", RankingUpdatesView.as_view(), name="ranking-updates"),
]
```

**Update tipapp/urls.py** to include scoring URLs:

```python
urlpatterns = [
    path('', include('scoring.urls')),  # Includes ranking-updates
    path('predictions/', include('predictions.urls')),
    path('ranking/', RedirectView.as_view(url='/', permanent=False), name='ranking'),
    # ... rest
]
```

## Edge Cases

### Ranking Updates
- **User at rank 1**: Compact ranking shows user + 4 below (same as initial load)
- **User at last rank**: Compact ranking shows 4 above + user
- **Round filter active**: HTMX preserves `?round=group` in polling URL
- **Expanded state toggle**: `hx-preserve` prevents state reset during swap
- **No matches live**: Polling slows to 60s (less server load)

### Prediction Auto-Save
- **Locked matches**: Auto-save still triggers but server returns error (expected behavior)
- **Empty inputs**: Form not submitted until both fields filled
- **Rapid typing**: Debounce ensures only one submit after user stops typing
- **JavaScript disabled**: Forms still work with manual submit button (if added later)
- **HTMX swap**: After save, new HTML replaces form, resets debounce timer

## Testing Strategy

### Manual Testing
- Visit `/ranking/` → should redirect to `/`
- Enter prediction on home page → should save automatically after 500ms
- Watch ranking during live match → should update every 10s
- Expand ranking, wait for update → should stay expanded
- Filter ranking by round, wait → update should preserve filter

### Automated Tests
- Test `RedirectView` returns 302 with correct Location header
- Test `RankingUpdatesView` requires login
- Test `RankingUpdatesView` returns correct partials
- Test `get_polling_interval()` returns 10 during live matches
- Test auto-save JavaScript (browser tests with Playwright)
