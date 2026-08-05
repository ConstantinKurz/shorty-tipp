# Design: Home Page with Compact Ranking and Next Matches

## Overview

Build a new home page view that combines a compact ranking display with quick access to upcoming matches for tipping. The page will be the new landing page after login (`/`) and will use existing components from the ranking and predictions systems.

## Architecture

### Component Structure

```
Home Page (/) - Replaces standalone ranking page
├── User Rank Hero Card
│   ├── Large rank number
│   ├── Total points display
│   ├── Champion prediction (flag)
│   └── Visual styling (gradient, trophy icon)
│
├── Ranking Section (replaces /ranking/ page)
│   ├── Collapsed state (default)
│   │   ├── 5 entries (user + 4 nearby ranks)
│   │   ├── Expand/collapse arrow icon
│   │   └── No filter visible
│   │
│   └── Expanded state (IDENTICAL to old ranking page)
│       ├── Full ranking table (all users)
│       ├── All columns: Rang, Name, Champion, Exakt, Joker, Punkte
│       ├── Tournament round filter with HTMX
│       ├── Desktop table + mobile cards
│       └── Collapse arrow icon
│
└── Next Matches Section
    ├── Section header ("Nächste Spiele")
    ├── Up to 3 upcoming matches
    ├── Match prediction rows (reused from predictions page)
    └── Link to full predictions page

Note: /ranking/ URL redirects to /#ranking or removed entirely
```

### URL Configuration

**tipapp/urls.py:**

```python
from django.views.generic import RedirectView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),  # New home page (replaces ranking)
    path('predictions/', include('predictions.urls')),
    path('ranking/', RedirectView.as_view(url='/', permanent=False), name='ranking'),  # Redirect to home
    # ... existing urls ...
]
```

Old `/ranking/` URL redirects to home page. All ranking functionality now in home page expanded view.

Update login redirect to point to home page instead of predictions.

### Data Flow

```
Home View (GET)
    │
    ├─► Get current user's ranking entry
    ├─► Get nearby ranking entries (2 above, 2 below)
    ├─► Get full leaderboard (for expanded state)
    ├─► Get next 3 upcoming matches (kickoff > now, ordered by kickoff)
    ├─► Get user's predictions for those matches
    ├─► Calculate joker limits and lock status
    └─► Render home template

Ranking Expand/Collapse
    │
    ├─► Client-side JavaScript toggle
    ├─► Show/hide full ranking table
    ├─► Show/hide round filter
    └─► HTMX round filtering (when expanded)

Round Filter (HTMX - when expanded)
    │
    ├─► GET request with ?round=<code>
    ├─► Swap ranking content only
    └─► Same behavior as old ranking page

Match Tipping (HTMX - reused from predictions)
    │
    ├─► POST to predictions:save-prediction
    ├─► Validate and save prediction
    └─► Return updated match row partial
```

## Implementation Details

### 1. View Implementation (scoring/views.py or new home app)

**Option A**: Add to scoring app (simpler, no new app)

