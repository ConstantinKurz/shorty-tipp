# Design: Enforce Champion Pick Lock Server-Side

## Overview

The champion lock becomes a construction-time property of `UserSettingsForm`. The view computes the
lock state from the first match kickoff and passes it to the form. A locked form does not expose the
`predicted_champion` field at all, which makes both a crafted overwrite and an accidental wipe
impossible through the same mechanism.

---

## 1. Why field removal instead of field-level validation

Django's `ModelForm._post_clean()` calls `construct_instance(form, instance, opts.fields, opts.exclude)`,
which iterates over `self.instance._meta.fields` and skips any field **not present in `form.fields`**.

Consequences:

- Removing `predicted_champion` from `self.fields` means the value is never read from `request.POST`,
  never validated, and never written to the instance.
- This fixes both symptoms with one change:
  - a crafted `predicted_champion=<team_id>` POST is ignored;
  - a POST without `predicted_champion` (theme-only save) no longer writes `None`.

Alternatives considered:

| Option | Verdict |
|--------|---------|
| `clean_predicted_champion()` returning `self.instance.predicted_champion` when locked | Works, but still binds and coerces attacker-controlled input; two code paths (field + clean) must stay in sync |
| Raise `ValidationError` when locked and a value is posted | Rejects legitimate theme-only saves that browsers may still submit from a cached page; produces a confusing error for the normal user |
| `disabled=True` on the field | Keeps the field bound and rendered; `disabled` falls back to `self.initial`, which is correct, but the field would still appear in the rendered form and `Meta.fields` semantics stay implicit |

**Decision**: remove the field when locked. Ignore rather than reject, because the locked state is
already surfaced read-only in the UI and a legitimate settings save must not fail.

---

## 2. Form changes

### Location

[users/forms.py](../../../users/forms.py)

### Changes

```python
class UserSettingsForm(forms.ModelForm):
    """Form for editing user profile settings."""

    # ... existing field declarations unchanged ...

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

Notes:

- `champion_locked` is keyword-only and defaults to `False`, so existing direct instantiations in
  tests and any other call sites keep working unchanged.
- `self.champion_locked` is stored so the template and tests can assert the state without
  re-deriving it.
- `Meta.fields` keeps `predicted_champion`; the runtime `fields` dict is the authoritative source for
  `construct_instance()`.

---

## 3. View changes

### Location

[users/views.py](../../../users/views.py)

### Changes

```python
    def can_change_champion(self) -> bool:
        """Check if the champion prediction can still be changed.

        Returns:
            True if no matches exist or the first match has not kicked off yet.
        """
        first_match = Match.objects.order_by("kickoff").first()
        if not first_match:
            return True
        return timezone.now() < first_match.kickoff

    def get_form_kwargs(self) -> dict[str, Any]:
        """Pass the champion lock state into the form."""
        kwargs = super().get_form_kwargs()
        kwargs["champion_locked"] = not self.can_change_champion()
        return kwargs
```

- `can_change_champion()` keeps its current semantics and stays the single source of truth:
  editable while `timezone.now() < first_match.kickoff`, i.e. locked from `now >= kickoff`.
- `get_context_data()` keeps exposing `can_change_champion` for the template; it is now a display
  hint only, no longer the enforcement point.
- Both GET and POST go through `get_form_kwargs()`, so the lock applies to the bound form as well.

---

## 4. Template changes

### Location

[templates/users/settings.html](../../../templates/users/settings.html)

The "Weltmeister-Tipp" section currently branches on `can_change_champion`. It must branch on whether
the form actually exposes the field, so template and form can never disagree:

```django
{% if form.predicted_champion %}
    <!-- editable widget, unchanged markup -->
{% else %}
    <!-- read-only lock display, unchanged markup -->
{% endif %}
```

When the field has been removed, `form.predicted_champion` resolves to an empty value in the template
(the `KeyError` from `Form.__getitem__` is swallowed by template variable resolution), so the locked
branch renders. The read-only branch keeps using `user.predicted_champion` and renders no input
element, so nothing is submitted for that field.

---

## 5. Lock semantics

| Situation | `can_change_champion()` | `champion_locked` | `predicted_champion` on form |
|-----------|-------------------------|-------------------|------------------------------|
| No matches in DB | True | False | present, editable |
| `now < first kickoff` | True | False | present, editable |
| `now == first kickoff` | False | True | removed |
| `now > first kickoff` | False | True | removed |

"First match" is `Match.objects.order_by("kickoff").first()` — unchanged from the current helper.

---

## 6. Test strategy

### Location

`users/tests/test_settings_view.py` (view/integration) and `users/tests/test_forms.py` (form unit).

### Deterministic time

No `freezegun` dependency exists in the project and none is added. Tests pin time with
`unittest.mock.patch` on the `timezone.now` used by the view:

```python
REFERENCE_NOW = datetime(2026, 6, 11, 18, 0, tzinfo=dt_timezone.utc)
KICKOFF = datetime(2026, 6, 11, 20, 0, tzinfo=dt_timezone.utc)  # 2h after reference

with patch("users.views.timezone.now", return_value=REFERENCE_NOW):
    ...
```

Match `kickoff` values are absolute datetimes derived from these constants, never
`timezone.now() + timedelta(...)`, so results do not depend on wall-clock time.

### Cases

| Case | Setup | Expectation |
|------|-------|-------------|
| Change accepted before kickoff | kickoff after reference now | POST with new team → `user.predicted_champion == new team` |
| Change rejected after kickoff | kickoff at/before reference now | POST with different team → pick unchanged, response still 302 |
| Pick preserved on unrelated save | kickoff before reference now | POST with only username/email/theme → pick unchanged, theme updated |
| Form unit: locked | `UserSettingsForm(champion_locked=True)` | `"predicted_champion" not in form.fields` |
| Form unit: unlocked | `UserSettingsForm(champion_locked=False)` | `"predicted_champion" in form.fields` |

---

## 7. Security considerations

- Authorization is enforced on the server in form construction, independent of rendered HTML
  (OWASP A01 – Broken Access Control).
- Attacker-controlled `predicted_champion` input is not merely hidden, it is never read once locked.
- No new logging of user data is introduced.

## 8. Backward compatibility

- No model, migration or URL changes.
- `UserSettingsForm(...)` without `champion_locked` behaves exactly as today.
- `can_change_champion` remains in the template context, so no other template breaks.
