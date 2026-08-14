# Design: Optimize Match Predictions Polling with Version Tracking

## Overview

Implement version-based change detection using match scores as the version identifier. When the match score hasn't changed post-kickoff, return an empty response. Extract match header into a separate partial for independent updates via HTMX Out-of-Band swaps. Set explicit 30s polling interval.

## Architecture

### Version Tracking Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Client: match_predictions_page.html                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Initial load: current version = "null:null" (pre-kickoff) │
│                                                             │
│  ┌──────────────────────────────────┐                       │
│  │  Every 30s:                      │                       │
│  │  GET /predictions/match/5/       │                       │
│  │      updates/?version=null:null  │                       │
│  └──────────────────────────────────┘                       │
│                   │                                         │
│                   ▼                                         │
│  ┌──────────────────────────────────────────────┐           │
│  │  Server: MatchPredictionsUpdateView         │           │
│  │  - current_version = "0:0" (kickoff, 0-0)   │           │
│  │  - client_version = "null:null"             │           │
│  │  - Mismatch → full render                   │           │
│  └──────────────────────────────────────────────┘           │
│                   │                                         │
│                   ▼                                         │
│  Response:                                                  │
│  <div id="match-header" hx-swap-oob="true">...</div>        │
│  <div id="predictions-content">...</div>                    │
│  HX-Trigger: {"version": "0:0"}                             │
│                   │                                         │
│                   ▼                                         │
│  Client updates version to "0:0"                            │
│  Next poll: ?version=0:0                                    │
│                   │                                         │
│                   ▼                                         │
│  Server: version matches → empty response                   │
│  HX-Trigger: {"version": "0:0"}                             │
│                                                             │
│  (90%+ of polls are now no-ops)                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Change Detection Logic

**Version format:** `{goals_home}:{goals_away}`

**Pre-kickoff:**
- `goals_home` and `goals_away` are `None`
- Version: `"None:None"` (string representation)
- Predictions can change → always render

**Post-kickoff:**
- `goals_home` and `goals_away` are integers (can be 0)
- Version: `"0:0"`, `"1:0"`, `"2:1"`, etc.
- Predictions locked → only version changes matter

**Implementation:**
```python
current_version = f"{match.goals_home}:{match.goals_away}"
client_version = request.GET.get("version", "")
is_locked = match.kickoff <= timezone.now()

# Optimization: skip if post-kickoff and unchanged
if is_locked and client_version == current_version:
    # Return empty with version header
    response = HttpResponse("")
    response["HX-Trigger"] = json.dumps({"version": current_version})
    return response
```

**Why this works:**
- Post-kickoff, predictions are immutable (locked by kickoff time)
- Points are deterministically calculated from match score + predictions
- If score unchanged, derived points unchanged
- No need to re-query or re-render

## Component Changes

### 1. Extract Match Header Partial

**New file:** `templates/predictions/partials/match_header.html`

Extract match header from `match_predictions_page.html`, following the design pattern from `prediction_row.html`:

