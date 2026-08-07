# Design: Dedicated All Tips Page

## Overview

Refactor the current bottom sheet implementation into a dedicated full-page view. The `MatchPredictionsView` will render a complete page template instead of an HTMX partial. Navigation will use standard page transitions with query parameters to track the referrer.

## Architecture

### Page Flow

```
Home Page or Predictions Page
    │
    └─► Click "Alle Tipps" button
            │
            └─► Navigate to /predictions/match/<id>/all/?from=<origin>
                    │
                    ├─► Render full page with all predictions
                    ├─► Back button in header
                    └─► Browser back button navigates to origin
```

### URL Structure

```
/predictions/match/<int:match_id>/all/
Query parameters:
  - from: Origin page ('home' or 'predictions')
```

## Component Changes

### 1. View Refactoring

**File:** `predictions/views.py`

Modify `MatchPredictionsView` to render a full page:

```python
class MatchPredictionsView(LoginRequiredMixin, TemplateView):
    """Display all predictions for a match on a dedicated page."""
    
    template_name = "predictions/match_predictions_page.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match_id = self.kwargs["match_id"]
        match = get_object_or_404(
            Match.objects.select_related("team_home", "team_away"),
            pk=match_id,
        )
        
        # Get origin for back navigation
        origin = self.request.GET.get("from", "predictions")
        if origin not in ("home", "predictions"):
            origin = "predictions"
        
        # Get sort mode
        sort_mode = self.request.GET.get("sort", "match")
        if sort_mode not in ("match", "total"):
            sort_mode = "match"
        
        # Build user predictions list (existing logic)
        # ... [same logic as current implementation] ...
        
        context.update({
            "match": match,
            "user_predictions": user_predictions,
            "sort_mode": sort_mode,
            "origin": origin,
            "current_user": self.request.user,
        })
        
        return context
```

### 2. Template Structure

**New File:** `templates/predictions/match_predictions_page.html`

```django
{% extends "base.html" %}
{% load static %}

{% block title %}{{ match.team_home.name }} vs {{ match.team_away.name }} - Alle Tipps{% endblock %}

{% block content %}
<div class="min-h-screen bg-zinc-50 dark:bg-zinc-900">
    <!-- Header with Back Button -->
    <header class="sticky top-0 z-10 bg-white dark:bg-zinc-800 border-b border-zinc-200 dark:border-zinc-700 shadow-sm">
        <div class="max-w-4xl mx-auto px-4 py-4">
            <div class="flex items-center gap-4">
                <a
                    href="{% if origin == 'home' %}{% url 'home' %}{% else %}{% url 'predictions:prediction-list' %}{% endif %}"
                    class="flex items-center gap-2 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors"
                >
                    <span class="text-xl">🔙</span>
                    <span class="text-sm font-medium">Zurück</span>
                </a>
                <h1 class="text-lg font-bold text-zinc-900 dark:text-white flex-1 text-center">
                    Alle Tipps
                </h1>
                <div class="w-16"></div> <!-- Spacer for center alignment -->
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-4xl mx-auto px-4 py-6">
        <!-- Match Info Card -->
        <div class="bg-white dark:bg-zinc-800 rounded-lg shadow-sm p-6 mb-6">
            <h2 class="text-2xl font-bold text-center text-zinc-900 dark:text-white">
                {{ match.team_home.name }} vs {{ match.team_away.name }}
            </h2>
            {% if match.goals_home is not None and match.goals_away is not None %}
            <p class="text-center text-3xl font-bold text-emerald-600 dark:text-emerald-400 mt-2">
                {{ match.goals_home }} : {{ match.goals_away }}
            </p>
            {% else %}
            <p class="text-center text-3xl font-bold text-emerald-600 dark:text-emerald-400 mt-2">
                - : -
            </p>
            {% endif %}
            <p class="text-center text-sm text-zinc-500 dark:text-zinc-400 mt-2">
                {{ match.kickoff|date:"d.m.Y H:i" }} Uhr
            </p>
        </div>

        <!-- Sort Toggle -->
        <div class="bg-white dark:bg-zinc-800 rounded-lg shadow-sm p-4 mb-4">
            <div class="flex justify-center">
                <div class="inline-flex rounded-lg p-1 bg-zinc-100 dark:bg-zinc-700" role="group">
                    <a
                        href="?sort=match&from={{ origin }}"
                        class="px-4 py-2 text-sm font-medium rounded-md transition-colors min-w-[120px] text-center
                        {% if sort_mode == 'match' %}bg-white dark:bg-zinc-600 text-zinc-900 dark:text-white shadow-sm{% else %}text-zinc-600 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white{% endif %}"
                    >
                        Spielpunkte
                    </a>
                    <a
                        href="?sort=total&from={{ origin }}"
                        class="px-4 py-2 text-sm font-medium rounded-md transition-colors min-w-[120px] text-center
                        {% if sort_mode == 'total' %}bg-white dark:bg-zinc-600 text-zinc-900 dark:text-white shadow-sm{% else %}text-zinc-600 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white{% endif %}"
                    >
                        Gesamtpunkte
                    </a>
                </div>
            </div>
        </div>

        <!-- Predictions List -->
        <div class="bg-white dark:bg-zinc-800 rounded-lg shadow-sm divide-y divide-zinc-100 dark:divide-zinc-700">
            {% for item in user_predictions %}
            <div class="p-4 {% if item.user == current_user %}bg-emerald-50 dark:bg-emerald-900/20{% endif %}">
                <!-- Existing prediction item markup -->
                <!-- ... (reuse from partial) ... -->
            </div>
            {% empty %}
            <div class="p-8 text-center text-zinc-500 dark:text-zinc-400">
                Noch keine Tipps vorhanden.
            </div>
            {% endfor %}
        </div>
    </main>
</div>
{% endblock %}
```

