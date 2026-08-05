# Design: Rules and How-To Page

## Overview

Implement a comprehensive, user-friendly rules page that explains both the game mechanics and website usage. The page should be accessible from main navigation and use collapsible sections powered by HTMX and Tailwind for better UX.

## Architecture

### Component Structure

```
Rules Page (/rules/)
├── Hero Section
│   └── Title + brief description
├── Game Rules Section
│   ├── Match Scoring (collapsible)
│   │   ├── Point categories with examples
│   │   └── Scoring precedence explanation
│   ├── Round Multipliers (collapsible)
│   │   └── Table with multipliers by phase
│   ├── Group Stage Limit (collapsible)
│   │   └── 36 out of 72 matches explanation
│   ├── Joker System (collapsible)
│   │   ├── How jokers work (double points)
│   │   └── Distribution by round
│   ├── Champion Prediction (collapsible)
│   │   ├── Bonus points explanation
│   │   └── Category A vs B teams
│   └── Ranking & Tiebreakers (collapsible)
│       ├── Total score calculation
│       └── Tiebreaking rules
├── How to Use Section
│   ├── Making Predictions (collapsible)
│   │   ├── Where to find matches
│   │   ├── How to enter scores
│   │   └── Deadline warnings
│   ├── Setting Jokers (collapsible)
│   │   ├── How to select jokers
│   │   └── Limitations per round
│   ├── Champion Selection (collapsible)
│   │   ├── Settings page location
│   │   └── Deadline (before first match)
│   ├── Viewing Rankings (collapsible)
│   │   ├── Leaderboard explanation
│   │   └── Your position
│   └── Seeing Others' Predictions (collapsible)
│       ├── Match-based view
│       └── Privacy note (only after match starts)
└── Quick Links Section
    ├── → Make Predictions
    ├── → View Rankings
    └── → User Settings

Main Navigation (base.html)
├── ... existing links ...
├── Rules (new)
└── ... existing links ...
```

### Data Flow

```
Rules View (GET)
    │
    ├─► Render static template (no database queries)
    └─► Return rules page with collapsed sections

Collapse/Expand (Client-side)
    │
    ├─► Toggle visibility of section content
    ├─► Rotate chevron icon
    └─► (Optional) Save expansion state to localStorage
```

## Implementation Details

### 1. URL Configuration

**tipapp/urls.py:**

```python
from django.urls import path
from users import views as users_views

urlpatterns = [
    # ... existing patterns ...
    path("rules/", users_views.RulesView.as_view(), name="rules"),
]
```

### 2. View

**users/views.py:**

```python
from django.views.generic import TemplateView

class RulesView(TemplateView):
    """Display game rules and how-to guide."""
    template_name = 'users/rules.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Rules & How to Play'
        return context
```

### 3. Template Structure

**templates/users/rules.html:**

- Extend `base.html`
- Use Tailwind utility classes for styling
- Implement collapsible sections using HTMX or Alpine.js-style approach
- Each section has:
  - Header with chevron icon
  - Hidden/shown content div
  - `hx-get` or click handler to toggle visibility

**Collapsible Section Pattern:**

```html
<div class="border rounded-lg mb-4">
  <button 
    class="w-full px-6 py-4 flex justify-between items-center text-left hover:bg-gray-50 dark:hover:bg-gray-800"
    onclick="toggleSection('section-id')"
  >
    <h3 class="text-lg font-semibold">Section Title</h3>
    <svg class="w-5 h-5 transform transition-transform" id="icon-section-id">
      <!-- Chevron icon -->
    </svg>
  </button>
  <div id="section-id" class="hidden px-6 py-4 border-t">
    <!-- Section content -->
  </div>
</div>
```

### 4. JavaScript for Collapse/Expand

**Inline or in base.html:**

```javascript
function toggleSection(sectionId) {
  const content = document.getElementById(sectionId);
  const icon = document.getElementById('icon-' + sectionId);
  
  if (content.classList.contains('hidden')) {
    content.classList.remove('hidden');
    icon.classList.add('rotate-180');
  } else {
    content.classList.add('hidden');
    icon.classList.remove('rotate-180');
  }
}
```

### 5. Navigation Link

**templates/base.html:**

Update the main navigation to include a Rules link:

```html
<nav>
  <a href="{% url 'home' %}">Home</a>
  <a href="{% url 'prediction-list' %}">Predictions</a>
  <a href="{% url 'rules' %}">Rules</a> <!-- New -->
  <a href="{% url 'settings' %}">Settings</a>
  <a href="{% url 'logout' %}">Logout</a>
</nav>
```

## Content Strategy

### Simplified Language
- Avoid technical jargon
- Use concrete examples (e.g., "Prediction 3:2, Result 1:0 → 5 points")
- Short paragraphs (2-3 sentences max)
- Bullet points for lists

### Visual Hierarchy
- Clear section headers
- Use tables for multipliers and point distributions
- Highlight key numbers (points, deadlines) with colored badges
- Whitespace between sections

### Examples
- Each scoring category should show 2-3 examples
- Use realistic match scenarios
- Highlight the calculation process

## Mobile Considerations

- Full-width collapsible sections
- Larger tap targets (min 44px)
- Readable font sizes (min 16px)
- No horizontal scrolling
- Tables convert to stacked layout on mobile

## Dark Mode

- Follow existing dark mode patterns from the app
- Use `dark:` Tailwind modifiers for all color classes
- Ensure sufficient contrast for readability
- Test chevron icon visibility in both modes

## Accessibility

- Semantic HTML (`<section>`, `<article>`, `<h2>`, `<h3>`)
- ARIA labels for collapsible buttons
- Keyboard navigation support (Enter/Space to toggle)
- Focus indicators on interactive elements
- Alt text for any icons or images

## Performance

- No external requests
- Minimal JavaScript
- CSS transitions for smooth collapse/expand
- No heavy dependencies
- Page should load instantly (static content)

## Future Enhancements (Out of Scope)

- Search/filter within rules
- Anchor links to specific sections
- Printable version
- Video tutorials
- FAQ section
- Multi-language support
