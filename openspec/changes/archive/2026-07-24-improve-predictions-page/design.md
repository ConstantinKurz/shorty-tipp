# Design: Improve Predictions Page

## Overview

This change enhances the predictions page with better navigation (scrollable list + filters), auto-scroll to relevant matches, live updates, and comprehensive test data for realistic testing scenarios.

## Architecture

### 1. Test Data Management Command

**Location**: `predictions/management/commands/create_wm2026_testdata.py`

**Purpose**: Populate database with realistic WM 2026 tournament data

**Data Generation Strategy**:

1. **Teams** (48 teams):
   - Create or use existing Team model
   - Simple naming: "Team A1", "Team A2", "Team A3" (Group A), "Team B1", "Team B2", "Team B3" (Group B), etc.
   - 16 groups × 3 teams = 48 teams
   - No need for real country names (simplified for testing)

2. **Matches** (104 matches):
   - Group stage: 48 matches (16 groups × 3 matches per group)
     - Round-robin within each group
     - Match dates: Start at 2026-06-11, spread over 2 weeks
   - R32: 32 matches (start 2026-06-27)
   - R16: 16 matches (start 2026-07-03)
   - QF: 8 matches (start 2026-07-09)
   - SF: 2 matches + 1 third-place (start 2026-07-14)
   - Final: 1 match (2026-07-19)
   - Kickoff times: 13:00, 16:00, 19:00, 22:00 (simplified, distributed)
   - Set some matches as finished (status='finished') with realistic results (0-5 goals)
   - Past matches: ~20 group stage matches should be finished
   - Future matches: All knockout + remaining group stage

3. **Users** (6-10 tippers):
   - Usernames: "tipper1", "tipper2", ..., "tipper8"
   - Emails: "tipper1@example.com", etc.
   - Passwords: "testpass123" (consistent for easy testing)
   - All set as active, verified users

4. **Predictions**:
   - For each user, create predictions for 70-90% of matches
   - Prediction patterns:
     - **tipper1**: Optimistic (high scores, many goals)
     - **tipper2**: Pessimistic (low scores, defensive)
     - **tipper3**: Chaotic (random scores)
     - **tipper4**: Realistic (balanced)
     - **tipper5**: Home-team bias
     - **tipper6**: Conservative (many draws)
   - **Joker distribution** (critical for testing):
     - Group stage: 0 jokers (rule enforcement)
     - R32: Assign 3 jokers randomly per user
     - R16: Assign 3 jokers randomly per user
     - QF: Assign 2 jokers randomly per user
     - SF/Final/Third: Assign 2 jokers total per user (combined pool)
   - **Group stage limit**: Each user should have exactly 36 group stage predictions
   - For finished matches:
     - Some predictions should match exactly (score points)
     - Some should match tendency only (score points)
     - Some should miss entirely (no points)
   - Run scoring calculation after creating predictions

**Command Options**:
- `--clear`: Delete all existing matches, predictions, and test users before creating
- `--users N`: Number of test users to create (default: 8)

**Implementation Notes**:
- Use transactions to ensure all-or-nothing creation
- Print progress messages during creation
- Validate data after creation (check counts, joker limits, etc.)
- Idempotent: Can be run multiple times safely with `--clear`

### 2. Predictions Page Frontend Changes

**Template**: `templates/predictions/prediction_list.html`

**Current Structure** (to be modified):
- Tab-based navigation (if exists) → Remove tabs
- Match rows grouped by date → Keep date grouping
- HTMX auto-save on individual predictions → Keep existing

**New Structure**:

