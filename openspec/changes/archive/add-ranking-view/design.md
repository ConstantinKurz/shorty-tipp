## Context

Django project with custom User model containing ranking-relevant fields: `total_points`, `exact_match_count`, `jokers_used`, and `predicted_champion` (FK to Team). Authentication system is implemented with login/logout. Base template exists with Tailwind CSS (CDN), dark mode support, and fintech aesthetic (zinc colors). Team model exists with country information for flag display.

## Goals / Non-Goals

**Goals:**
- Display complete ranking of all users
- Show olympic-style placement (users with same points share the same rank)
- Display username, rank, total points, predicted champion with flag
- Display exact match count and jokers used count
- Sort by total points descending, then alphabetically by username
- Accessible only to authenticated users
- Mobile-responsive table layout
- Consistent with existing fintech design

**Non-Goals:**
- Filtering or searching rankings (can be added later)
- Historical ranking data / timeline
- User profile links from ranking (separate feature)
- Export functionality (CSV, PDF)
- Pagination (user base is ~50 people, single page is fine)
- Real-time updates (standard page load is sufficient)

## Decisions

### 1. View Location

**Decision:** Create ranking view in `users/views.py` as `RankingView`.

**Rationale:**
- Ranking is fundamentally about users
- Keeps user-related views in one place
- No need for separate ranking app for single view
- Follows Django convention for small projects

**Alternatives considered:**
- Separate `ranking` app: Rejected - overkill for one view
- Root-level view in `tipapp/views.py`: Rejected - less organized

### 2. URL Route

**Decision:** Add `/ranking/` URL to main `tipapp/urls.py`.

```python
path("ranking/", views.RankingView.as_view(), name="ranking"),
```

**Rationale:**
- Short, memorable URL
- Top-level route makes sense for core feature
- Named URL for reverse lookups and template links
- Requires login via `@login_required` or `LoginRequiredMixin`

### 3. Olympic-Style Ranking Logic

**Decision:** Use existing `RankingService.get_current_leaderboard()` from `scoring/services.py`.

**Implementation:**
```python
from scoring.services import RankingService

leaderboard = RankingService.get_current_leaderboard()
# Returns list of dicts with: rank, user_id, username, total_points, 
# exact_match_count, jokers_used
```

**Rationale:**
- Ranking logic already implemented and tested in RankingService
- Uses correct tiebreaker rules per WM 2026 rules:
  1. Total points (higher is better)
  2. Exact match count (higher is better)  
  3. Jokers used (fewer is better - more jokers left)
- Olympic-style shared ranks (1, 2, 2, 4) already implemented
- Keeps business logic centralized in service layer
- View stays thin and delegates to domain service

**Note:** The service returns user data but not `predicted_champion`. We'll need to enrich the data with champion info in the view.

**Alternatives considered:**
- Django ORM window functions (Rank()): Rejected - logic already exists in service
- Manual Python ranking in view: Rejected - duplicates tested service logic

### 4. Template Structure

**Decision:** Card-based layout matching login page aesthetic, with responsive table inside card.

**Layout (following login.html style):**
```
┌─────────────────────────────────────────────────────────────────┐
│  Gradient background (zinc-100 to zinc-200, dark mode zinc-900) │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  White/zinc-800 card with rounded-2xl shadow-xl          │  │
│  │                                                           │  │
│  │  🏆 Ranking                                              │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ Rang │ Name │ Punkte │ Champion │ Exakt │ Joker │  │  │
│  │  ├──────┼──────┼────────┼──────────┼───────┼───────┤  │  │
│  │  │  1   │ max  │  245   │ 🇩🇪 DE   │  18   │   5   │  │  │
│  │  │  2   │ anna │  238   │ 🇧🇷 BR   │  15   │   7   │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Mobile Layout (stacked cards within main card):**
```
┌─────────────────────────────────┐
│ #1 maxmuster                    │
│ 245 Punkte                      │
│ 🇩🇪 Deutschland                  │
│ 18 Exakt · 5 Joker              │
├─────────────────────────────────┤
│ #2 annaschulz                   │
│ ...                             │
└─────────────────────────────────┘
```

**Rationale:**
- Consistent with login page: centered card, gradient background, rounded-2xl
- Same color scheme: zinc palette with emerald accents
- Maintains fintech aesthetic across all pages
- Table fits naturally inside card container
- Mobile stacked layout prevents horizontal scroll

### 5. Country Flag Display

**Decision:** Use Unicode flag emojis based on Team's ISO country code.

```python
# In view context or template tag
def get_flag_emoji(country_code: str) -> str:
    # Convert ISO code to regional indicator symbols
    # e.g., "DE" -> "🇩🇪"
    return "".join(chr(0x1F1E6 - 65 + ord(char)) for char in country_code.upper())
