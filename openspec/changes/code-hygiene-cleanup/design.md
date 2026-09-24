# Code Hygiene Cleanup - Design

## Context

The repository passes `make test` (521 tests) and `ruff format --check .`, but `make lint` reports
8 violations and `make typecheck` runs with a configuration that contradicts the one the project
believes it uses. On top of that, the sweep found one fully dead 671-line module and 16 imports
placed inside functions or `try`/`except ImportError` blocks.

Measured baseline on `clean-up` before this change:

| Check | Command | Result |
| --- | --- | --- |
| Tests | `DJANGO_SETTINGS_MODULE=tipapp.settings.test python -m pytest -q` | 521 passed |
| Format | `ruff format --check .` | 144 files, 0 would change |
| Lint | `ruff check .` | 8 errors (5 F841, 2 DJ001, 1 B905) |
| Types | `mypy .` | 17 errors in 6 files, 4 `[annotation-unchecked]` notes |

Relevant facts established by reading the code rather than assuming:

- **The import graph does not force late imports.** `matches/models.py`, `users/models.py`,
  `predictions/models.py` and `scoring/models.py` import nothing from `scoring`, `notifications`
  or `predictions`. `scoring/ranking_service.py:15` and the now-dead `scoring/services.py:18`
  already import `users.models` at module level and load fine. Therefore the late imports in
  `scoring/champion_scoring.py`, `scoring/match_scoring.py`, `scoring/ranking_service.py`,
  `notifications/services.py`, `scoring/exports.py` and `users/signals.py` are not
  circular-import workarounds and can be hoisted.
- **`scoring/services.py` has no importer.** `grep -rn "scoring.services\|scoring import services"`
  over all `.py`, `.html`, `.toml` and `.cfg` files returns only a prose mention in
  `core/ranking.py:5`. `scoring/__init__.py` is empty, so there is no re-export either.
  `scoring/signals.py`, `scoring/admin.py`, `scoring/views.py`, `tipapp/views.py`, `users/views.py`,
  `users/signals.py` and every management command import from `match_scoring`, `champion_scoring`
  or `ranking_service`.
- **`mypy.ini` wins over `pyproject.toml`.** mypy reads `mypy.ini` first when both exist in the
  working directory. The `[tool.mypy] strict = true` block in `pyproject.toml` is therefore inert,
  which is why mypy emits `[annotation-unchecked]` notes for untyped function bodies.
- **`reportlab` is undeclared.** It appears in `scoring/exports.py` and
  `scoring/management/commands/export_leaderboard.py` but in no dependency list. The two modules
  contain two separate implementations of the same PDF table build.

## Goals / Non-Goals

**Goals**

- Every import in production code sits at module top level, except `if TYPE_CHECKING:` blocks.
- No `try`/`except ImportError` remains in production code.
- Scoring, champion-bonus and ranking logic exists exactly once.
- Every third-party import is declared in `pyproject.toml`.
- Exception handlers name the exception types they handle; loop-continue handlers report failures
  to the caller.
- One authoritative static-analysis configuration; `make check` is green at the end.
- The 521 existing tests keep passing unchanged, with no test edited to accommodate a behaviour
  change.

**Non-Goals**

- Changing scoring results, ranking order, lock times, joker limits or any other game behaviour.
- Reaching full `strict = true` mypy compliance in this change. The goal is one honest
  configuration with explicit, documented relaxations — not zero relaxations.
- Eliminating the 38 `# type: ignore` comments that stem from `django-stubs` limitations.
- Rewriting `predictions/views.py` class hierarchies. Only pure, side-effect-free helpers move.

## Decisions

### 1. Delete `scoring/services.py` rather than merging it

The module duplicates `match_scoring.py`, `champion_scoring.py` and `ranking_service.py` line for
line, but is the version *not* wired into `scoring/signals.py`. Keeping it as a backward-compatible
re-export shim would preserve exactly the ambiguity this change removes, and the shim would have no
consumer.

**Chosen:** delete the file outright, in its own commit, so the deletion can be reverted in
isolation if an unknown consumer appears.

**Verification before deletion** (must all be empty, excluding `openspec/changes/archive/`):

