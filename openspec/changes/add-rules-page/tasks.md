# Tasks: Rules and How-To Page

## Task 1: Create RulesView and URL routing

### Goal
Set up the view and URL configuration for the rules page.

### Scope
- Add `RulesView` class to `users/views.py` (TemplateView)
- Add `/rules/` URL pattern to `tipapp/urls.py`
- View should set page title in context

### Out of Scope
- Template creation
- Navigation link
- Content writing

### Acceptance Criteria
- [x] `RulesView` exists in `users/views.py`
- [x] View extends `TemplateView`
- [x] View specifies `template_name = 'users/rules.html'`
- [x] Context includes `page_title`
- [x] URL pattern `/rules/` routes to `RulesView`
- [x] URL has name `rules`

### Required Tests
- Test that `/rules/` URL resolves to `RulesView`
- Test that anonymous users can access the page (no login required)
- Test that page title is in context

---

## Task 2: Create base rules template structure

### Goal
Build the HTML structure for the rules page with all sections outlined.

### Scope
- Create `templates/users/rules.html`
- Extend `base.html`
- Create hero section with title and description
- Create empty collapsible section structure for:
  - Match Scoring
  - Round Multipliers
  - Group Stage Limit
  - Joker System
  - Champion Prediction
  - Ranking & Tiebreakers
  - Making Predictions
  - Setting Jokers
  - Champion Selection
  - Viewing Rankings
  - Seeing Others' Predictions
- Add quick links section at bottom
- Add `toggleSection` JavaScript function

### Out of Scope
- Content writing (add placeholder text only)
- Styling beyond basic Tailwind
- Navigation link

### Acceptance Criteria
- [x] Template extends `base.html`
- [x] Hero section with title and intro paragraph
- [x] All 11 sections have collapsible structure
- [x] Each section has header button, chevron icon, and hidden content div
- [x] Unique IDs for each section
- [x] JavaScript function toggles visibility and icon rotation
- [x] Quick links section with 3 links (predictions, ranking, settings)
- [x] Template renders without errors

### Required Tests
- Visual test: page loads and displays structure
- Visual test: clicking section headers expands/collapses content
- Visual test: chevron icons rotate correctly

---

## Task 3: Write game rules content

### Goal
Fill in all game rules sections with user-friendly explanations and examples.

### Scope
- Write content for 6 game rules sections:
  - Match Scoring (6-5-4-3-1-0 system with 3 examples per category)
  - Round Multipliers (table with all phases)
  - Group Stage Limit (36 out of 72 explanation)
  - Joker System (how it works, distribution table)
  - Champion Prediction (bonus points, A/B categories)
  - Ranking & Tiebreakers (score calculation, tiebreaking rules)
- Use simplified language
- Include concrete examples with calculations
- Use tables for structured data
- Source content from `docs/rules/wm2026-rules.md`

### Out of Scope
- How-to-use-website content
- Styling refinements
- Visual examples or diagrams

### Acceptance Criteria
- [x] All 6 game rules sections have complete content
- [x] Match scoring section shows all 6 categories with examples
- [x] Round multipliers section has complete table
- [x] Joker distribution table is accurate and clear
- [x] Champion prediction explains A/B categories (20/30 points)
- [x] All examples show clear calculations
- [x] Content uses simple, non-technical language
- [x] Content is accurate per `docs/rules/wm2026-rules.md`

### Required Tests
- Manual review: content is accurate
- Manual review: examples are clear and correct
- Manual review: language is user-friendly

---

## Task 4: Write website usage content

### Goal
Fill in all "how to use" sections with step-by-step guides.

### Scope
- Write content for 5 website usage sections:
  - Making Predictions (where to go, how to enter, deadline warnings)
  - Setting Jokers (how to select, limitations)
  - Champion Selection (settings page, deadline)
  - Viewing Rankings (leaderboard explanation, finding your position)
  - Seeing Others' Predictions (match-based view, privacy note)
- Include links to relevant pages
- Reference actual URLs and navigation paths

### Out of Scope
- Game rules content
- Screenshots or videos
- Troubleshooting guides

### Acceptance Criteria
- [x] All 5 website usage sections have complete content
- [x] Each section explains step-by-step how to use the feature
- [x] Relevant internal links are included (predictions, settings, ranking)
- [x] Deadline information is clearly stated
- [x] Privacy note about seeing others' predictions is included
- [x] Content matches actual website navigation and features

### Required Tests
- Manual review: instructions match actual website behavior
- Manual review: all links work correctly
- Manual test: follow instructions as a new user

---

## Task 5: Style and polish the rules page

### Goal
Apply Tailwind styling to make the page visually appealing and readable.

### Scope
- Style collapsible sections with borders, padding, hover effects
- Style headers with appropriate font sizes and weights
- Style tables for readability
- Add spacing between sections
- Style quick links as buttons/cards
- Ensure consistent color scheme
- Apply dark mode styles
- Make responsive for mobile

