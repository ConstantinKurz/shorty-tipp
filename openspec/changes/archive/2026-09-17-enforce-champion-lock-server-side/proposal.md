# Proposal: Enforce Champion Pick Lock Server-Side

## Summary

Move the champion-pick lock from template rendering into server-side form logic so that
`predicted_champion` can neither be changed nor cleared once the first match has kicked off.

## Problem

**Current State:**

- `UserSettingsView.can_change_champion()` ([users/views.py](../../../users/views.py)) returns
  `timezone.now() < first_match.kickoff`, but the result is only put into the template context.
- `UserSettingsForm` ([users/forms.py](../../../users/forms.py)) lists `predicted_champion` in
  `Meta.fields` with `required=False` and performs no lock validation.
- The settings template hides the champion field after kickoff, but the form still binds it.

**Impact:**

1. **Authorization bypass.** A crafted POST to `/settings/` after the first kickoff changes the
   champion pick. The champion bonus is worth 20 points (odds category A) or 30 points
   (odds category B), so this directly manipulates the leaderboard.
2. **Silent data loss.** After kickoff the field is not rendered, so a normal "change theme" save
   posts no `predicted_champion` value. Because the field is `required=False`, the ModelForm writes
   `None` and wipes the user's existing pick without any error message.

This is Known Issue #3 in [docs/project/architecture.md](../../../docs/project/architecture.md) §15.

## Solution

Make the lock a property of the bound form, not of the rendered template.

### Key Changes

1. **`UserSettingsForm`**: accept a `champion_locked` keyword argument. When locked, remove
   `predicted_champion` from `self.fields` in `__init__`, so the field is neither bound, validated,
   nor written back to the instance by `construct_instance()`.
2. **`UserSettingsView`**: pass `champion_locked` into the form via `get_form_kwargs()`, derived from
   the same first-kickoff check that already drives `can_change_champion()`.
3. **`templates/users/settings.html`**: render the editable champion widget only when the form
   actually exposes the field; keep the read-only locked display otherwise.

### What Changes

| Aspect | Before | After |
|--------|--------|-------|
| Lock enforcement | Template `{% if can_change_champion %}` only | Form drops the field when locked |
| Crafted POST after kickoff | Overwrites `predicted_champion` | Ignored, pick unchanged |
| Saving theme after kickoff | Writes `None`, wipes pick | Pick preserved |
| Lock condition | `now < first_match.kickoff` (view only) | Same condition, shared by view and form |

## Benefits

- **Security**: Champion authorization no longer depends on what the template renders.
- **Data integrity**: An existing pick can never be cleared as a side effect of another settings save.
- **Consistency**: One lock condition (`now >= first match kickoff`) used for both rendering and validation.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Template references a removed bound field | Template renders the widget only when the field is present on the form |
| Silent ignore hides user intent | Locked state is already communicated in the UI by the read-only champion display |
| Regression in existing settings tests | Existing `users/tests/test_settings_view.py` and `test_forms.py` run unchanged in CI |

## Scope

### In Scope

- [users/forms.py](../../../users/forms.py)
- [users/views.py](../../../users/views.py)
- [templates/users/settings.html](../../../templates/users/settings.html)
- Tests for champion lock behaviour in `users/tests/`

### Out of Scope

- The 3-minute prediction lock buffer for match predictions
- Any other Known Issue from architecture §15
- Champion bonus scoring logic (`scoring/champion_scoring.py`)
- Changing the lock moment itself (stays at first match kickoff)
- Admin-side champion edits

## Success Criteria

1. A POST to `/settings/` with `predicted_champion` before the first kickoff still updates the pick.
2. A POST to `/settings/` with `predicted_champion` after the first kickoff leaves the stored pick unchanged.
3. Saving unrelated settings (e.g. `theme_preference`) after kickoff preserves the existing pick.
4. The lock condition is `now >= first match kickoff`, matching the existing helper; with no matches
   in the database, the champion remains editable.
5. Tests use a fixed reference time (patched `timezone.now`), not real wall-clock time.
6. Existing settings view and form tests continue to pass.