```python
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

class HomeView(LoginRequiredMixin, TemplateView):
    """
    Home page view showing user rank, compact ranking, and next matches.
    """
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get full leaderboard (for expanded state and finding user position)
        leaderboard = RankingService.get_leaderboard()
        
        # Find user's entry and nearby entries
        user_entry = None
        user_index = None
        for idx, entry in enumerate(leaderboard):
            if entry.user_id == user.id:
                user_entry = entry
                user_index = idx
                break
        
        # Get compact leaderboard (5 entries: user + 4 nearby)
        compact_leaderboard = []
        if user_index is not None:
            # Get 2 above and 2 below (adjust if at edges)
            start = max(0, user_index - 2)
            end = min(len(leaderboard), user_index + 3)
            compact_leaderboard = leaderboard[start:end]
        
        # Get next 3 upcoming matches
        now = timezone.now()
        upcoming_matches = Match.objects.filter(
            kickoff__gt=now
        ).order_by('kickoff')[:3]
        
        # Get user's predictions for those matches
        predictions = {
            p.match_id: p 
            for p in MatchPrediction.objects.filter(
                user=user, 
                match__in=upcoming_matches
            )
        }
        
        # Build match data (similar to predictions view)
        matches_data = []
        for match in upcoming_matches:
            prediction = predictions.get(match.id)
            is_locked = match.kickoff <= now
            
            # Check joker availability
            joker_stats = PredictionLimitService.get_joker_stats(
                user, match.round
            )
            can_add_joker = (
                joker_stats['joker_count'] < joker_stats['joker_limit']
            )
            
            form = PredictionForm(
                instance=prediction,
                match=match,
                user=user,
            ) if not is_locked else None
            
            matches_data.append({
                'match': match,
                'prediction': prediction,
                'form': form,
                'is_locked': is_locked,
                'can_add_joker': can_add_joker,
                'joker_count': joker_stats['joker_count'],
                'joker_limit': joker_stats['joker_limit'],
                'is_group_stage': match.round == 'group',
            })
        
        context.update({
            'user_rank_entry': user_entry,
            'compact_leaderboard': compact_leaderboard,
            'full_leaderboard': leaderboard,
            'available_rounds': [
                {'code': code, 'label': label} 
                for code, label in TOURNAMENT_PHASES.items()
            ],
            'selected_round': None,  # Default to Live view
            'matches_data': matches_data,
        })
        
        return context
```

### 2. Template Structure (templates/home.html)

```django
{% extends "base.html" %}
{% load user_tags %}

{% block title %}Home - Shortytipp Tippspiel{% endblock %}

{% block content %}
<div class="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-sky-50 dark:from-zinc-900 dark:via-zinc-900 dark:to-zinc-800">
    <div class="max-w-4xl mx-auto px-4 py-8 space-y-6">
        
        <!-- User Rank Hero Card -->
        <div class="bg-gradient-to-br from-emerald-500 to-sky-500 rounded-2xl shadow-xl p-6 sm:p-8 text-white">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-sm opacity-90 mb-1">Dein Rang</p>
                    <h1 class="text-5xl font-bold">#{{ user_rank_entry.rank }}</h1>
                </div>
                <div class="text-right">
                    <p class="text-sm opacity-90 mb-1">Punkte</p>
                    <p class="text-4xl font-bold">{{ user_rank_entry.total_points }}</p>
                </div>
            </div>
            {% if user_rank_entry.predicted_champion %}
            <div class="mt-4 flex items-center gap-2 text-sm opacity-90">
                <span>Champion:</span>
                <span class="text-3xl">{{ user_rank_entry.predicted_champion.fifa_code|flag_emoji }}</span>
            </div>
            {% endif %}
        </div>
        
        <!-- Compact Ranking Section -->
        <div class="bg-white dark:bg-zinc-800 rounded-2xl shadow-xl border border-zinc-200 dark:border-zinc-700 overflow-hidden">
            <div class="p-6">
                <!-- Header with expand/collapse -->
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-bold text-zinc-900 dark:text-white">
                        🏆 Ranking
                    </h2>
                    <button 
                        id="ranking-toggle-btn"
                        class="p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors duration-200"
                        aria-label="Ranking erweitern/reduzieren">
                        <svg id="expand-icon" class="w-5 h-5 text-zinc-600 dark:text-zinc-400 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>
                </div>
                
                <!-- Compact ranking (default) -->
                <div id="compact-ranking">
                    {% include "partials/compact_ranking.html" %}
                </div>
                
                <!-- Full ranking (initially hidden) - HTMX swap target -->
                <div id="full-ranking" class="hidden">
                    <div id="ranking-content">
                        {% include "partials/ranking_content.html" %}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Next Matches Section -->
        <div class="bg-white dark:bg-zinc-800 rounded-2xl shadow-xl border border-zinc-200 dark:border-zinc-700 p-6">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-xl font-bold text-zinc-900 dark:text-white">
                    ⚽ Nächste Spiele
                </h2>
                <a href="{% url 'predictions:predictions' %}" 
                   class="text-sm text-emerald-600 dark:text-emerald-400 hover:underline">
                    Alle Spiele →
                </a>
            </div>
            
            {% if matches_data %}
            <div class="space-y-3">
                {% for item in matches_data %}
                    {% include "predictions/prediction_row.html" with match=item.match prediction=item.prediction form=item.form is_locked=item.is_locked can_add_joker=item.can_add_joker joker_count=item.joker_count joker_limit=item.joker_limit is_group_stage=item.is_group_stage %}
                {% endfor %}
            </div>
            {% else %}
            <p class="text-center text-zinc-500 dark:text-zinc-400 py-8">
                Keine anstehenden Spiele.
            </p>
            {% endif %}
        </div>
        
    </div>
</div>

<script>
// Ranking expand/collapse toggle
(function() {
    const toggleBtn = document.getElementById('ranking-toggle-btn');
    const expandIcon = document.getElementById('expand-icon');
    const compactRanking = document.getElementById('compact-ranking');
    const fullRanking = document.getElementById('full-ranking');
    
    let isExpanded = false;
    
    toggleBtn.addEventListener('click', () => {
        isExpanded = !isExpanded;
        
        if (isExpanded) {
            compactRanking.classList.add('hidden');
            fullRanking.classList.remove('hidden');
            expandIcon.style.transform = 'rotate(180deg)';
        } else {
            compactRanking.classList.remove('hidden');
            fullRanking.classList.add('hidden');
            expandIcon.style.transform = 'rotate(0deg)';
        }
    });
})();
</script>
{% endblock %}
```