```bash
grep -rn "scoring\.services" --include='*.py' --include='*.html' --include='*.toml' .
grep -rn "from scoring import" --include='*.py' .
```

**Rejected:** merging `services.py` into `match_scoring.py`. The two implementations are
equivalent, so a merge produces no new information while risking that the unused variant's
behaviour leaks into the live path.

**Side effect:** removes the mypy errors at `scoring/services.py:542-544` and the five
`# noqa: F811` suppressions, which exist only in this file.

### 2. Hoist imports to module level; `if TYPE_CHECKING:` stays

Classification of the 28 non-top-level imports found:

| Category | Locations | Action |
| --- | --- | --- |
| `if TYPE_CHECKING:` type-only | `predictions/views.py:31`, `predictions/services.py:11-12`, `scoring/champion_scoring.py:14`, `scoring/match_scoring.py:16-17`, `notifications/services.py:15-16` | Keep |
| Empty `TYPE_CHECKING` block | `scoring/exports.py:14` | Delete block |
| Runtime model import in function | `notifications/services.py:37-39,118-120`, `scoring/exports.py:175-176`, `scoring/ranking_service.py:230`, `scoring/champion_scoring.py:55,103`, `scoring/match_scoring.py:281,327`, `scoring/management/commands/repair_scoring.py:32`, `users/signals.py:52`, `predictions/management/commands/create_wm2026_testdata.py:538` | Hoist to module level |
| Optional-dependency `try`-import | `scoring/exports.py:61-72`, `scoring/management/commands/export_leaderboard.py:78-91` | See decision 3 |
| Bootstrap `try`-import | `manage.py:12-17` (`dotenv`), `manage.py:21-27` (Django) | See decision 4 |
| Django app-ready signal import | `scoring/apps.py:10`, `users/apps.py:10` (`# noqa: F401`) | Keep — required by Django's app registry |
| Settings star-import | `tipapp/settings/*.py` (`# noqa: F403, F401`) | Keep — standard Django settings layering |
| Dead-module imports | `scoring/services.py:295-647` | Removed with the file |
| Script-local imports | `scripts/verify_scoring.py:196,219,245,247`, `conftest.py:16,34,52` | Hoist where possible; `conftest.py` fixtures may keep `get_user_model()` calls inside the fixture body |

If hoisting an import does raise `ImportError` at startup, the fix is to move the *consumer* (for
example a signal handler) rather than to restore the late import. Each hoist is verified with
`python manage.py check` plus the full test suite.

`scoring/apps.py` and `users/apps.py` keep their in-method signal imports: Django requires signal
registration inside `AppConfig.ready()`, and moving them to module level breaks app loading. This
is the one documented exception and it is recorded as a `per-file-ignores` entry for `PLC0415`.

### 3. Make `reportlab` an explicit optional extra with a single implementation

```toml
[project.optional-dependencies]
pdf = ["reportlab>=4.0"]
```

`scoring/exports.py` imports `reportlab` at module top level. The module is only imported by
`scoring/admin.py`, `scoring/views.py`, `scripts/verify_scoring.py` and
`export_leaderboard.py` — all of which are already opt-in paths — so a top-level import does not
affect the request path of the rest of the app.

`export_leaderboard.py` drops its own 60-line PDF builder and calls
`generate_leaderboard_pdf(leaderboard, title=...)`. That removes the second copy of the table
layout and the second `try`/`except ImportError`.

`make install` becomes `uv pip install -e ".[dev,pdf]"` so the existing developer workflow and CI
keep the PDF tests runnable.

**Rejected:** keeping the lazy import and adding `reportlab` to the required dependencies. That
leaves a `try`/`except ImportError` in the code for a dependency that is always installed, which is
exactly the pattern being removed.

### 4. `manage.py` imports `dotenv` unconditionally

`python-dotenv>=1.0` is a required dependency. The current `except ImportError: pass` turns a
broken environment into a silently misconfigured one. The Django `try`/`except ImportError` block
at `manage.py:21-27` is Django's own generated boilerplate whose purpose is a human-readable error
message, not optional behaviour — it stays.

### 5. Narrow exception handling, and make skipped items visible

Handler-by-handler decision:

