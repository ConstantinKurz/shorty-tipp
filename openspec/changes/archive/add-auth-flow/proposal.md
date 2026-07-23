## Why

The Django project has Login/Logout URLs already configured but lacks the actual UI. Users cannot authenticate because no templates exist. This is a blocker for all user-facing features (predictions, leaderboard, profile).

The UI should follow modern fintech design principles (Trade Republic, Scalable Capital, Revolut style):
- Clean, minimal layouts
- Dark mode first with light mode support
- Professional typography
- Subtle animations
- Mobile-first responsive design

## What Changes

- Create base template with Tailwind CSS CDN (production will use build)
- Create login page with email/password form
- Create logout confirmation/redirect
- Add LOGIN_REDIRECT_URL and LOGOUT_REDIRECT_URL settings
- Style forms with modern fintech aesthetic
- **Write view tests for authentication flow**
- **Establish template testing patterns for future features**

## Capabilities

### New Capabilities
- `auth-templates`: Login and logout pages with modern fintech styling
- `base-template`: Reusable base template with Tailwind CSS and dark mode support

### Modified Capabilities
- None

## Impact

- New templates/ directory structure with base.html, login.html
- New test file: tests/test_auth_views.py with pytest view tests
- Settings update for redirect URLs
- Foundation for all future user-facing pages
- Template testing patterns documented
- No model changes
- No migrations