### 3. Update Navigation Links

**File:** `templates/predictions/prediction_row.html`

Replace HTMX bottom sheet trigger with standard link:

```django
<!-- Old: HTMX trigger -->
<button
    hx-get="{% url 'predictions:match-predictions' match.pk %}"
    hx-target="#bottom-sheet-content"
    ...
>
    Alle Tipps
</button>

<!-- New: Standard link -->
<a
    href="{% url 'predictions:match-predictions' match.pk %}?from=predictions"
    class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
>
    <span>👥</span>
    <span>Alle Tipps</span>
</a>
```

**File:** `templates/home.html`

Add "Alle Tipps" link to match cards:

```django
<a
    href="{% url 'predictions:match-predictions' match.pk %}?from=home"
    class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
>
    <span>👥</span>
    <span>Alle Tipps</span>
</a>
```

### 4. Remove Bottom Sheet

**File:** `templates/base.html`

Remove bottom sheet HTML structure and JavaScript:

```django
<!-- Remove: -->
<div id="bottom-sheet-backdrop" ...></div>
<div id="bottom-sheet" ...></div>
<script>
    // Bottom sheet logic
</script>
```

### 5. Icon Standardization

Create a centralized icon reference and ensure consistency across all templates:

| Feature | Icon | Usage |
|---------|------|-------|
| View all tips | 👥 | "Alle Tipps" button |
| Back navigation | 🔙 | Back button in headers |
| Joker active | ⭐ | Joker indicator in predictions |
| Champion prediction | 🏆 | User's champion pick |
| Exact match | ✓ | Exact prediction count |
| Edit prediction | ✏️ | Edit button |
| Delete prediction | 🗑️ | Delete button |

**Files to update:**
- `templates/home.html`
- `templates/predictions/prediction_list.html`
- `templates/predictions/prediction_row.html`
- `templates/ranking.html`
- `templates/predictions/match_predictions_page.html` (new)

### 6. Responsive Design

**Mobile (< 768px):**
- Full-width content
- Padding: 1rem (16px)
- Larger touch targets (44x44px minimum)
- Font sizes: 14-16px for body, 20-24px for headings
- Stack elements vertically

**Tablet (768px - 1024px):**
- Max width: 768px, centered
- Padding: 1.5rem (24px)
- Two-column layout for some stats

**Desktop (> 1024px):**
- Max width: 1024px (4xl), centered
- Padding: 2rem (32px)
- Multi-column stats layout
- Hover states more prominent

## Data Flow

```
Request: GET /predictions/match/42/all/?from=predictions&sort=total
    │
    ├─► MatchPredictionsView.get_context_data()
    │   ├─► Parse match_id: 42
    │   ├─► Parse origin: "predictions"
    │   ├─► Parse sort_mode: "total"
    │   ├─► Fetch match and all predictions
    │   ├─► Calculate ranking (Olympic-style)
    │   └─► Return context
    │
    └─► Render templates/predictions/match_predictions_page.html
        ├─► Header with back link to predictions page
        ├─► Match info card
        ├─► Sort toggle (preserve origin param)
        └─► Predictions list (ranked)
```

## Migration Path

1. Create new template file (match_predictions_page.html)
2. Refactor MatchPredictionsView to use TemplateView
3. Update links in prediction_row.html (predictions page)
4. Update links in home.html (home page)
5. Standardize icons across templates
6. Remove bottom sheet from base.html
7. Test navigation flow from both origins
8. Verify responsive behavior on mobile and desktop

## Testing Strategy

### Manual Testing
- Navigate from predictions page → verify back returns to predictions
- Navigate from home page → verify back returns to home
- Test sort toggle preserves origin parameter
- Test on mobile (320px, 375px, 414px widths)
- Test on desktop (1024px, 1440px, 1920px widths)
- Verify all icons match across pages

### Automated Testing
- URL resolution and reversal
- View returns 404 for non-existent match
- View requires authentication
- Origin parameter defaults to "predictions"
- Invalid origin falls back to "predictions"
- Invalid sort mode falls back to "match"
- Template renders with correct context

## Performance Considerations

- Same query performance as current implementation
- No HTMX overhead for partial updates
- Standard page load with browser caching
- Consider adding pagination if user count > 100 (future enhancement)

## Accessibility

- Semantic HTML structure
- Proper heading hierarchy (h1 → h2 → h3)
- ARIA labels for icon buttons
- Keyboard navigation support
- Focus management on page load
- Color contrast meeting WCAG AA standards
