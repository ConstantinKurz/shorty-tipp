# Tasks: User Settings Page

## Task 1: Add theme_preference field to User model

### Goal
Extend the User model to store theme preference in the database.

### Scope
- Add `theme_preference` CharField to `users/models.py`
- Choices: `light`, `dark`, `system` (default: `system`)
- Create and run migration

### Out of Scope
- View changes
- Template changes
- Theme sync logic

### Acceptance Criteria
- [x] `theme_preference` field exists on User model
- [x] Field has correct choices and default value
- [x] Migration runs successfully
- [x] Existing users get default value `system`

### Required Tests
- Test that new users have `theme_preference='system'`
- Test that field accepts valid choices

---

## Task 2: Create UserSettingsForm

### Goal
Implement the form for editing user settings with validation.

### Scope
- Create `users/forms.py` with `UserSettingsForm`
- Fields: `username`, `email`, `predicted_champion`, `theme_preference`
- Username validation: max 20 chars, unique
- Email validation: unique (excluding current user)

### Out of Scope
- View implementation
- Template creation
- Champion deadline logic

### Acceptance Criteria
- [x] Form validates username max length (20 chars)
- [x] Form rejects duplicate usernames
- [x] Form rejects duplicate emails
- [x] Form allows empty `predicted_champion`
- [x] Form validates theme choices

### Required Tests
- Test form with valid data
- Test form rejects username > 20 chars
- Test form rejects duplicate username
- Test form rejects duplicate email
- Test form accepts all theme choices

---

## Task 3: Create UserSettingsView

### Goal
Implement the view to display and process the settings form.

### Scope
- Add `UserSettingsView` to `users/views.py`
- Use `UpdateView` with `LoginRequiredMixin`
- Add `can_change_champion()` logic
- Pass teams and champion lock status to template
- Show success message after save

### Out of Scope
- URL configuration
- Template creation
- Password reset

### Acceptance Criteria
- [x] View requires login
- [x] View returns current user's data
- [x] Context includes all teams for dropdown
- [x] Context includes `can_change_champion` flag
- [x] Champion flag is True before first match
- [x] Champion flag is False after first match kickoff
- [x] Successful save shows success message
- [x] Redirects back to settings page after save

### Required Tests
- Test anonymous user redirected to login
- Test authenticated user can access view
- Test context contains teams
- Test champion lock before/after first match
- Test form submission updates user

---

## Task 4: Create settings page template

### Goal
Build the user settings page UI with all sections.

### Scope
- Create `templates/users/settings.html`
- Profile section: username, email fields
- Champion section: team dropdown or locked display
- Theme section: radio buttons
- Success/error message display
- Submit button
- Responsive design with Tailwind

### Out of Scope
- Password reset
- Navigation link
- Theme sync JavaScript

### Acceptance Criteria
- [x] Template extends `base.html`
- [x] All form fields rendered with proper styling
- [x] Form errors display below fields
- [x] Success messages display at top
- [x] Champion dropdown disabled/hidden when locked
- [x] Theme radios properly grouped
- [x] Responsive on mobile
- [x] Dark mode support

### Required Tests
- Visual test on desktop and mobile
- Test form error display
- Test locked champion display

---

## Task 5: Configure URL routing for settings

### Goal
Wire up the settings view to a URL.

### Scope
- Create `users/urls.py` if not exists
- Add settings path
- Include users URLs in main `tipapp/urls.py`
- Add settings link to navigation header

### Out of Scope
- Password reset URLs
- View logic

### Acceptance Criteria
- [x] `/settings/` URL accessible
- [x] URL name is `users:settings`
- [x] Settings gear icon in navigation header
- [x] Link active state when on settings page

### Required Tests
- Test URL resolves to correct view
- Test reverse URL lookup works

---

## Task 6: Add theme sync JavaScript

### Goal
Sync server-saved theme preference with client-side state.

### Scope
- On settings page load, read server theme from template
- Update `localStorage` to match server preference
- Apply theme class to HTML element
- Handle "system" preference (use system setting)

### Out of Scope
- Form validation
- Password reset

### Acceptance Criteria
- [x] Changing theme in form and saving applies it immediately
- [x] Theme persists after page reload
- [x] "System" option respects OS preference
- [x] No flash of wrong theme on page load

### Required Tests
- Manual test: change theme, verify applied after save
- Manual test: verify system preference works

---

## Task 7: Add password reset URLs and views

### Goal
Enable password reset via Django's built-in auth views.

### Scope
- Add password reset URL patterns to `tipapp/urls.py`
- Use Django's `PasswordResetView`, `PasswordResetDoneView`, `PasswordResetConfirmView`, `PasswordResetCompleteView`
- Configure custom template names

### Out of Scope
- Template creation
- Email configuration
- Login page link

### Acceptance Criteria
- [x] `/password-reset/` shows email form
- [x] `/password-reset/done/` shows confirmation
- [x] `/password-reset-confirm/<uidb64>/<token>/` shows new password form
- [x] `/password-reset-complete/` shows success

### Required Tests
- Test all URLs resolve correctly
- Test view renders correct template

---

## Task 8: Create password reset templates

### Goal
Build the templates for the password reset flow.

### Scope
- `templates/registration/password_reset_form.html` - email input
- `templates/registration/password_reset_done.html` - email sent
- `templates/registration/password_reset_email.html` - email content
- `templates/registration/password_reset_subject.txt` - email subject
- `templates/registration/password_reset_confirm.html` - new password
- `templates/registration/password_reset_complete.html` - success
- All templates extend `base.html` (except email templates)
- German language

### Out of Scope
- Email backend configuration
- View logic

### Acceptance Criteria
- [x] All templates render correctly
- [x] Consistent styling with rest of app
- [x] German text throughout
- [x] Email template is plain text, clear instructions
- [x] Forms show validation errors
- [x] Dark mode support

### Required Tests
- Visual test of each step in flow
- Test email content is readable

---

## Task 9: Add password reset link to login page

### Goal
Add "Passwort vergessen?" link to the login page.

### Scope
- Update `templates/login.html`
- Add link below login form
- Style consistently with form

### Out of Scope
- Password reset logic
- Template creation

### Acceptance Criteria
- [x] Link visible below login form
- [x] Link navigates to `/password-reset/`
- [x] Styling matches login page design

### Required Tests
- Manual test: click link, verify navigation

---

## Task 10: Configure email backend for development

### Goal
Set up console email backend for local testing of password reset.

### Scope
- Add `EMAIL_BACKEND` setting for development
- Document production email configuration in `.env.example`

### Out of Scope
- Production email setup
- SMTP configuration

### Acceptance Criteria
- [x] Password reset emails appear in console
- [x] `.env.example` documents required email variables

### Required Tests
- Test password reset flow shows email in console

---

## Implementation Order

1. Task 1 (model field) - foundation
2. Task 2 (form) - validation logic
3. Task 3 (view) - business logic
4. Task 4 (template) - UI
5. Task 5 (URLs) - wire up
6. Task 6 (theme JS) - client sync
7. Task 7 (reset URLs) - password reset wiring
8. Task 8 (reset templates) - password reset UI
9. Task 9 (login link) - entry point
10. Task 10 (email config) - enable testing

## Estimated Effort

| Task | Effort |
|------|--------|
| Task 1 | ~15 min |
| Task 2 | ~30 min |
| Task 3 | ~30 min |
| Task 4 | ~45 min |
| Task 5 | ~15 min |
| Task 6 | ~20 min |
| Task 7 | ~15 min |
| Task 8 | ~45 min |
| Task 9 | ~10 min |
| Task 10 | ~10 min |
| **Total** | **~4 hours** |
