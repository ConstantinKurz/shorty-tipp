# Proposal: Rules and How-To Page

## Summary

Create a comprehensive rules page that explains the World Cup tipping game rules and how to use the website. The page should present information in a user-friendly, simplified format with collapsible sections for better readability.

## Problem

Currently, users have no centralized place to:

- Understand how the game scoring works
- Learn about joker rules and round multipliers
- Understand the champion prediction bonus
- Learn how to navigate and use the website features
- Find answers to common questions about predictions, deadlines, and rankings

New users especially struggle to understand the complex scoring system without guidance. The full rules document (`docs/rules/wm2026-rules.md`) is technical and implementation-focused, not user-friendly.

## Solution

### Rules Page (`/rules/`)

A dedicated, accessible page that covers:

**1. Game Rules (Simplified)**
- Match prediction scoring (6-5-4-3-1-0 point system with examples)
- Round multipliers (group stage x1, knockout rounds x2-x3)
- Group stage limit (36 out of 72 matches)
- Joker system (double points, distribution by round)
- Champion prediction bonus (20-30 points based on odds)
- Ranking and tie-breaking rules

**2. How to Use the Website**
- Creating and editing predictions
- Setting jokers on predictions
- Choosing your champion in settings
- Viewing the ranking/leaderboard
- Seeing other users' predictions
- Understanding prediction deadlines and locks
- Navigating between tournament phases

**3. Interactive Features**
- Collapsible sections for each topic
- Visual examples with score calculations
- Quick links to relevant pages (predictions, settings, ranking)
- Mobile-friendly responsive design

## Non-Goals

- Full technical rules document (keep in `docs/`)
- Admin-specific documentation
- API documentation
- Advanced scoring edge cases (administratively removed matches, etc.)
- Real-time rule updates (static content, updated through code changes)
- Multi-language support (English only for now)

## Success Criteria

- All key game rules are explained in simplified, non-technical language
- Each scoring category includes at least one clear example
- Website navigation guide helps users find all main features
- Page is accessible from main navigation on all pages
- Sections can be collapsed/expanded for easier reading
- Page is fully responsive on mobile devices
- New users can understand how to participate without external help
- Dark mode support matches the rest of the site