```django
{# Match card header - matches prediction_row.html design #}
<div class="bg-zinc-50 dark:bg-zinc-800/50 rounded-xl p-4 border border-zinc-200 dark:border-zinc-700">
  <div class="flex flex-col sm:flex-row sm:items-center gap-3">
    <!-- Time and Lock Status -->
    <div class="flex items-center gap-2 sm:w-20 text-sm text-zinc-500 dark:text-zinc-400">
      {% if is_locked %}
        <span class="text-amber-500">🔒</span>
      {% endif %}
      <span class="font-medium">{{ match.kickoff|time:"H:i" }}</span>
    </div>

    <!-- Teams and Score Display -->
    <div class="flex-1 flex items-center justify-center gap-2 sm:gap-3">
      <!-- Home Team -->
      <div class="flex items-center gap-2 flex-1 justify-end">
        <span class="text-sm sm:text-base font-medium text-zinc-900 dark:text-white truncate">
          {{ match.team_home.name }}
        </span>
        <span class="text-lg">{{ match.team_home.fifa_code|slice:":2"|upper }}</span>
      </div>

      <!-- Score Display -->
      <div class="flex items-center gap-1">
        <div class="w-10 h-10 sm:w-12 sm:h-12 flex items-center justify-center text-lg font-bold text-zinc-900 dark:text-white">
          {% if match.goals_home is not None %}{{ match.goals_home }}{% else %}-{% endif %}
        </div>
        <span class="text-xl font-bold text-zinc-400 dark:text-zinc-500">:</span>
        <div class="w-10 h-10 sm:w-12 sm:h-12 flex items-center justify-center text-lg font-bold text-zinc-900 dark:text-white">
          {% if match.goals_away is not None %}{{ match.goals_away }}{% else %}-{% endif %}
        </div>
      </div>

      <!-- Away Team -->
      <div class="flex items-center gap-2 flex-1">
        <span class="text-lg">{{ match.team_away.fifa_code|slice:":2"|upper }}</span>
        <span class="text-sm sm:text-base font-medium text-zinc-900 dark:text-white truncate">
          {{ match.team_away.name }}
        </span>
      </div>
    </div>
  </div>

  <!-- Match Result Section -->
  <div class="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-700 flex items-center justify-between text-sm">
    <div class="flex items-center gap-2 text-zinc-600 dark:text-zinc-400">
      <span>Ergebnis:</span>
      {% if match.goals_home is not None and match.goals_away is not None %}
        <span class="font-bold {% if match.status == 'live' %}text-amber-500 animate-pulse{% else %}text-zinc-900 dark:text-white{% endif %}">
          {{ match.goals_home }}:{{ match.goals_away }}
          {% if match.status == 'live' %}
            <span class="ml-1 text-xs">🔴 Live</span>
          {% endif %}
        </span>
      {% else %}
        <span class="font-medium text-zinc-400 dark:text-zinc-500">-:-</span>
      {% endif %}
    </div>
    <span class="text-xs px-2 py-0.5 rounded-full bg-zinc-200 dark:bg-zinc-700 text-zinc-600 dark:text-zinc-400">
      {{ match.get_round_display }}
    </span>
  </div>
</div>
```

**Purpose:**
- Matches existing `prediction_row.html` design for consistency
- Independently swappable component via OOB
- Shows: teams, score, time, lock status, round, live indicator
- Reused in full page template

### 2. Update Full Page Template

**File:** `templates/predictions/match_predictions_page.html`

**Changes:**

1. **Wrap header with ID for OOB target:**
```django
<div id="match-header">
  {% include "predictions/partials/match_header.html" with match=match %}
</div>
```

2. **Update predictions content polling:**
```django
<div id="predictions-content"
     hx-get="{% url 'predictions:match_updates' match.pk %}?sort={{ sort_mode }}&version={{ current_version }}"
     hx-trigger="every 30s"
     hx-swap="innerHTML">
  {% include "predictions/partials/match_predictions_content.html" %}
</div>

<script>
  // Update version parameter on each response
  document.addEventListener('htmx:afterOnLoad', function(event) {
    if (event.detail.elt.id === 'predictions-content') {
      const trigger = JSON.parse(event.detail.xhr.getResponseHeader('HX-Trigger') || '{}');
      if (trigger.version) {
        // Update URL with new version
        const url = new URL(event.detail.elt.getAttribute('hx-get'), window.location.origin);
        url.searchParams.set('version', trigger.version);
        event.detail.elt.setAttribute('hx-get', url.toString());
      }
    }
  });
</script>
```

3. **Pass initial version to template:**

View must add `current_version` to context:
```python
context["current_version"] = f"{match.goals_home}:{match.goals_away}"
```

### 3. Update View - Version Check & OOB Response

**File:** `predictions/views.py`

**Modify:** `MatchPredictionsUpdateView.get()`

