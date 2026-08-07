# Proposal: Optimize Match Predictions Polling with Version Tracking

## Summary

Reduce server load and network overhead on the match predictions page by implementing version-based change detection using match scores. Skip unnecessary rendering when predictions haven't changed (post-kickoff), update match header via HTMX Out-of-Band swaps, and adjust polling interval from implicit 1s to explicit 30s.

## Problem

The current HTMX polling implementation on `/predictions/match/<id>/all/` polls every second and re-renders the entire predictions list on every request, regardless of whether anything changed:

**Performance inefficiencies:**
- Every 1s poll triggers full template rendering (match header + all predictions)
- Post-kickoff, predictions are locked - only match score and derived points change
- When score hasn't changed, predictions and points are identical to previous poll
- Rendering dozens of user rows with stats every second wastes CPU and bandwidth
- 1s polling during idle periods is unnecessarily aggressive

**Change detection gap:**
- No mechanism to detect if anything changed since last poll
- Server always renders full response even when data is identical
- Client always swaps DOM even when HTML is byte-identical
- Match header (score card) isn't independently updatable - requires full swap

**Polling behavior issues:**
- Polling interval not explicitly set in template (relies on view context default)
- Pre-kickoff: predictions can change (users editing), polling needed
- Post-kickoff: only score changes trigger updates, but we poll for everything
- No differentiation between these states in polling logic

## Solution

### Version-Based Change Detection

Track match score as a version string: `{goals_home}:{goals_away}`

**Pre-kickoff:** Score is `-:-` (both null), version is stable until kickoff
**Post-kickoff:** Version changes only when admin updates match result

On each poll request:
1. Client sends current version in query param: `?version=1:0`
2. Server compares to current match score
3. If unchanged (post-kickoff): return empty 304-style response with version header
4. If changed (or pre-kickoff): render full update with new version header

This eliminates 90%+ of rendering work post-kickoff when score is stable.

### HTMX Out-of-Band (OOB) Header Swap

Currently match header is embedded in predictions content. When predictions update, entire block re-renders including header.

Extract match header into separate partial: `predictions/partials/match_header.html`

On update responses, include header as OOB swap:
```html
<div id="match-header" hx-swap-oob="true">
  ... updated header ...
</div>
... predictions content ...
```

This allows:
- Score updates without re-rendering predictions
- Independent cache/update logic for header vs content
- Cleaner separation of concerns

### Explicit 30s Polling Interval

Change from implied 1s to explicit 30s polling:
- Reduces server load 30x
- Still provides timely updates (match scores change every few minutes)
- Aligns with typical admin workflow (score updates happen during/after matches)
- Pre-kickoff: 30s is sufficient for prediction edits (users don't edit every second)
- Post-kickoff: 30s with version check means most polls are no-ops

### Optimized View Logic

**MatchPredictionsUpdateView changes:**

```python
def get(self, request, match_id):
    match = get_object_or_404(Match, pk=match_id)
    now = timezone.now()
    is_locked = match.kickoff <= now
    
    # Build version from match score
    current_version = f"{match.goals_home}:{match.goals_away}"
    client_version = request.GET.get("version", "")
    
    # Post-kickoff: early exit if nothing changed
    if is_locked and client_version == current_version:
        response = HttpResponse("")  # Empty body
        response["HX-Trigger"] = json.dumps({"version": current_version})
        return response
    
    # Changed or pre-kickoff: full render
    user_predictions = build_match_predictions_list(...)
    
    # Render header partial (for OOB swap)
    header_html = render_to_string(
        "predictions/partials/match_header.html",
        {"match": match},
        request,
    )
    
    # Render content partial
    content_html = render_to_string(
        "predictions/partials/match_predictions_content.html",
        context,
        request,
    )
    
    # Combine with OOB directive
    response = HttpResponse(
        f'<div id="match-header" hx-swap-oob="true">{header_html}</div>'
        f'{content_html}'
    )
    response["HX-Trigger"] = json.dumps({"version": current_version})
    return response
```

### Template Changes

**match_predictions_page.html:**
- Extract match header section into separate `<div id="match-header">`
- Update `#predictions-content` to include version in hx-get URL
- Set explicit `hx-trigger="every 10s"`
- Add JavaScript listener to update version param from HX-Trigger header

**New partial: match_header.html:**
- Contains match score card (team names, flags, score)
- Independently swappable via OOB

## Non-Goals

- WebSocket or server-sent events for real-time push
- Delta/diff updates (sending only changed rows)
- Client-side state diffing or caching
- Changing polling interval based on match phase (10s is fine for all states)
- Optimizing pre-kickoff polling differently (predictions visible throughout)
- Adding loading indicators or skeleton screens

## Success Criteria

- Post-kickoff polls with unchanged score return empty response (no rendering)
- Server load reduced by ~90% during idle match periods
- Match header updates independently when score changes
- Polling interval explicitly set to 30s in template
- Version tracking prevents redundant DOM swaps
- Pre-kickoff polling still works (predictions visible and update)
- No visual regressions (page looks and behaves identically)
- Response times <100ms for no-change responses
- Response times <500ms for changed responses

## Impact

**Before optimization:**
- 1 poll/second × 60s/minute = 60 full renders/minute
- Post-kickoff with stable score: 60 renders producing identical HTML
- Each render: query predictions, calculate stats, render template (~50-200ms)

**After optimization:**
- 2 polls/minute (every 30s)
- Post-kickoff with stable score: 2 version checks (~5ms each), 0 renders
- When score changes: 1 full render, header OOB swap
- **Result: 30x fewer requests, 95%+ fewer renders**
