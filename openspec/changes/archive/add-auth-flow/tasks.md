## 1. Create Base Template

- [x] 1.1 Create templates/ directory if not exists
- [x] 1.2 Create templates/base.html with HTML5 doctype
- [x] 1.3 Add Tailwind CDN script with custom config
- [x] 1.4 Configure dark mode via tailwind.config (class strategy)
- [x] 1.5 Add meta viewport for mobile responsiveness
- [x] 1.6 Define {% block title %} with default "Shortytipp Tippspiel"
- [x] 1.7 Define {% block content %} for page content
- [x] 1.8 Add dark mode toggle script with localStorage persistence
- [x] 1.9 Set zinc-based color scheme as default
- [x] 1.10 Add system preference detection for initial dark mode state

## 2. Create Login Template

- [x] 2.1 Create templates/login.html extending base.html
- [x] 2.2 Add centered card layout with gradient background
- [x] 2.3 Add app title/logo area at top of card
- [x] 2.4 Style username input with zinc dark mode colors
- [x] 2.5 Style password input with zinc dark mode colors
- [x] 2.6 Add focus states with emerald accent ring
- [x] 2.7 Create submit button with emerald background
- [x] 2.8 Add hover/active states for button
- [x] 2.9 Display form.non_field_errors at top of form (invalid credentials)
- [x] 2.10 Display field-specific errors below each input
- [x] 2.11 Add aria attributes for accessibility
- [x] 2.12 Include CSRF token in form

## 3. Update Settings

- [x] 3.1 Add LOGIN_REDIRECT_URL = "/" to settings
- [x] 3.2 Add LOGOUT_REDIRECT_URL = "/login/" to settings
- [x] 3.3 Add LOGIN_URL = "/login/" to settings
- [x] 3.4 Verify TEMPLATES DIRS includes templates/ (already configured)

## 4. Write View Tests for Auth Flow

- [x] 4.1 Create tests/test_auth_views.py in tipapp/ or users/
- [x] 4.2 Write fixture: create_test_user (username, password)
- [x] 4.3 Test: GET /login/ returns 200 and uses login.html template
- [x] 4.4 Test: GET /login/ contains username and password inputs
- [x] 4.5 Test: GET /login/ contains CSRF token
- [x] 4.6 Test: POST /login/ with valid credentials redirects to LOGIN_REDIRECT_URL
- [x] 4.7 Test: POST /login/ with valid credentials authenticates user (user.is_authenticated)
- [x] 4.8 Test: POST /login/ with invalid credentials returns 200 (stays on login page)
- [x] 4.9 Test: POST /login/ with invalid credentials shows error message
- [x] 4.10 Test: POST /logout/ when authenticated redirects to LOGOUT_REDIRECT_URL
- [x] 4.11 Test: POST /logout/ when authenticated logs user out (not is_authenticated)
- [x] 4.12 Test: Base template contains dark mode toggle element
- [x] 4.13 Run pytest to verify all auth view tests pass

## 5. Manual Test Auth Flow

- [ ] 5.1 Start dev server and navigate to /login/
- [ ] 5.2 Verify login page renders with styling
- [ ] 5.3 Test login with valid credentials
- [ ] 5.4 Verify redirect to / after login
- [ ] 5.5 Test login with invalid credentials
- [ ] 5.6 Verify error message displays correctly
- [ ] 5.7 Test logout via /logout/ (POST)
- [ ] 5.8 Verify redirect to /login/ after logout
- [ ] 5.9 Test dark mode toggle persists across page reload
- [ ] 5.10 Test mobile responsiveness (resize browser)

## 6. Polish and Cleanup

- [x] 6.1 Add subtle transition animations to inputs/buttons
- [ ] 6.2 Add loading state to submit button (optional)
- [x] 6.3 Verify contrast ratios meet WCAG AA
- [x] 6.4 Test keyboard navigation (tab order)
- [x] 6.5 Run ruff check on any Python changes
- [ ] 6.6 Document view testing patterns in docs/testing.md (optional)
- [ ] 6.7 Commit changes with descriptive message