### 3. Compact Ranking Partial (templates/partials/compact_ranking.html)

```django
{% load user_tags %}

<!-- Desktop compact table -->
<div class="hidden sm:block overflow-x-auto">
    <table class="w-full">
        <thead>
            <tr class="border-b border-zinc-200 dark:border-zinc-700">
                <th class="px-4 py-3 text-left text-sm font-semibold text-zinc-700 dark:text-zinc-300">Rang</th>
                <th class="px-4 py-3 text-left text-sm font-semibold text-zinc-700 dark:text-zinc-300">Name</th>
                <th class="px-4 py-3 text-left text-sm font-semibold text-zinc-700 dark:text-zinc-300">Champion</th>
                <th class="px-4 py-3 text-right text-sm font-semibold text-zinc-700 dark:text-zinc-300">Punkte</th>
            </tr>
        </thead>
        <tbody>
            {% for entry in compact_leaderboard %}
            <tr class="border-b border-zinc-100 dark:border-zinc-700/50 {% if entry.user_id == request.user.id %}bg-emerald-50 dark:bg-emerald-900/20{% elif forloop.counter|divisibleby:2 %}bg-zinc-50/50 dark:bg-zinc-800/50{% endif %} transition-colors duration-150">
                <td class="px-4 py-3 text-zinc-900 dark:text-zinc-100 font-medium">{{ entry.rank }}</td>
                <td class="px-4 py-3 text-zinc-900 dark:text-zinc-100">
                    {{ entry.username }}
                    {% if entry.user_id == request.user.id %}
                        <span class="text-xs text-emerald-600 dark:text-emerald-400">(Du)</span>
                    {% endif %}
                </td>
                <td class="px-4 py-3 text-zinc-900 dark:text-zinc-100">
                    {% if entry.predicted_champion %}
                        <span class="text-3xl rounded-lg inline-block">{{ entry.predicted_champion.fifa_code|flag_emoji }}</span>
                    {% else %}
                        <span class="text-zinc-400 dark:text-zinc-500">–</span>
                    {% endif %}
                </td>
                <td class="px-4 py-3 text-right text-zinc-900 dark:text-zinc-100 font-bold text-lg text-emerald-600 dark:text-emerald-400">{{ entry.total_points }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<!-- Mobile compact cards -->
<div class="sm:hidden space-y-3">
    {% for entry in compact_leaderboard %}
    <div class="bg-zinc-50 dark:bg-zinc-700/50 rounded-lg p-4 border border-zinc-200 dark:border-zinc-600 {% if entry.user_id == request.user.id %}ring-2 ring-emerald-500 dark:ring-emerald-400{% endif %}">
        <div class="flex items-center justify-between mb-2">
            <span class="text-base font-semibold text-zinc-900 dark:text-white">
                #{{ entry.rank }} {{ entry.username }}
                {% if entry.user_id == request.user.id %}
                    <span class="text-xs text-emerald-600 dark:text-emerald-400">(Du)</span>
                {% endif %}
            </span>
            <span class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                {{ entry.total_points }}
            </span>
        </div>
        <div class="text-sm text-zinc-600 dark:text-zinc-400">
            {% if entry.predicted_champion %}
                <span class="text-2xl">{{ entry.predicted_champion.fifa_code|flag_emoji }}</span>
            {% else %}
                <span class="text-zinc-400 dark:text-zinc-500">–</span>
            {% endif %}
        </div>
    </div>
    {% endfor %}
</div>
```