| Location | Today | After |
| --- | --- | --- |
| `matches/services.py:154` | `except Exception:` → log, continue loop | Catch `(ValueError, TypeError, KeyError, DjangoValidationError, DatabaseError)`; append the match to a `failed` list on the returned result object |
| `scoring/management/commands/repair_scoring.py:82` | `except Exception as exc:  # noqa: BLE001` | Same narrowing; count failures and `raise CommandError` at the end if any occurred |
| `matches/management/commands/sync_teams.py:40` | `except Exception as e:` → log, re-raise | Re-raise as `CommandError` with context; drop the blanket catch |
| `matches/management/commands/update_matches.py:100` | `except Exception as e:` in daemon loop | Keep broad catch — a supervisor loop must not die — but add `# noqa: BLE001` with a one-line reason and log `exc_info=True` |
| `notifications/management/commands/notification_daemon.py:112` | same daemon pattern | Same as above |
| `notifications/services.py:105,203` | `except Exception as e:` → `(False, msg)` | Catch `(SMTPException, OSError, TemplateDoesNotExist)`; e-mail failure must not break scoring |
| `predictions/management/commands/create_wm2026_testdata.py:171` | `except Exception as e:` → re-raise | Replace with `CommandError` |
| `scoring/management/commands/create_snapshot.py:30` | `except Exception as e:` → re-raise | Replace with `CommandError` |
| `scoring/signals.py:61` | `except Exception:` → log, re-raise | Keep. `fix-prediction-correctness-bugs` deliberately made this re-raise; narrowing it here would fight that change. Add `# noqa: BLE001` with the reason |
| `scripts/verify_scoring.py:236` | `except Exception as e:` | Keep — standalone diagnostic script, not production code |

The two surviving broad handlers (`update_matches`, `notification_daemon`) are long-running
supervisor loops where dying on an unexpected error is the worse outcome. They are marked
explicitly so the `BLE001` rule can be enabled globally.

### 6. One mypy configuration, in `pyproject.toml`

`mypy.ini` is deleted. `[tool.mypy]` keeps `strict = true` and gains explicit per-module
relaxations that replace the previous global opt-out:

```toml
[[tool.mypy.overrides]]
module = ["*.migrations.*", "manage", "scripts.*"]
ignore_errors = true

[[tool.mypy.overrides]]
module = "*.tests.*"
disallow_untyped_defs = false
```

Test modules account for 5 of the 17 current errors (`_MonkeyPatchedWSGIResponse.url`,
`view_class`) — pytest-django's stubs, not project code.

**Staging matters.** Removing `mypy.ini` switches on `disallow_untyped_defs`,
`disallow_any_generics` and `check_untyped_defs` across the whole project, so the error count will
rise sharply before it falls. Task 5 therefore proceeds in one file at a time and must end with
`make typecheck` green. If a module cannot be made strict-clean within the task's scope, it gets
its own documented `[[tool.mypy.overrides]]` entry with a comment naming the blocker, instead of a
scattering of `# type: ignore` comments.

**Rejected:** deleting `[tool.mypy]` from `pyproject.toml` and keeping `mypy.ini`. `pyproject.toml`
already holds ruff, pytest, coverage and django-stubs configuration; a single file is the
consistent choice.

### 7. Extend the ruff rule set so the cleanup is enforced, not just performed

Added to `[tool.ruff.lint] select`:

| Rule | Catches |
| --- | --- |
| `PLC0415` | `import` outside top level — the rule that makes this cleanup permanent |
| `BLE001` | blind `except Exception` |
| `TID` | relative/banned imports |
| `RUF` | Django- and Python-specific ruff checks |

The 8 existing violations are fixed rather than ignored:
`matches/models.py:26,103` (DJ001) get `blank=True, default=""` instead of `null=True`, which
requires a migration — the field currently permits both `NULL` and `""` for the same "no value"
state. If any row already stores `NULL`, the migration backfills `""` first.
`scoring/tests/test_ranking_service.py:358` gets `strict=False` (preserving current behaviour)
or `strict=True` if the sequences are known to be equal length. The 5 F841 findings are unused
locals in tests and are simply removed.

