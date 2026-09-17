# Tasks: Enforce Champion Pick Lock Server-Side

## Task 1: Make `UserSettingsForm` Lock-Aware

**Priority**: HIGH
**Dependencies**: None

### Goal

Give `UserSettingsForm` a `champion_locked` keyword argument that removes `predicted_champion` from
the form's runtime fields, so a locked pick can be neither overwritten nor cleared.

### Scope

- [users/forms.py](../../../users/forms.py) — add `__init__` override

### Implementation

1. Import `Any` from `typing`.
2. Add to `UserSettingsForm`:

   ```python
   def __init__(self, *args: Any, champion_locked: bool = False, **kwargs: Any) -> None:
       """Initialize the form and drop the champion field when the pick is locked.

       Args:
           champion_locked: True once the first match has kicked off. When True the
               ``predicted_champion`` field is removed, so posted values are ignored and
               the stored pick is never overwritten.
       """
       super().__init__(*args, **kwargs)
       self.champion_locked = champion_locked
       if champion_locked:
           self.fields.pop("predicted_champion", None)
   ```

3. Leave `Meta.fields`, the declared field definitions, `clean_username()` and `clean_email()` unchanged.

### Out of Scope

- View wiring (Task 2)
- Template rendering (Task 3)
- Any change to `required=False` on the unlocked field

### Acceptance Criteria

- [x] `UserSettingsForm(champion_locked=True)` has no `predicted_champion` key in `form.fields`
- [x] `UserSettingsForm()` (default) still has `predicted_champion` in `form.fields`
- [x] A bound locked form with `predicted_champion` in the data is valid and does not change
      `instance.predicted_champion`
- [x] A bound locked form without `predicted_champion` in the data does not set it to `None`
- [x] `ruff` and `mypy` pass

### Tests Required

- `users/tests/test_forms.py`:
  - `test_champion_field_present_when_unlocked`
  - `test_champion_field_removed_when_locked`
  - `test_locked_form_ignores_posted_champion`
  - `test_locked_form_preserves_existing_champion`

---

## Task 2: Pass Lock State From View Into Form

**Priority**: HIGH
**Dependencies**: Task 1

### Goal

Derive `champion_locked` in `UserSettingsView` from the existing first-kickoff check and pass it to
the form for both GET and POST.

### Scope

- [users/views.py](../../../users/views.py) — add `get_form_kwargs()` override

### Implementation

1. Add to `UserSettingsView`:

   ```python
   def get_form_kwargs(self) -> dict[str, Any]:
       """Pass the champion lock state into the form."""
       kwargs = super().get_form_kwargs()
       kwargs["champion_locked"] = not self.can_change_champion()
       return kwargs
   ```

2. Keep `can_change_champion()` exactly as it is (`timezone.now() < first_match.kickoff`, `True` when
   no matches exist) — it is the single source of truth for the lock.
3. Keep `can_change_champion` in `get_context_data()`; it is now a display hint only.
4. Update the `UserSettingsView` docstring line about the champion field to state that the lock is
   enforced server-side.

### Out of Scope

- Changing the lock moment or the "no matches → editable" behaviour
- Adding a user-facing error message for locked POSTs (silently ignored by design)

### Acceptance Criteria

- [x] POST to `/settings/` with a different `predicted_champion` before the first kickoff updates the pick
- [x] POST to `/settings/` with a different `predicted_champion` at or after the first kickoff leaves the pick unchanged
- [x] The locked POST still succeeds (redirect to `users:settings`, success message shown)
- [x] With no matches in the database the champion is still editable
- [x] `ruff` and `mypy` pass

### Tests Required

- `users/tests/test_settings_view.py`:
  - `test_champion_change_accepted_before_first_kickoff`
  - `test_champion_change_rejected_after_first_kickoff`
  - `test_champion_editable_when_no_matches_exist`

---

## Task 3: Render Champion Field From Form State

**Priority**: MEDIUM
**Dependencies**: Task 2

### Goal

Make the settings template branch on whether the form exposes `predicted_champion`, so rendering can
never contradict the server-side lock.

### Scope