```html
<div class="predictions-page">
  <!-- Header with filter -->
  <div class="page-header">
    <h1>🎯 Meine Tipps</h1>
    <div class="group-stage-counter">{{ group_stage_count }}/36</div>
    <div class="stage-filter">
      <button class="filter-toggle" id="filter-toggle">
        🔽 Filter
      </button>
      <div class="filter-dropdown" id="filter-dropdown" style="display: none;">
        <button data-stage="all">Alle Spiele</button>
        <button data-stage="gs">Gruppenphase</button>
        <button data-stage="r32">Achtelfinale (R32)</button>
        <button data-stage="r16">Achtelfinale (R16)</button>
        <button data-stage="qf">Viertelfinale</button>
        <button data-stage="sf">Halbfinale</button>
        <button data-stage="final">Finale</button>
      </div>
    </div>
  </div>

  <!-- Match list (scrollable) -->
  <div class="match-list" id="match-list">
    {% for date, matches in matches_by_date.items %}
      <div class="date-group">
        <h2 class="date-header">{{ date|date:"d. F Y" }}</h2>
        {% for match_data in matches %}
          {% include "predictions/prediction_row.html" with match=match_data.match prediction=match_data.prediction is_locked=match_data.is_locked %}
        {% endfor %}
      </div>
    {% endfor %}
  </div>

  <!-- HTMX polling for live updates -->
  <div hx-get="{% url 'prediction-updates' %}" 
       hx-trigger="every 60s" 
       hx-swap="none"
       hx-vals='{"last_update": "{{ last_update_timestamp }}"}'>
  </div>
</div>
```

**JavaScript Additions** (inline or in static file):

```javascript
// Auto-scroll to nearest upcoming match on page load
document.addEventListener('DOMContentLoaded', function() {
  const now = Date.now();
  const matchRows = document.querySelectorAll('[data-kickoff-timestamp]');
  let nearestMatch = null;
  let minDiff = Infinity;

  matchRows.forEach(row => {
    const kickoff = parseInt(row.dataset.kickoffTimestamp);
    const diff = kickoff - now;
    
    // Find nearest future match
    if (diff > 0 && diff < minDiff) {
      minDiff = diff;
      nearestMatch = row;
    }
  });

  // If no future matches, scroll to last match
  if (!nearestMatch && matchRows.length > 0) {
    nearestMatch = matchRows[matchRows.length - 1];
  }

  // Smooth scroll to match with offset for header
  if (nearestMatch) {
    const offset = 100; // Account for fixed header
    const elementPosition = nearestMatch.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - offset;
    
    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
  }
});

// Filter toggle functionality
document.getElementById('filter-toggle').addEventListener('click', function() {
  const dropdown = document.getElementById('filter-dropdown');
  dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
});

// Filter stage selection
document.querySelectorAll('[data-stage]').forEach(button => {
  button.addEventListener('click', function() {
    const stage = this.dataset.stage;
    
    // Update URL parameter
    const url = new URL(window.location);
    if (stage === 'all') {
      url.searchParams.delete('stage');
    } else {
      url.searchParams.set('stage', stage);
    }
    window.history.pushState({}, '', url);
    
    // Filter matches
    document.querySelectorAll('[data-match-stage]').forEach(match => {
      if (stage === 'all' || match.dataset.matchStage === stage) {
        match.style.display = '';
      } else {
        match.style.display = 'none';
      }
    });
    
    // Close dropdown
    document.getElementById('filter-dropdown').style.display = 'none';
  });
});

// Apply filter on page load based on URL parameter
const urlParams = new URLSearchParams(window.location.search);
const stageParam = urlParams.get('stage');
if (stageParam) {
  const button = document.querySelector(`[data-stage="${stageParam}"]`);
  if (button) button.click();
}
```

### 3. Match Row Template Updates

**Template**: `templates/predictions/prediction_row.html`

**Add data attributes** for filtering and auto-scroll:

```html
<div class="match-row" 
     id="match-{{ match.id }}"
     data-match-stage="{{ match.round }}"
     data-kickoff-timestamp="{{ match.kickoff|date:'U' }}">
  
  <!-- Existing match row content -->
  <!-- ... team names, scores, prediction inputs, joker toggle, etc. ... -->
  
</div>
```

### 4. Live Update Endpoint (HTMX Polling)

**New View**: `PredictionUpdatesView`

**Location**: `predictions/views.py`

**Purpose**: Return updated match results for polling

**Implementation**:

