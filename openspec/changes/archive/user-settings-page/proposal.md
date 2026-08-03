# Proposal: User Settings Page

## Summary

Create a dedicated user settings page where users can manage their profile information, set their World Cup champion prediction, and toggle dark/light mode. Additionally, add password reset functionality to the login page.

## Problem

Currently, users cannot:

- Change their email address
- Change their username
- Set or update their predicted World Cup champion
- Switch between dark and light mode
- Reset their password if forgotten

This limits user autonomy and makes account management difficult.

## Solution

### 1. User Settings Page (`/settings/`)

A dedicated page where logged-in users can:

- **Change email**: Update their email address with validation
- **Change username**: Update username (max 20 characters, unique check)
- **Set champion**: Select their predicted World Cup winner from available teams
- **Toggle theme**: Switch between dark and light mode (persisted in user preferences)

### 2. Password Reset Flow

On the login page:

- Add "Passwort vergessen?" link
- Use Django's built-in password reset via email
- Standard flow: request → email → reset link → new password → confirmation

## Non-Goals

- Social login integration
- Profile picture upload
- Two-factor authentication
- Account deletion
- Public profile pages

## Success Criteria

- Users can update their email and username with proper validation
- Username limited to 20 characters, must remain unique
- Champion selection shows all tournament teams
- Champion can only be set/changed before the first match
- Theme preference persists across sessions
- Password reset email arrives within 1 minute
- All forms show clear success/error feedback