```python
def get(self, request: HttpRequest, match_id: int) -> HttpResponse:
    """
    Return updated predictions list for HTMX polling.
    
    Implements version-based change detection:
    - Post-kickoff: return empty if version unchanged (skip rendering)
    - Otherwise: return full content with OOB header swap
    """
    match = get_object_or_404(
        Match.objects.select_related("team_home", "team_away"),
        pk=match_id,
    )
    
    now = timezone.now()
    is_locked = match.kickoff <= now
    
    # Build version from match score
    current_version = f"{match.goals_home}:{match.goals_away}"
    client_version = request.GET.get("version", "")
    
    # OPTIMIZATION: Post-kickoff, skip if nothing changed
    if is_locked and client_version == current_version:
        # Return empty body with version header
        response = HttpResponse("")
        response["HX-Trigger"] = json.dumps({"version": current_version})
        return response
    
    # Version changed or pre-kickoff: full render needed
    
    # Get sort mode
    sort_mode = request.GET.get("sort", "match")
    if sort_mode not in ("match", "total"):
        sort_mode = "match"
    
    # Build predictions list (existing helper)
    user_predictions = build_match_predictions_list(
        match=match,
        sort_mode=sort_mode,
        current_user=request.user,
    )
    
    # Render match header partial (for OOB swap)
    header_html = render_to_string(
        "predictions/partials/match_header.html",
        {"match": match},
        request=request,
    )
    
    # Render predictions content
    context = {
        "match": match,
        "user_predictions": user_predictions,
        "sort_mode": sort_mode,
        "current_user": request.user,
        "origin": request.GET.get("from", "predictions"),
    }
    content_html = render_to_string(
        "predictions/partials/match_predictions_content.html",
        context,
        request=request,
    )
    
    # Combine with OOB directive for header
    html = (
        f'<div id="match-header" hx-swap-oob="true">{header_html}</div>'
        f'{content_html}'
    )
    
    response = HttpResponse(html)
    response["HX-Trigger"] = json.dumps({"version": current_version})
    
    return response
```

### 4. Update Full Page View - Add Initial Version

**File:** `predictions/views.py`

**Modify:** `MatchPredictionsView.get_context_data()`

Add `current_version` to context so template can initialize polling URL:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    match = self.get_object()
    
    # ... existing logic ...
    
    # Add version for HTMX polling
    context["current_version"] = f"{match.goals_home}:{match.goals_away}"
    
    return context
```

## Data Flow

### Pre-Kickoff Scenario

```
User loads page
  → match.goals_home = None, match.goals_away = None
  → current_version = "None:None"
  → Template: hx-get="...?version=None:None"

Poll 1 (30s later):
  → Server: is_locked = False → full render (predictions can change)
  → Returns: header OOB + content + HX-Trigger: {"version": "None:None"}

Poll 2 (30s later):
  → Server: is_locked = False → full render
  → Returns: header OOB + content

(Continues until kickoff)

Kickoff happens, admin sets score to 0:0:
  → match.goals_home = 0, match.goals_away = 0
  → current_version = "0:0"

Next poll:
  → client_version = "None:None", current_version = "0:0"
  → Mismatch → full render
  → Returns: HX-Trigger: {"version": "0:0"}
  → Client updates URL to ?version=0:0
```

### Post-Kickoff Stable Score

```
Poll N:
  → client_version = "0:0", current_version = "0:0"
  → is_locked = True, versions match
  → Return: HttpResponse("") + HX-Trigger: {"version": "0:0"}
  → Client: no DOM change (empty body)

Poll N+1:
  → Same → empty response

(Repeats until score changes)

Admin updates score to 1:0:
  → match.goals_home = 1
  → current_version = "1:0"

Next poll:
  → client_version = "0:0", current_version = "1:0"
  → Mismatch → full render
  → Predictions re-scored, points recalculated
  → Returns: updated header OOB + updated content
  → HX-Trigger: {"version": "1:0"}