### 4. Services Integration

Reuse existing services:
- `RankingService.get_leaderboard()` - Get full ranking
- `PredictionLimitService.get_joker_stats()` - Check joker limits
- Existing `PredictionForm` and match row template

No new service logic needed.

### 5. URL and Login Configuration

**tipapp/settings/base.py:**

```python
# After successful login, redirect to home page
LOGIN_REDIRECT_URL = '/'
```

**tipapp/urls.py:**

```python
from django.views.generic import RedirectView
from scoring.views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('ranking/', RedirectView.as_view(url='/', permanent=False), name='ranking'),
    # ... rest of urls
]
```

### 6. HTMX Round Filter Support

HomeView must handle `?round=<code>` query param (same as old RankingView):

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    # ...
    
    # Handle round filter (for HTMX requests when expanded)
    selected_round = self.request.GET.get('round')
    
    if selected_round:
        leaderboard = RankingService.get_leaderboard(round_code=selected_round)
    else:
        leaderboard = RankingService.get_leaderboard()  # Live
    
    # ... rest of logic
    
    context['selected_round'] = selected_round
    return context
```

HTMX requests swap `#ranking-content` div only, preserving expanded state.

## Design Considerations

### Visual Styling

- **Hero card**: Gradient background (emerald to sky), large typography
- **Compact ranking**: Highlight current user's row (different background color)
- **Expand icon**: Smooth rotation animation (0° collapsed, 180° expanded)
- **Match rows**: Reuse existing design from predictions page
- **Spacing**: Generous gap-6 between sections
- **Responsiveness**: Stack vertically on mobile, optimize for small screens

### Performance

- Single database query for full leaderboard (used for both compact and expanded)
- Limit upcoming matches to 3 to avoid overwhelming the view
- Reuse existing HTMX endpoints for match prediction updates
- No additional polling needed (matches already have update mechanism)

### Accessibility

- Semantic HTML structure
- ARIA labels for expand/collapse button
- Keyboard navigation support
- Clear visual focus states

### Edge Cases

- **User at top of ranking**: Show user + 4 below
- **User at bottom**: Show user + 4 above
- **Fewer than 5 total users**: Show all available users
- **No upcoming matches**: Show friendly empty state
- **No ranking data yet**: Handle gracefully with placeholder

## Migration Path

1. Create HomeView
2. Create home.html template
3. Create compact_ranking.html partial
4. Update URL configuration
5. Update LOGIN_REDIRECT_URL
6. Test all states (collapsed, expanded, match tipping)
7. Verify responsiveness on mobile

## Dependencies

- Existing `RankingService`
- Existing `PredictionForm` and views
- Existing match row partial template
- HTMX (already in use)
- Tailwind CSS (already in use)

No new dependencies required.