### Out of Scope
- Content changes
- JavaScript enhancements beyond toggle
- Animations (beyond simple transitions)

### Acceptance Criteria
- [x] Sections have clear visual separation
- [x] Headers are prominent and readable
- [x] Tables are well-formatted and responsive
- [x] Hover effects on interactive elements
- [x] Sufficient padding and whitespace
- [x] Dark mode works correctly
- [x] Mobile layout is readable (responsive)
- [x] Quick links are styled as prominent CTAs
- [x] Consistent with rest of site's design

### Required Tests
- Visual test on desktop (light and dark mode)
- Visual test on mobile (light and dark mode)
- Test hover states
- Test section transitions

---

## Task 6: Add rules link to main navigation

### Goal
Make the rules page accessible from the main navigation.

### Scope
- Update `templates/base.html` to include Rules link
- Position between Predictions and Settings (or appropriate location)
- Apply active state styling when on rules page
- Ensure responsive navigation still works

### Out of Scope
- Footer link
- Breadcrumbs
- Mobile menu changes (unless broken)

### Acceptance Criteria
- [x] Rules link appears in main navigation
- [x] Link points to `{% url 'rules' %}`
- [x] Link has appropriate text ("Rules" or "Rules & How-To")
- [x] Active state highlights when on `/rules/` page
- [x] Link is visible on all pages
- [x] Link works in mobile navigation
- [x] Navigation layout not broken

### Required Tests
- Visual test: link appears on all pages
- Visual test: active state on rules page
- Visual test: mobile navigation includes link
- Click test: link navigates to rules page

---

## Task 7: Add accessibility features

### Goal
Ensure the rules page is fully accessible.

### Scope
- Add ARIA labels to collapsible section buttons
- Add `aria-expanded` attribute that toggles
- Add `aria-controls` attribute linking button to content
- Ensure keyboard navigation works (Enter/Space to toggle)
- Add focus indicators to interactive elements
- Use semantic HTML (`<section>`, `<article>`)
- Ensure sufficient color contrast

### Out of Scope
- Screen reader testing (though code should support it)
- Advanced keyboard shortcuts
- WCAG audit

### Acceptance Criteria
- [x] Section buttons have `aria-label` or `aria-labelledby`
- [x] Buttons have `aria-expanded="false"` / `"true"`
- [x] Buttons have `aria-controls` matching content div ID
- [x] Enter/Space keys toggle sections
- [x] Tab navigation follows logical order
- [x] Focus indicators visible on all interactive elements
- [x] Semantic HTML tags used appropriately
- [x] Color contrast meets WCAG AA standards

### Required Tests
- Keyboard test: Tab through page
- Keyboard test: Toggle sections with Enter/Space
- Visual test: focus indicators visible
- Automated test: run accessibility checker (if available)

---

## Task 8: Write tests for RulesView

### Goal
Add automated tests for the rules page view.

### Scope
- Test in `users/tests/test_views.py`
- Test URL resolution
- Test view accessibility (no login required)
- Test context data
- Test template used
- Test page contains key sections

### Out of Scope
- Content accuracy tests (manual review)
- JavaScript functionality tests
- Visual regression tests

### Acceptance Criteria
- [x] Test that `/rules/` URL resolves to `RulesView`
- [x] Test anonymous user can access page (status 200)
- [x] Test authenticated user can access page
- [x] Test correct template is used
- [x] Test page title in context
- [x] Test page contains "Match Scoring" section
- [x] Test page contains "How to Use" content
- [x] All tests pass

### Required Tests
```python
def test_rules_url_resolves()
def test_rules_view_accessible_to_anonymous()
def test_rules_view_accessible_to_authenticated()
def test_rules_view_uses_correct_template()
def test_rules_view_context_includes_page_title()
def test_rules_page_contains_scoring_section()
def test_rules_page_contains_joker_section()
```

---

## Task 9: Update README or documentation

### Goal
Document the new rules page in project documentation.

### Scope
- Update `README.md` to mention rules page
- Add rules page to feature list
- Update any user-facing documentation

### Out of Scope
- Technical documentation
- Architecture documentation
- API documentation

### Acceptance Criteria
- [ ] `README.md` mentions rules page
- [ ] Feature list includes rules page
- [ ] Brief description of what rules page contains

### Required Tests
- Manual review: documentation is accurate

---

## Implementation Notes

- **Task Order**: Tasks should be completed in sequence (1-9)
- **Content Source**: All game rules content must come from `docs/rules/wm2026-rules.md`
- **No Database**: This is a fully static page, no database queries
- **Performance**: Page should load instantly
- **Accessibility**: This is a content-heavy page, accessibility is critical

## Estimated Total Effort

- Task 1: 15 minutes
- Task 2: 30 minutes
- Task 3: 1.5 hours
- Task 4: 1 hour
- Task 5: 1 hour
- Task 6: 15 minutes
- Task 7: 45 minutes
- Task 8: 45 minutes
- Task 9: 15 minutes

**Total: ~6 hours**
