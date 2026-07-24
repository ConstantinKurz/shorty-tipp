## 1. Create Ranking View

- [x] 1.1 Create `RankingView` class in `users/views.py` (or dedicated view file)
- [x] 1.2 Inherit from `LoginRequiredMixin` and `TemplateView`
- [x] 1.3 Set `template_name = "ranking.html"`
- [x] 1.4 Import `RankingService` from `scoring.services`
- [x] 1.5 Import `User` model for champion enrichment
- [x] 1.6 Implement `get_context_data()` method
- [x] 1.7 Call `RankingService.get_current_leaderboard()` to get ranked users
- [x] 1.8 Extract user IDs from leaderboard data
- [x] 1.9 Query users with `select_related('predicted_champion')` for champion data
- [x] 1.10 Create user dict mapping user_id to User instance
- [x] 1.11 Enrich leaderboard entries with `predicted_champion` from users dict
- [x] 1.12 Add enriched leaderboard to context as 'leaderboard'
- [x] 1.13 Add type hints for view methods

## 2. Create Flag Helper Function

- [x] 2.1 Create `get_flag_emoji(country_code: str) -> str` function in `users/utils.py` or as template tag
- [x] 2.2 Implement conversion from ISO code to Unicode regional indicator symbols
- [x] 2.3 Handle None/empty country codes gracefully (return empty string)
- [x] 2.4 Add docstring explaining emoji conversion
- [x] 2.5 Register as template filter if implemented as tag

## 3. Add URL Route

- [x] 3.1 Import RankingView in `tipapp/urls.py`
- [x] 3.2 Add `path("ranking/", RankingView.as_view(), name="ranking")` to urlpatterns
- [x] 3.3 Ensure route is within authenticated area (if using URL-level auth)
- [x] 3.4 Test URL reverse with `reverse('ranking')` in tests

## 4. Create Ranking Template

- [x] 4.1 Create `templates/ranking.html` extending `base.html`
- [x] 4.2 Set page title to "Ranking - WM 2026 Tippspiel"
- [x] 4.3 Add gradient background wrapper matching login.html (min-h-screen flex items-center justify-center bg-gradient-to-br from-zinc-100 to-zinc-200 dark:from-zinc-900 dark:to-zinc-800)
- [x] 4.4 Create main card container with login page styling (bg-white dark:bg-zinc-800 rounded-2xl shadow-xl border border-zinc-200 dark:border-zinc-700 p-8)
- [x] 4.5 Add card heading "🏆 Ranking" with zinc styling (text-2xl font-bold text-zinc-900 dark:text-white)
- [x] 4.6 Create responsive table with Tailwind classes inside card
- [x] 4.7 Add table headers: Rang, Name, Punkte, Champion, Exakt, Joker
- [x] 4.8 Style headers with zinc-700/zinc-300 background for dark/light mode
- [x] 4.9 Loop through leaderboard entries with `{% for entry in leaderboard %}`
- [x] 4.10 Display `entry.rank` in first column
- [x] 4.11 Display `entry.username` in second column
- [x] 4.12 Display `entry.total_points` in third column
- [x] 4.13 Display champion flag emoji + team name from entry.predicted_champion (or "–" if None)
- [x] 4.14 Display `entry.exact_match_count` in fifth column
- [x] 4.15 Display `entry.jokers_used` in sixth column
- [x] 4.16 Add zebra striping with subtle zinc background alternation
- [x] 4.17 Add hover effect with hover:bg-zinc-700 dark:hover:bg-zinc-600
- [x] 4.18 Create mobile-specific stacked card layout for <640px breakpoint (hidden table, show cards)
- [x] 4.19 Ensure text colors work in dark/light mode (text-zinc-100/text-zinc-900)
- [x] 4.20 Match form field styling from login (rounded-lg, focus:ring-emerald-500)

## 5. Update Base Template Navigation

- [x] 5.1 Open `templates/base.html`
- [x] 5.2 Add navigation section if not exists (header with nav links)
- [x] 5.3 Add "Ranking" link with `href="{% url 'ranking' %}"`
- [x] 5.4 Style nav links with fintech aesthetic (zinc colors, hover states)
- [x] 5.5 Add active state indication if on ranking page (optional)
- [x] 5.6 Ensure nav is responsive (hamburger menu on mobile optional)
- [x] 5.7 Test navigation link is visible when logged in

## 6. Write View Tests

- [x] 6.1 Create `tests/test_ranking_view.py` in users/ or tipapp/
- [x] 6.2 Import necessary models, view, pytest fixtures, RankingService
- [x] 6.3 Create fixture: `create_users_with_points()` - multiple users with different points
- [x] 6.4 Test: GET /ranking/ as authenticated user returns 200
- [x] 6.5 Test: GET /ranking/ as unauthenticated user redirects to /login/
- [x] 6.6 Test: Response uses 'ranking.html' template
- [x] 6.7 Test: RankingService.get_current_leaderboard() is called (mock or verify context)
- [x] 6.8 Test: Leaderboard data includes rank, username, total_points, exact_match_count, jokers_used
- [x] 6.9 Test: Champion data is enriched correctly when user has predicted_champion
- [x] 6.10 Test: Champion data shows None when user has no predicted_champion
- [x] 6.11 Test: Verify tiebreaker logic matches service (points > exact > jokers_used)
- [x] 6.12 Test: Olympic-style ranking with shared ranks (1, 2, 2, 4)
- [x] 6.13 Test: Flag emoji generation for valid country codes
- [x] 6.14 Test: Flag function handles None/empty country code gracefully
- [x] 6.15 Test: No N+1 queries (use django-debug-toolbar or assertNumQueries)
- [x] 6.16 Run pytest to verify all ranking view tests pass

## 7. Manual Testing

- [x] 7.1 Start dev server and log in
- [x] 7.2 Create test users with varying points via Django shell/admin
- [x] 7.3 Assign predicted_champion to some users
- [x] 7.4 Set different exact_match_count and jokers_used values
- [x] 7.5 Navigate to /ranking/ via URL
- [x] 7.6 Verify ranking table displays correctly
- [x] 7.7 Verify olympic-style ranking for tied users
- [x] 7.8 Verify champion flags display as emojis
- [x] 7.9 Verify users without champion show placeholder
- [x] 7.10 Test responsive layout on mobile screen size
- [x] 7.11 Verify navigation link works from other pages
- [x] 7.12 Test dark/light mode toggle affects ranking page

## 8. Code Quality and Documentation

- [x] 8.1 Add docstrings to RankingView and helper functions
- [x] 8.2 Add type hints to all function signatures
- [x] 8.3 Run `ruff check` on modified Python files
- [x] 8.4 Run `ruff format` on modified Python files
- [x] 8.5 Run `mypy` on users/views.py
- [x] 8.6 Fix any type errors or linting issues
- [x] 8.7 Verify no unused imports

## 9. Final Verification

- [x] 9.1 Run full test suite with `pytest`
- [x] 9.2 Verify all new tests pass
- [x] 9.3 Verify existing tests still pass
- [x] 9.4 Check database queries (no N+1 issues with select_related)
- [x] 9.5 Verify ranking accuracy with manual calculation
- [x] 9.6 Test with empty database (no users)
- [x] 9.7 Test with single user
- [x] 9.8 Test with multiple users having same points
- [ ] 9.9 Commit changes with descriptive message
- [ ] 9.10 Update CHANGELOG or project docs if applicable