```python
class PredictionUpdatesView(LoginRequiredMixin, View):
    """
    Return match updates since last check.
    
    Compares client's last_update timestamp with server state.
    Returns HTMX commands to update only changed match rows.
    """
    
    def get(self, request: HttpRequest) -> HttpResponse:
        last_update = request.GET.get('last_update', 0)
        try:
            last_update_time = timezone.datetime.fromtimestamp(
                int(last_update), tz=timezone.utc
            )
        except (ValueError, TypeError):
            last_update_time = timezone.now() - timezone.timedelta(hours=24)
        
        # Find matches updated since last check
        updated_matches = Match.objects.filter(
            updated_at__gt=last_update_time,
            status='finished'
        ).select_related('team_home', 'team_away')
        
        if not updated_matches.exists():
            # No updates, return empty response
            return HttpResponse('', content_type='text/html')
        
        # Build HTMX OOB updates for changed matches
        user = request.user
        predictions = MatchPrediction.objects.filter(
            user=user,
            match__in=updated_matches
        ).select_related('match')
        
        prediction_map = {p.match_id: p for p in predictions}
        
        html_parts = []
        for match in updated_matches:
            prediction = prediction_map.get(match.id)
            is_locked = match.kickoff <= timezone.now()
            
            # Render updated row with OOB swap
            row_html = render_to_string(
                'predictions/prediction_row.html',
                {
                    'match': match,
                    'prediction': prediction,
                    'is_locked': is_locked,
                }
            )
            # Add OOB attribute for HTMX to swap
            row_html = row_html.replace(
                f'id="match-{match.id}"',
                f'id="match-{match.id}" hx-swap-oob="true"'
            )
            html_parts.append(row_html)
        
        return HttpResponse(''.join(html_parts), content_type='text/html')
```

**URL Route**:
```python
path("updates/", PredictionUpdatesView.as_view(), name="prediction-updates")
```

## Data Flow

### Page Load Flow

1. User navigates to `/predictions/`
2. Server renders `PredictionListView`:
   - Query all matches ordered by kickoff
   - Query user's predictions
   - Build match_data list with prediction, is_locked, joker info
   - Group by date
   - Pass to template
3. Template renders full match list
4. JavaScript runs on DOMContentLoaded:
   - Find nearest upcoming match by timestamp
   - Scroll to match smoothly
5. Check URL for `?stage=<stage>` parameter:
   - Apply filter if present
   - Show/hide matches based on stage
6. HTMX starts polling every 60 seconds for updates

### Filter Interaction Flow

1. User clicks "🔽 Filter" button
2. Dropdown shows stage options
3. User clicks stage (e.g., "Gruppenphase")
4. JavaScript:
   - Updates URL parameter `?stage=gs`
   - Hides all match rows where `data-match-stage !== 'gs'`
   - Closes dropdown
5. If user reloads page, filter persists via URL parameter

### Live Update Flow

1. Every 60 seconds, HTMX sends GET to `/predictions/updates/`
2. Server compares `last_update` timestamp with match `updated_at` fields
3. If matches have been updated (results changed):
   - Render updated prediction_row.html for each changed match
   - Add `hx-swap-oob="true"` attribute
   - Return HTML fragments
4. HTMX receives response and swaps updated rows in-place
5. User sees new results without page reload
6. No visual flicker for unchanged matches

## UI/UX Considerations

### Auto-scroll Behavior

- Scroll offset: 100px from top (account for fixed header)
- Smooth scroll animation (300-500ms)
- Run only on initial page load, not on filter changes
- If no upcoming matches, scroll to last match (tournament finished)
- If no matches at all, show empty state message

### Filter UI

- Filter button always visible in header (fixed position optional)
- Dropdown closes on selection or outside click
- Active filter highlighted in button text: "🔽 Filter (Gruppenphase)"
- Filter state persists via URL parameter (shareable links)
- Filtered-out matches: `display: none` (not removed from DOM)

### Live Updates

- No loading spinner during polling (silent updates)
- Optional: Subtle flash animation on updated rows (fade-in effect)
- Polling interval: 60 seconds (configurable)
- Stop polling if user is inactive (optional: detect `visibilitychange`)

### Responsive Design

- Filter dropdown: Full-width on mobile, fixed-width on desktop
- Match list: Single column, scroll vertically
- Auto-scroll works on all screen sizes
- Touch-friendly filter buttons (min 44x44px tap target)

## Database Schema Changes