`per-file-ignores` entries are added only for the documented exceptions:
`scoring/apps.py` and `users/apps.py` (`PLC0415`), `tipapp/settings/*.py` (`F403`, `F405`),
`scripts/verify_scoring.py` (`BLE001`, `T201`).

### 8. Move pure helpers out of `predictions/views.py`

`predictions/views.py` is 927 lines. Three module-level functions are pure and testable in
isolation:

| Function | Lines | Destination |
| --- | --- | --- |
| `get_polling_interval()` | ~22 | `predictions/services.py` |
| `get_phase_stats()` | ~50 | `predictions/services.py` |
| `build_match_predictions_list()` | ~139 | `predictions/services.py` |

The constants `POLLING_INTERVAL_ACTIVE`, `POLLING_INTERVAL_IDLE` and
`MATCH_ACTIVE_WINDOW_MINUTES` move with `get_polling_interval()`.

This is a pure move: function bodies, signatures and return shapes are unchanged, imports are
updated, and no template or URL changes. Any existing test that imports these from
`predictions.views` is updated to import from `predictions.services`. The move is verified by the
unchanged assertions of the existing view tests.

Deliberately **not** moved: `get_context_data()` overrides. Splitting those is a behavioural
refactor with real regression risk and belongs in its own change.

## Risks / Trade-offs

- **Hoisting an import introduces a circular import at startup.** Mitigated by hoisting one module
  per step and running `python manage.py check` plus the full suite after each. The import graph
  analysis above shows no model module depends on a service module, so the risk is low.
- **Deleting `scoring/services.py` breaks an unknown consumer.** Mitigated by the two grep checks
  in decision 1, by the full test suite, and by keeping the deletion in its own commit.
- **The DJ001 fix needs a migration on `matches.Match`.** `null=True` → `blank=True, default=""`
  changes the database column. The migration must backfill existing `NULL` values to `""` before
  altering the field, and code reading those fields must be checked for `is None` comparisons.
  If the backfill turns out to be risky on production data, the fallback is a `per-file-ignores`
  entry for DJ001 on `matches/models.py` with the reason recorded in
  [docs/project/decisions.md](../../../docs/project/decisions.md).
- **Enabling strict mypy surfaces many errors at once.** Mitigated by the staged approach in
  decision 6: per-module overrides with a named blocker are an acceptable outcome; leaving

  `make typecheck` red is not.
- **`reportlab` as a top-level import slows `scoring/exports.py` import.** Acceptable: the module
  is only reached from admin actions, the export view, the export command and a script.
- **Churn conflicts with `fix-prediction-correctness-bugs`.** That change touches
  `matches/services.py`, `matches/models.py`, `scoring/signals.py` and `predictions/views.py`.
  This change must be rebased onto it, and decision 5 explicitly preserves its re-raise semantics
  in `scoring/signals.py`.

## Migration Plan

One task per commit, in the order given in `tasks.md`. Dependency-critical ordering:

1. Task 1 (delete dead module) runs first — it removes 3 mypy errors and 5 `noqa`s that would
   otherwise have to be handled by tasks 3 and 5.
2. Task 2 (`reportlab` extra) runs before task 3, because hoisting the `scoring/exports.py`
   imports requires the dependency to be declared first.
3. Task 5 (mypy) and task 6 (ruff) run after tasks 1-4, so they lint the final code shape.
4. Task 7 (helper move) is the only task that touches `predictions/views.py`.
5. Task 8 records the outcome and is the final `make check` gate.

After every task: `make lint`, `make typecheck`, `make test`. A task is not done while any of the
three regresses against the baseline recorded in the Context table.

Rollback: every task is a self-contained commit that can be reverted individually. No task writes
data, and only task 6 creates a migration.

## Open Questions

- `matches/models.py:26,103` DJ001: do production rows currently hold `NULL` in those fields? If
  yes the backfill is mandatory; if the fields were added with a default, the migration is a plain
  `AlterField`. To be checked against the production database before task 6 is implemented.
- Should `scripts/verify_scoring.py` (66 `print()` calls, broad `except`) stay a script or become a
  management command? Out of scope here; raise as a follow-up change if the answer is "command".