```

## Performance Analysis

### Request Cost

**Old (1s polling, no version check):**
- Frequency: 60 requests/minute
- Per request: query DB, render template (~50-100ms)
- Cost: 3,000-6,000ms CPU/minute

**New (30s polling, with version check):**
- Frequency: 2 requests/minute
- Post-kickoff, stable score: version check only (~5ms)
- Post-kickoff, score changed: full render (~50-100ms)
- Pre-kickoff: full render (~50-100ms)
- Cost (stable): 10ms CPU/minute (99.8% reduction)
- Cost (changing): 100-200ms CPU/minute (97% reduction)

### Network Overhead

**Old:**
- 60 responses/minute × ~20KB each = ~1.2MB/minute/user
- Mostly redundant (identical HTML)

**New:**
- 2 responses/minute
- Stable score: 2 × ~100 bytes (headers only) = ~200 bytes/minute
- Changing score: 1 × ~20KB (when needed)
- Reduction: 99.8%+ during stable periods

## Testing Strategy

### Unit Tests

**Test version check logic:**
```python
def test_update_view_returns_empty_when_version_unchanged_post_kickoff():
    # Match after kickoff with score 1:0
    match = create_match(kickoff=timezone.now() - timedelta(hours=1),
                         goals_home=1, goals_away=0)
    
    # Poll with matching version
    response = client.get(f"/predictions/match/{match.pk}/updates/?version=1:0")
    
    assert response.status_code == 200
    assert response.content == b""  # Empty body
    assert "HX-Trigger" in response
    trigger = json.loads(response["HX-Trigger"])
    assert trigger["version"] == "1:0"

def test_update_view_renders_when_version_changed():
    match = create_match(kickoff=timezone.now() - timedelta(hours=1),
                         goals_home=2, goals_away=1)
    
    # Poll with old version
    response = client.get(f"/predictions/match/{match.pk}/updates/?version=1:0")
    
    assert response.status_code == 200
    assert len(response.content) > 0  # Has content
    assert b'hx-swap-oob="true"' in response.content  # OOB directive
    trigger = json.loads(response["HX-Trigger"])
    assert trigger["version"] == "2:1"

def test_update_view_always_renders_pre_kickoff():
    match = create_match(kickoff=timezone.now() + timedelta(hours=1),
                         goals_home=None, goals_away=None)
    
    # Poll twice with same version
    response1 = client.get(f"/predictions/match/{match.pk}/updates/?version=None:None")
    response2 = client.get(f"/predictions/match/{match.pk}/updates/?version=None:None")
    
    # Both render (predictions can change pre-kickoff)
    assert len(response1.content) > 0
    assert len(response2.content) > 0
```

### Integration Tests

**Test OOB swapping:**
```python
def test_match_header_updates_independently():
    # Load page, verify header present
    # Update match score via admin
    # Poll update endpoint
    # Verify response contains OOB header directive
    # Verify header content shows new score
```

**Test version propagation:**
```python
def test_client_version_updates_from_response():
    # Mock HTMX request
    # Verify HX-Trigger header contains new version
    # Verify subsequent poll includes updated version param
```

## Rollout Plan

1. Deploy with feature flag: `ENABLE_VERSION_TRACKING = False`
2. Monitor logs: count version-check hits vs full-render hits
3. Enable for 10% of users
4. Monitor metrics: response times, error rates
5. Gradually increase to 100%
6. Remove feature flag

## Monitoring

**Metrics to track:**
- `predictions.update.version_check_hit`: version matched, empty response
- `predictions.update.version_check_miss`: version changed, full render
- `predictions.update.pre_kickoff`: pre-kickoff full render
- `predictions.update.response_time`: p50, p95, p99
- `predictions.update.requests_per_minute`: overall load

**Expected post-rollout:**
- 90%+ requests are version_check_hit (post-kickoff stable matches)
- p95 response time < 50ms (empty responses dominate)
- Requests/minute reduced 30x (from 1s to 30s polling)