**No schema changes required**. All functionality uses existing models:
- `Match` (team_home, team_away, kickoff, round, status, goals_home, goals_away, updated_at)
- `MatchPrediction` (user, match, predicted_goals_home, predicted_goals_away, joker_active, points_earned)
- `Team` (name)
- `User` (Django auth)

## Testing Strategy

### Management Command Tests

**Location**: `predictions/tests/test_management_commands.py`

**Test Cases**:
1. Command creates exactly 104 matches
2. Command creates correct number of group stage matches (48)
3. Command creates correct number of knockout matches (56)
4. Each group has exactly 3 matches (round-robin)
5. Command creates specified number of users (default 8)
6. Each user has predictions (70-90% coverage)
7. Joker counts per user match limits:
   - 0 in group stage
   - 3 in R32
   - 3 in R16
   - 2 in QF
   - 2 combined in SF/Final/Third
8. Each user has exactly 36 group stage predictions
9. Some matches have results (status='finished')
10. `--clear` option removes existing data before creating
11. Command is idempotent (can run multiple times with `--clear`)

### Frontend Tests

**Location**: `predictions/tests/test_views.py` and JavaScript tests

**Test Cases**:
1. PredictionListView returns all matches ordered by kickoff
2. Auto-scroll JavaScript identifies correct nearest upcoming match
3. Auto-scroll falls back to last match if all matches finished
4. Filter parameter `?stage=gs` hides non-group-stage matches
5. Filter parameter persists across page reloads
6. PredictionUpdatesView returns empty response if no updates
7. PredictionUpdatesView returns updated rows for changed matches
8. HTMX OOB swap correctly updates match rows without full reload
9. Polling sends correct `last_update` timestamp

### Integration Tests

1. Create test data, load predictions page, verify all matches visible
2. Apply filter, verify correct matches shown/hidden
3. Simulate match result change, verify polling updates match row
4. Navigate with filter, verify URL parameter persists
5. Reload page with filter, verify filter still applied

## Performance Considerations

### Query Optimization

- Use `select_related('team_home', 'team_away')` to avoid N+1 queries
- Use `prefetch_related` for predictions if needed
- Index on `Match.updated_at` for efficient polling queries
- Index on `Match.kickoff` for ordering and filtering

### Frontend Performance

- Polling interval: 60 seconds (avoid server load)
- Use `display: none` for filtering (no DOM manipulation)
- Throttle/debounce filter button clicks (prevent rapid toggles)
- Lazy-load match rows if list becomes very large (future optimization)

### Caching Strategy

- No caching for prediction data (needs to be real-time for user)
- Optional: Cache match list for anonymous users (future optimization)
- Optional: Cache team names/flags (static data)

## Error Handling

### Management Command Errors

- Wrap in transaction: Rollback if any error occurs
- Validate data after creation (raise exception if validation fails)
- Print clear error messages for debugging
- Handle duplicate teams/matches gracefully with `get_or_create`

### Frontend Errors

- Polling failure: Silent fail, retry on next interval
- Filter JavaScript error: Log to console, don't break page
- Auto-scroll error: Log to console, don't block page load

## Security Considerations

- All views require authentication (`LoginRequiredMixin`)
- Filter parameter: Validate against known stage codes (prevent injection)
- Polling endpoint: Only return data for authenticated user's predictions
- No sensitive data in `data-*` attributes (only IDs and timestamps)
- CSRF token required for all POST requests (existing)

## Accessibility

- Filter button: Proper ARIA labels and keyboard navigation
- Auto-scroll: Don't trap focus, allow keyboard users to navigate normally
- Filter dropdown: Close on Escape key, focus management
- Match rows: Maintain existing accessibility features (form labels, etc.)
- Screen reader announcements for filter changes (optional)

## Deployment Notes

- Run `python manage.py create_wm2026_testdata --clear` on test/dev environments
- Do not run on production (command is for testing only)
- No migrations required (uses existing schema)
- No new dependencies required
- Frontend changes are backward-compatible (progressive enhancement)

## Future Enhancements (Out of Scope)

- WebSocket for real-time updates (instead of polling)
- Push notifications when match results change
- Virtualized scrolling for very long match lists
- Advanced filters (by team, by date range, by prediction status)
- Export predictions to PDF/CSV
- Match detail page with prediction statistics
- Admin interface for match management
