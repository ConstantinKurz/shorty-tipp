# Add Predictions View

## Summary

Implement a single-page predictions interface where users can view all matches with results, enter/edit predictions inline (auto-save), toggle jokers, and delete predictions. Server-side validation enforces joker limits per round and the 36 group-stage prediction limit.

## Problem

The `MatchPrediction` model exists with all required fields (user, match, predicted scores, joker, scoring fields), and the model tests are complete. However, there are no views, forms, URLs, or templates to allow users to interact with predictions through the web interface.

Currently missing:
- `predictions/views.py` is empty
- No `predictions/urls.py` exists
- No `predictions/forms.py` exists
- No prediction templates exist
- No routes in `tipapp/urls.py`

## Solution

Create a streamlined predictions interface with:

1. **Single List View** - All matches ordered by kickoff time, with results visible
2. **Inline Editing** - Auto-save when both goal fields filled (no save button)
3. **Auto-save Joker** - Joker toggle saves immediately on change
4. **Delete Function** - Trash icon to remove predictions
5. **Points Display** - Show earned points directly on each match
6. **Joker Indicator** - Visual indicator (⭐) when joker is active
7. **Server-side Limits** - Enforce joker limits per round and 36 group-stage limit

## Scope

### In Scope

- Predictions list view with all matches ordered by kickoff
- Match results visible (goals_home, goals_away if finished)
- Inline prediction input (auto-save via HTMX when both fields filled)
- Joker toggle with immediate save
- Delete prediction via trash icon
- Points display per prediction (if match finished)
- Joker indicator visible on predictions
- **Server-side joker limit enforcement per round** (configurable)
- **Server-side 36 group-stage prediction limit**
- Locktime validation (no changes after kickoff)
- HTMX for seamless UX without page reloads
- View tests and form tests

### Out of Scope

- Viewing other users' predictions (separate change)
- Prediction history/audit log
- Bulk prediction entry
- REST API endpoints

## Business Rules (from wm2026-rules.md)

### Joker Limits per Round
| Round | Max Jokers |
|-------|-----------|
| Group stage (gs) | 0 (no jokers allowed) |
| Round of 32 (r32) | 3 |
| Round of 16 (r16) | 3 |
| Quarter-final (qf) | 2 |
| Semi-final + Final + Third-place (sf, final, third) | 2 combined |

Note: Total joker count discrepancy (8 vs 10) - implement as configurable.

### Group Stage Limit
- Max 36 predictions for group stage matches
- User chooses which 36 to predict
- Predictions beyond limit are rejected

## Success Criteria

- [ ] Authenticated users see all matches ordered by kickoff time
- [ ] Match results (actual goals) visible for finished matches
- [ ] Auto-save prediction when both goal fields are filled
- [ ] Auto-save joker toggle immediately on change
- [ ] Delete prediction via trash icon
- [ ] Points earned visible on finished match predictions
- [ ] Joker indicator (⭐) shown when joker active
- [ ] Server rejects joker if round limit exceeded
- [ ] Server rejects group-stage prediction if 36 limit exceeded
- [ ] Server rejects changes after match kickoff
- [ ] All views require authentication
- [ ] Comprehensive test coverage for limits and locktime
