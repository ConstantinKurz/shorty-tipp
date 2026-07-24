# Design: Match Phase Navigation

## Overview

Implement a phase-based navigation system for the predictions page with a sticky progress bar. The solution uses client-side filtering and vanilla JavaScript for instant phase switching.

## Architecture

### Component Structure

```
┌─────────────────────────────────────────────────────────┐
│ Sticky Progress Bar (position: sticky)                  │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Phase Tabs: [Gruppe] [R32] [R16] [VF] [HF] [3rd] [F]│ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ Progress: "Gruppenphase: 12/36 Tipps"               │ │
│ │ Jokers:   "Joker: 2/3 gesetzt" (knockout only)      │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ Match List (scrollable)                                 │
│ - Date headers                                          │
│ - Match rows (filtered by active phase)                 │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
View (Django)
    │
    ├─► Calculate predictions per phase
    ├─► Calculate jokers per phase  
    ├─► Pass phase_stats to template
    │
Template (Jinja2)
    │
    ├─► Render all matches with data-match-stage attribute
    ├─► Render phase tabs with data-phase attribute
    ├─► Embed phase_stats as JSON in data attribute
    │
JavaScript (Client)
    │
    ├─► Filter matches by phase (show/hide)
    ├─► Update progress display
    ├─► Update URL parameter
    └─► Persist selection
```

## Implementation Details

### 1. View Changes (predictions/views.py)

Add `phase_stats` to context:

```python
def get_phase_stats(user: User) -> dict[str, dict[str, int]]:
    """Calculate prediction and joker counts per tournament phase."""
    phases = ['group', 'r32', 'r16', 'qf', 'sf', '3rd', 'final']
    stats = {}
    
    for phase in phases:
        predictions = MatchPrediction.objects.filter(
            user=user,
            match__round=phase
        )
        jokers = predictions.filter(joker_active=True).count()
        
        stats[phase] = {
            'predictions': predictions.count(),
            'jokers': jokers,
            'total_matches': Match.objects.filter(round=phase).count(),
            'joker_limit': PredictionLimitService.get_joker_limit_for_round(phase),
        }
    
    return stats
```

### 2. Template Structure (predictions/prediction_list.html)

**Sticky Progress Bar:**

```html
<div class="sticky-phase-nav" id="phase-nav">
    <!-- Phase Tabs -->
    <div class="phase-tabs">
        <button data-phase="group" class="phase-tab active">Gruppe</button>
        <button data-phase="r32" class="phase-tab">R32</button>
        <button data-phase="r16" class="phase-tab">R16</button>
        <button data-phase="qf" class="phase-tab">VF</button>
        <button data-phase="sf" class="phase-tab">HF</button>
        <button data-phase="3rd" class="phase-tab">3.</button>
        <button data-phase="final" class="phase-tab">Finale</button>
    </div>
    
    <!-- Progress Display -->
    <div class="phase-progress" id="phase-progress">
        <span id="progress-predictions">0/0 Tipps</span>
        <span id="progress-jokers" class="hidden">0/0 Joker</span>
    </div>
</div>
```

**Phase Stats Data:**

```html
<div id="phase-stats-data" 
     data-stats='{{ phase_stats|json_script:"phase-stats" }}'
     class="hidden">
</div>
```

### 3. CSS Styling

```css
.sticky-phase-nav {
    position: sticky;
    top: 0;
    z-index: 40;
    background: white;
    border-bottom: 1px solid var(--border);
    padding: 0.5rem 1rem;
}

.phase-tabs {
    display: flex;
    gap: 0.25rem;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
}

.phase-tab {
    flex-shrink: 0;
    padding: 0.5rem 1rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.15s;
}

.phase-tab.active {
    background: var(--emerald-500);
    color: white;
}

.phase-progress {
    display: flex;
    gap: 1rem;
    padding-top: 0.5rem;
    font-size: 0.875rem;
    color: var(--zinc-600);
}

/* Mobile: smaller tabs */
@media (max-width: 640px) {
    .phase-tab {
        padding: 0.375rem 0.75rem;
        font-size: 0.75rem;
    }
}
```

### 4. JavaScript Logic

```javascript
const PhaseNav = {
    currentPhase: 'group',
    stats: {},
    
    init() {
        this.stats = JSON.parse(
            document.getElementById('phase-stats').textContent
        );
        
        // Bind tab clicks
        document.querySelectorAll('.phase-tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchPhase(tab.dataset.phase));
        });
        
        // Restore from URL
        const urlPhase = new URLSearchParams(location.search).get('phase');
        if (urlPhase && this.stats[urlPhase]) {
            this.switchPhase(urlPhase, false);
        }
    },
    
    switchPhase(phase, updateUrl = true) {
        this.currentPhase = phase;
        
        // Update tabs
        document.querySelectorAll('.phase-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.phase === phase);
        });
        
        // Filter matches
        document.querySelectorAll('.match-row').forEach(row => {
            row.style.display = row.dataset.matchStage === phase ? '' : 'none';
        });
        
        // Hide empty date headers
        this.updateDateHeaders();
        
        // Update progress display
        this.updateProgress(phase);
        
        // Update URL
        if (updateUrl) {
            const url = new URL(location);
            url.searchParams.set('phase', phase);
            history.pushState({}, '', url);
        }
    },
    
    updateProgress(phase) {
        const stat = this.stats[phase];
        const predictions = document.getElementById('progress-predictions');
        const jokers = document.getElementById('progress-jokers');
        
        predictions.textContent = `${stat.predictions}/${stat.total_matches} Tipps`;
        
        if (phase === 'group') {
            jokers.classList.add('hidden');
        } else {
            jokers.classList.remove('hidden');
            jokers.textContent = `${stat.jokers}/${stat.joker_limit} Joker`;
        }
    }
};

document.addEventListener('DOMContentLoaded', () => PhaseNav.init());
```

## Responsive Design

### Desktop (≥768px)
- Full tab bar with labels
- Progress displayed inline

### Mobile (<768px)
- Horizontally scrollable tabs
- Active tab auto-scrolled into view
- Progress stacked below tabs

## Edge Cases

1. **No matches in phase**: Show empty state message
2. **All phases empty**: Redirect to dashboard with message
3. **URL has invalid phase**: Default to 'group'
4. **HTMX updates**: Re-run filter after row updates

## Dependencies

- No new Python packages
- No new JavaScript libraries
- Uses existing Tailwind CSS classes