```

**Rationale:**
- No external images or CDN needed
- Native browser support
- Lightweight
- Works in dark/light mode

**Alternatives considered:**
- SVG flag icons: Rejected - adds dependencies, maintenance
- Image files: Rejected - slower, requires hosting
- Flag CSS libraries: Rejected - overkill for simple flags

### 6. Handling Users Without Champion Prediction

**Decision:** Display "–" (em dash) or "Noch nicht gewählt" for missing champion.

**Rationale:**
- Clear indication of missing data
- Doesn't break table layout
- Neutral styling (not error state)

### 7. Navigation Link

**Decision:** Add "Ranking" link to main navigation in base template.

**Location:**
- In header if navigation exists
- Or add simple nav bar with Home | Ranking | Profile links

**Rationale:**
- Core feature should be prominently accessible
- Users need easy access from any page
- Follows standard web UX patterns

### 8. View Testing Strategy

**Decision:** Write pytest view tests covering ranking display and edge cases.

**Test Coverage:**
- GET /ranking/ as authenticated user returns 200
- GET /ranking/ as unauthenticated user redirects to login
- Ranking template is used
- Users are ordered by points descending, then username
- Olympic-style ranking with shared ranks for ties
- Champion flag and name display correctly
- Exact match count and jokers used display correctly
- Users without champion show placeholder

**Rationale:**
- Ranking logic is critical and must not break
- Tests document expected behavior
- Prevents regressions when data changes
- Faster than manual testing

### 9. Color Coding (Optional for Future)

**Decision:** No color coding in initial version.

**Rationale:**
- Keeps design clean and neutral
- Avoids subjective "good/bad" colors
- All participants are equal (no podium highlighting)
- Can add subtle hover effects for interactivity

**Alternatives considered:**
- Gold/Silver/Bronze for top 3: Rejected - too game-like, may discourage others
- Gradient based on position: Rejected - adds visual noise

### 10. Performance Considerations

**Decision:** Call `RankingService.get_current_leaderboard()`, then enrich with champion data using single query.

**Rationale:**
- Service returns basic user ranking data (rank, username, points, etc.)
- Need to add `predicted_champion` info separately
- Fetch all User objects with `select_related('predicted_champion')` in single query
- Map champion data to ranking list in view
- No N+1 queries
- User count is small (~50 people), no caching needed yet

```python
from scoring.services import RankingService
from users.models import User

leaderboard = RankingService.get_current_leaderboard()
user_ids = [entry['user_id'] for entry in leaderboard]

# Fetch users with champion in one query
users_dict = {
    user.pk: user 
    for user in User.objects.filter(pk__in=user_ids).select_related('predicted_champion')
}

# Enrich leaderboard with champion data
for entry in leaderboard:
    user = users_dict[entry['user_id']]
    entry['predicted_champion'] = user.predicted_champion
```

## Risks / Trade-offs

**Risk:** Unicode flag emojis may not render on very old browsers
**Mitigation:** Acceptable - target modern browsers, flags are nice-to-have not critical

**Risk:** Table layout may be cramped on small mobile screens
**Mitigation:** Responsive stacked layout for <640px breakpoint

**Trade-off:** No real-time updates
**Acceptance:** Standard page refresh is fine for tipping game, not a live sports ticker

**Trade-off:** No historical ranking data
**Acceptance:** Current snapshot is sufficient, historical tracking is separate feature

**Trade-off:** All users visible to everyone
**Acceptance:** Aligns with game rules, transparency is expected in tipping games
