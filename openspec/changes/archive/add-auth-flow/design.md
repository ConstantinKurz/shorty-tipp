## Context

Django project with custom User model (users.User) extending AbstractUser. Login/Logout URLs already configured in tipapp/urls.py using Django's built-in auth views. Templates directory configured in settings but empty. Tailwind CSS specified as frontend stack. Target aesthetic: modern fintech apps (Trade Republic, Scalable Capital, Revolut).

## Goals / Non-Goals

**Goals:**
- Create functional login page with Django auth
- Create base template for reuse across app
- Implement dark mode first design
- Mobile-first responsive layout
- Clean, minimal fintech aesthetic
- Setup Tailwind via CDN for development

**Non-Goals:**
- Registration flow (admin creates users for this private tipping game)
- Password reset via email (out of scope, can be added later)
- Social auth (Google, GitHub etc.)
- Remember me checkbox (Django sessions handle this)
- Custom authentication backend
- Production Tailwind build setup

## Decisions

### 1. Tailwind CSS via CDN

**Decision:** Use Tailwind CDN script in base template for now.

```html
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    darkMode: 'class',
    theme: { extend: { ... } }
  }
</script>
```

**Rationale:**
- Zero build setup required
- Instant development iteration
- Production build can be added later as separate change
- Acceptable for small user base (~50 tippers)

**Alternatives considered:**
- Django-Tailwind package: Rejected - adds build complexity
- Inline styles: Rejected - unmaintainable
- Bootstrap: Rejected - not fintech aesthetic

### 2. Dark Mode Implementation

**Decision:** Dark mode default with `class` strategy, toggle via JavaScript with localStorage persistence.

**Rationale:**
- Fintech apps favor dark mode
- `class` strategy allows explicit control
- localStorage persists preference across sessions
- Respects system preference as initial value

### 3. Template Structure

**Decision:** Flat template structure initially.

```
templates/
├── base.html          # Base layout with nav, footer, dark mode
├── login.html         # Login form
└── components/        # Future: reusable components
```

**Rationale:**
- Simple project, no need for deep nesting
- Can refactor later if complexity grows
- Django convention for small projects

### 4. Form Styling Approach

**Decision:** Style Django form fields directly in template, not via Django widget attrs.

```html
<input type="text" name="{{ form.username.name }}" 
       class="bg-zinc-800 border-zinc-700 ..." />
```

**Rationale:**
- Full Tailwind control in template
- No Python code changes for styling
- Easier to iterate on design
- Widget attrs become messy with many classes

**Alternatives considered:**
- django-crispy-forms: Rejected - adds dependency, less control
- Widget attrs in forms.py: Rejected - mixes concerns

### 5. Color Palette

**Decision:** Zinc-based neutral palette with accent color.

```
Background:  zinc-900 (dark), white (light)
Cards:       zinc-800 (dark), zinc-100 (light)
Borders:     zinc-700 (dark), zinc-200 (light)
Text:        zinc-100 (dark), zinc-900 (light)
Accent:      emerald-500 (success/primary actions)
Error:       red-500
```

**Rationale:**
- Zinc is modern, professional (used by Vercel, Linear)
- Emerald accent common in finance apps (green = money)
- High contrast for accessibility
- Works in both light and dark mode

### 6. Login Page Layout

**Decision:** Centered card on gradient background.

```
┌─────────────────────────────────────────────────┐
│                                                 │
│     ┌──────────────────────────────────┐        │
│     │         WM 2026 Tippspiel        │        │
│     │                                  │        │
│     │  ┌─────────────────────────────┐ │        │
│     │  │ Email / Username            │ │        │
│     │  └─────────────────────────────┘ │        │
│     │  ┌─────────────────────────────┐ │        │
│     │  │ Password                    │ │        │
│     │  └─────────────────────────────┘ │        │
│     │                                  │        │
│     │  ┌─────────────────────────────┐ │        │
│     │  │       Anmelden              │ │        │
│     │  └─────────────────────────────┘ │        │
│     │                                  │        │
│     └──────────────────────────────────┘        │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Rationale:**
- Standard pattern for auth pages
- Focused attention on single action
- Works well on mobile and desktop
- Professional appearance

### 7. Error Display

**Decision:** Inline field errors + top-level form errors.

**Rationale:**
- Immediate feedback per field
- Non-field errors (invalid credentials) shown prominently
- Accessible with aria attributes
- Red color consistent with error state

### 8. Redirect Settings

**Decision:** After login redirect to `/` (home), after logout redirect to `/login/`.

```python
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
LOGIN_URL = "/login/"
```

**Rationale:**
- Home page will show match list or dashboard
- Logout returns to login (security)
- LOGIN_URL needed for @login_required decorator

### 9. No Logout Confirmation Page

**Decision:** Direct logout via POST, redirect immediately.

**Rationale:**
- One less page to maintain
- Standard UX (most apps just log out)
- Django LogoutView handles POST automatically
- CSRF protection via Django middleware

### 10. View Testing Strategy

**Decision:** Write pytest view tests for authentication flow, establish testing patterns for templates.

**Test Coverage:**
- Login page rendering (GET)
- Login with valid credentials (POST → redirect)
- Login with invalid credentials (POST → error display)
- Logout functionality (POST → redirect)
- Template context variables
- Dark mode toggle presence in base template

**Rationale:**
- View tests verify template rendering and Django auth integration
- Prevents regressions in critical auth flow
- Documents expected behavior
- Establishes testing patterns for future templates
- Faster than manual testing
- No browser automation needed for basic template tests

**Testing Tools:**
- pytest-django for Django test client
- pytest fixtures for test users
- Django test client for GET/POST requests
- assertContains/assertTemplateUsed for response validation

**Alternatives considered:**
- Manual testing only: Rejected - error-prone, not repeatable
- E2E browser tests: Rejected - overkill for basic auth, slower
- Template unit tests: Rejected - view tests cover template integration better

## Risks / Trade-offs

**Risk:** Tailwind CDN adds external dependency
**Mitigation:** Small user base, fast CDN, can inline critical CSS later

**Risk:** Dark mode toggle adds JavaScript complexity
**Mitigation:** Minimal JS, localStorage is reliable, graceful fallback

**Trade-off:** No registration flow
**Acceptance:** Private game, admin creates accounts. Can add registration later if needed.

**Trade-off:** No password reset
**Acceptance:** Admin can reset passwords. Email-based reset is separate change.