- [templates/users/settings.html](../../../templates/users/settings.html) — "Weltmeister-Tipp" section

### Implementation

1. Replace `{% if can_change_champion %}` with `{% if form.predicted_champion %}` in the
   "Weltmeister-Tipp" section.
2. Keep both branches' markup unchanged: editable branch renders the widget, errors and help text;
   locked branch renders the read-only `🔒` display based on `user.predicted_champion`.
3. Ensure the locked branch renders no input, select or hidden element for `predicted_champion`.

### Out of Scope

- Styling changes
- Any other section of the template
- Removing `can_change_champion` from the view context

### Acceptance Criteria

- [x] Before the first kickoff the page contains a `predicted_champion` select element
- [x] At or after the first kickoff the page contains no `predicted_champion` form control
- [x] The locked page still displays the stored champion name (or the "kein Tipp" text)
- [x] Theme and profile sections render unchanged

### Tests Required

- `users/tests/test_settings_view.py`:
  - `test_settings_page_renders_champion_field_before_kickoff`
  - `test_settings_page_hides_champion_field_after_kickoff`

---

## Task 4: Deterministic Champion Lock Tests

**Priority**: HIGH
**Dependencies**: Task 1, Task 2, Task 3

### Goal

Cover the lock behaviour with tests that use a fixed reference time instead of wall-clock time.

### Scope

- [users/tests/test_settings_view.py](../../../users/tests/test_settings_view.py)
- [users/tests/test_forms.py](../../../users/tests/test_forms.py)

### Implementation

1. Define module-level constants in the test module:

   ```python
   REFERENCE_NOW = datetime(2026, 6, 11, 18, 0, tzinfo=dt_timezone.utc)
   KICKOFF_BEFORE_NOW = datetime(2026, 6, 11, 16, 0, tzinfo=dt_timezone.utc)
   KICKOFF_AFTER_NOW = datetime(2026, 6, 11, 20, 0, tzinfo=dt_timezone.utc)
   ```

2. Create `Match` rows with these absolute datetimes — never `timezone.now() + timedelta(...)`.
3. Patch time with `unittest.mock.patch("users.views.timezone.now", return_value=REFERENCE_NOW)`
   around the request under test. Do not add a new test dependency such as `freezegun`.
4. Required test cases:
   - champion change accepted when kickoff is after the reference time;
   - champion change ignored when kickoff is at or before the reference time (assert the stored pick
     equals the original team);
   - champion preserved when POSTing only username, email and `theme_preference` after kickoff, and
     the theme actually changed (proves the save went through);
   - form unit tests for field presence/absence per `champion_locked`.
5. Each POST must include all required fields (`username`, `email`, `theme_preference`) so the form
   is valid; assert `response.status_code == 302` on success paths.
6. Re-check the values from the database with `user.refresh_from_db()`.

### Out of Scope

- Rewriting the existing wall-clock-based tests in `test_settings_view.py`
- Tests for prediction lock buffers or scoring

### Acceptance Criteria

- [x] New tests pass with `pytest users/tests/test_settings_view.py users/tests/test_forms.py`
- [x] No new test result depends on the real current date or time
- [x] No new package added to `pyproject.toml`
- [x] Full suite `pytest` passes

### Tests Required

- All test names listed in Tasks 1–3

---

## Task 5: Update Documentation

**Priority**: LOW
**Dependencies**: Task 1, Task 2, Task 3, Task 4

### Goal

Reflect the fixed behaviour in the architecture documentation.

### Scope

- [docs/project/architecture.md](../../../docs/project/architecture.md) — §8.6 and §15 issue #3

### Implementation

1. §8.6: state that `can_change_champion()` drives both the template and the `champion_locked` form
   kwarg, and that the form removes `predicted_champion` when locked.
2. §15: mark issue #3 as resolved (or remove it) and reference this change.

### Out of Scope

- Restructuring the document
- Other known issues

### Acceptance Criteria

- [x] §8.6 no longer claims there is no server-side validation
- [x] §15 issue #3 is marked resolved
- [x] No other documentation sections modified

### Tests Required

- None (documentation only)
