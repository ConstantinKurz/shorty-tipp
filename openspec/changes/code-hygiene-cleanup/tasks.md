# Code Hygiene Cleanup - Tasks

Eight independent tasks. Each is reviewable, testable and revertible on its own.
Implement **one task at a time** and commit it separately.

**Baseline that must never regress** (measured on `clean-up` before this change):

| Check | Command | Baseline |
| --- | --- | --- |
| Tests | `make test` | 521 passed |
| Format | `make format-check` | 144 files, 0 would change |
| Lint | `make lint` | 8 errors (5 F841, 2 DJ001, 1 B905) |
| Types | `make typecheck` | 17 errors in 6 files |

Run `make lint && make typecheck && make test` after every task.

**Order matters — implement 1 through 8 in sequence.** Task 1 removes code that tasks 3 and 5
would otherwise have to clean. Task 2 declares the `reportlab` dependency that task 3 hoists.
Tasks 5 and 6 lint the final code shape, so they run after tasks 1-4. Task 7 is the only task that
touches `predictions/views.py`.

---

## 1. Delete the dead `scoring/services.py` module

**Goal:** Scoring, champion-bonus and ranking logic exists exactly once, in
`scoring/match_scoring.py`, `scoring/champion_scoring.py` and `scoring/ranking_service.py`.

- [x] Confirm the module has no consumer:
      `grep -rn "scoring\.services\|from scoring import" --include='*.py' --include='*.html' --include='*.toml' --include='*.cfg' .`
      must return no hit outside `openspec/changes/archive/` and the prose mention in
      `core/ranking.py:5`
- [x] Confirm `scoring/__init__.py` is empty and re-exports nothing
- [x] Delete `scoring/services.py`
- [x] Update the prose reference in `core/ranking.py:5` to name `scoring/match_scoring.py` and
      `scoring/ranking_service.py` instead of "scoring services"
- [x] Update [docs/project/architecture.md](../../../docs/project/architecture.md) if it lists
      `scoring/services.py` as a live module (no reference present)
- [x] Verify `python manage.py check` and the full test suite still pass

**Scope:** `scoring/services.py`, the docstring in `core/ranking.py`, `docs/project/architecture.md`.

**Out of Scope:** Any change to `match_scoring.py`, `champion_scoring.py` or `ranking_service.py`.
No scoring value, multiplier or ranking rule may change.

**Acceptance Criteria:**
- `scoring/services.py` no longer exists
- `grep -rn "scoring\.services" --include='*.py' .` returns nothing
- `python manage.py check` exits 0
- `make test` still reports 521 passed, with no test file modified
- `make typecheck` reports 14 errors (17 minus the 3 from `scoring/services.py:542-544`)
- `ruff check .` reports the same 8 findings as the baseline

**Required Tests:** No new tests. The existing 521 tests are the regression guard — they already
cover `match_scoring`, `champion_scoring` and `ranking_service` and must pass unchanged.

---

## 2. Declare `reportlab` and remove the PDF `try`/`except ImportError`

**Goal:** PDF export has a declared dependency and one implementation, with no runtime import
probing.

- [x] Add `pdf = ["reportlab>=4.0"]` to `[project.optional-dependencies]` in `pyproject.toml`
- [x] Change `make install` to `uv pip install -e ".[dev,pdf]"`
- [x] In `scoring/exports.py`: move the `reportlab` imports from inside
      `generate_leaderboard_pdf()` (lines 61-72) to module top level and delete the
      `try`/`except ImportError` block and the hand-written error message
- [x] Remove the now-wrong `Raises: ImportError` line from the `generate_leaderboard_pdf` docstring
- [x] Delete the empty `if TYPE_CHECKING: pass` block at `scoring/exports.py:14`
- [x] Hoist the model imports at `scoring/exports.py:175-176` to module top level
- [x] In `scoring/management/commands/export_leaderboard.py`: delete the local `reportlab` imports
      and the duplicated PDF builder (lines 77-91 and the table-building block that follows) and
      call `generate_leaderboard_pdf(leaderboard, title=...)` instead
- [x] Keep the `# type: ignore` comments only where mypy still needs them after the hoist
- [x] Update `README.md` with the `[pdf]` extra if it documents the install command

**Scope:** `pyproject.toml`, `Makefile`, `scoring/exports.py`,
`scoring/management/commands/export_leaderboard.py`, `README.md`.

**Out of Scope:** The PDF layout, column set, fonts, page size or file name. The generated PDF
must be byte-comparable in structure to the current `scoring/exports.py` output.

**Acceptance Criteria:**
- `grep -n "except ImportError" scoring/exports.py scoring/management/commands/export_leaderboard.py`
  returns nothing
- `grep -c "reportlab" scoring/management/commands/export_leaderboard.py` returns 0
- Every `import` in `scoring/exports.py` is at module level
- `python -c "import scoring.exports"` succeeds in an environment installed with `[dev,pdf]`
- `python manage.py export_leaderboard --format=pdf` produces a non-empty PDF with the same
  columns and title as before
- CSV export is untouched and its tests pass unchanged

**Required Tests** (`scoring/tests/test_exports.py`, extend the existing file):
- `generate_leaderboard_pdf()` returns non-empty `bytes` starting with `%PDF`
- The management command with `--format=pdf` writes a file whose content equals
  `generate_leaderboard_pdf()` for the same leaderboard input
- The management command with `--format=csv` is unaffected

---

## 3. Hoist runtime imports to module level

**Goal:** No production module imports anything inside a function body, except `if TYPE_CHECKING:`
blocks and the two Django `AppConfig.ready()` signal registrations.

- [x] `notifications/services.py`: hoist `MatchPrediction`, `LeaderboardSnapshot`, `User`
      (lines 37-39) and `Match`, `MatchPrediction`, `User` (lines 118-120) to module level; keep
      the `if TYPE_CHECKING:` block only for names used purely in annotations, or delete it if the
      runtime import now covers them
- [x] `scoring/ranking_service.py`: hoist `MatchPrediction` (line 230)
- [x] `scoring/champion_scoring.py`: hoist `Match` (line 55) and `User` (line 103); drop the
      `as MatchModel` / `as UserModel` aliases if the `TYPE_CHECKING` block no longer conflicts
- [x] `scoring/match_scoring.py`: hoist `User` (line 281) and `MatchPrediction` (line 327)
- [x] `scoring/management/commands/repair_scoring.py`: hoist `MatchPrediction` (line 32)
- [x] `users/signals.py`: hoist `RankingService` (line 52); if this creates an import cycle, move
      the receiver registration instead of restoring the late import, and record the reason in
      [docs/project/decisions.md](../../../docs/project/decisions.md) (no cycle occurred)
- [x] `predictions/management/commands/create_wm2026_testdata.py`: hoist `ScoringService` (line 538)
- [x] `scripts/verify_scoring.py`: hoist the imports at lines 196, 219, 245, 247
- [x] `manage.py`: remove the `try`/`except ImportError: pass` around `from dotenv import load_dotenv`
      (lines 11-17); keep Django's own `try`/`except ImportError` boilerplate at lines 20-27
- [x] After each file, run `python manage.py check` to catch an import cycle immediately
- [x] Leave `scoring/apps.py:10` and `users/apps.py:10` unchanged — Django requires signal imports
      inside `ready()`

**Scope:** `notifications/services.py`, `scoring/ranking_service.py`, `scoring/champion_scoring.py`,
`scoring/match_scoring.py`, `scoring/management/commands/repair_scoring.py`, `users/signals.py`,
`predictions/management/commands/create_wm2026_testdata.py`, `scripts/verify_scoring.py`,
`manage.py`.

**Out of Scope:** `scoring/apps.py`, `users/apps.py`, `tipapp/settings/*.py` star-imports,
`conftest.py` fixture bodies, and any change to function logic. Imports move; nothing else does.

**Acceptance Criteria:**
- `grep -rn "^[[:space:]]\+\(from\|import\) " --include='*.py' core matches notifications predictions scoring users tipapp scripts manage.py | grep -v '/migrations/' | grep -v '/tests/'`
  returns only `if TYPE_CHECKING:` bodies, `scoring/apps.py`, `users/apps.py` and
  `tipapp/settings/__init__.py`
- No `# noqa: F811` remains anywhere in the repository
- `python manage.py check` exits 0
- `python manage.py runserver --noreload` starts without an `ImportError`
- `make test` reports 521 passed with no test file modified
- `make lint` reports no more findings than the baseline

**Required Tests:** No new behavioural tests. Add one guard test in `core/tests/test_imports.py`:
- Importing each of `notifications.services`, `scoring.match_scoring`, `scoring.champion_scoring`,
  `scoring.ranking_service`, `scoring.exports`, `users.signals` directly via `importlib` succeeds
  in isolation, proving no hidden import-order dependency was introduced

---

## 4. Narrow exception handling in services and one-shot commands

**Goal:** Every handler outside the two daemon loops names the exception types it can recover from.

- [x] `matches/services.py:154`: replace `except Exception:` with
      `except (ValueError, TypeError, KeyError, ValidationError, DatabaseError) as exc:`;
      keep logging with `exc_info=True` and continue the loop
- [x] `matches/management/commands/sync_teams.py:40`: raise `CommandError` with the original
      exception as `__cause__` instead of catching `Exception` and re-raising
- [x] `predictions/management/commands/create_wm2026_testdata.py:171`: same — `CommandError`
- [x] `scoring/management/commands/create_snapshot.py:30`: same — `CommandError`
- [x] `notifications/services.py:105` and `:203`: replace `except Exception as e:` with
      `except (SMTPException, OSError, TemplateDoesNotExist) as exc:`, keeping the
      `(False, message)` return shape so callers are unaffected
- [x] `scoring/management/commands/repair_scoring.py:82`: narrow the same way as
      `matches/services.py`, count failures, and raise `CommandError` at the end if
      `failed_count > 0`
- [x] `matches/management/commands/update_matches.py:100` and
      `notifications/management/commands/notification_daemon.py:112`: keep the broad catch (these
      are supervisor loops that must not die), but log with `exc_info=True` and add
      `# noqa: BLE001 - supervisor loop must survive unexpected errors`
- [x] `scoring/signals.py:61`: keep the broad catch-log-reraise introduced by
      `fix-prediction-correctness-bugs`; add `# noqa: BLE001 - re-raised, see scoring-failure-handling`
- [x] `scripts/verify_scoring.py:236`: leave unchanged (diagnostic script)

**Scope:** the nine files listed above.

**Out of Scope:** Retry logic, backoff strategy, new exception classes, alerting, and the daemon
sleep intervals. Failure *reporting* changes; failure *recovery* does not.

**Acceptance Criteria:**
- `grep -rn "except Exception" --include='*.py' core matches notifications predictions scoring users tipapp | grep -v '/tests/'`
  returns exactly three lines, each carrying a `# noqa: BLE001` comment with a reason
- No bare `except:` anywhere in production code
- `repair_scoring` exits non-zero when at least one match failed, and zero when none did
- `matches/services.py` still processes the remaining matches after one match fails
- `notifications/services.py` still returns `(False, message)` on an SMTP failure — no caller
  signature changes
- `make test` reports 521 passed plus the new tests below

**Required Tests:**
- `matches/tests/test_services.py`: one match raising `ValueError` during sync is recorded as
  failed while the other matches are still imported
- `scoring/tests/test_management_commands.py`: `repair_scoring` raises `CommandError` when a match
  fails, and exits cleanly when none do
- `notifications/tests/test_email_service.py`: an `SMTPException` from `send_mail` yields
  `(False, <message>)`; an unexpected `RuntimeError` now propagates instead of being swallowed
- `matches/tests/test_sync_teams_command.py`: an API error surfaces as `CommandError`

---

## 5. Consolidate mypy configuration into `pyproject.toml`

**Goal:** One authoritative mypy configuration, honest about what it checks, with `make typecheck`
green.

- [x] Delete `mypy.ini`
- [x] In `pyproject.toml` `[tool.mypy]`, keep `strict = true` and add the module overrides:
      `["*.migrations.*", "manage", "scripts.*"]` → `ignore_errors = true`;
      `"*.tests.*"` → `disallow_untyped_defs = false`
- [x] Run `mypy .` and fix the remaining errors file by file, starting with production code
- [x] `scoring/exports.py:222-224,242`: fix the `user_id` / `match_id` `[attr-defined]` errors by
      selecting the IDs explicitly (`.values_list("user_id", ...)`) or by annotating the queryset,
      not by adding `# type: ignore` (resolved by enabling the django-stubs plugin)
- [x] `users/signals.py:23-48`: fix the `_original_predicted_champion_id` errors by declaring the
      attribute on the model or by using a typed module-level `WeakKeyDictionary`, whichever is
      simpler
- [x] For any module that cannot be made strict-clean within this task, add a dedicated
      `[[tool.mypy.overrides]]` entry with a comment naming the blocker — do **not** scatter
      `# type: ignore` comments
- [x] Record the configuration consolidation in
      [docs/project/decisions.md](../../../docs/project/decisions.md)

**Scope:** `mypy.ini` (deleted), `pyproject.toml`, `scoring/exports.py`, `users/signals.py`, plus
any module needing a documented override.

**Out of Scope:** Removing the 38 pre-existing `# type: ignore` comments caused by `django-stubs`
limitations, upgrading `django-stubs`, and adding type hints to test helpers.

**Acceptance Criteria:**
- `mypy.ini` no longer exists
- `make typecheck` exits 0 with "Success: no issues found"
- `mypy .` emits no `[annotation-unchecked]` notes, proving `check_untyped_defs` is now active
- Every `[[tool.mypy.overrides]]` block has a comment explaining why it exists
- The total count of `# type: ignore` comments does not increase above the current 38
- `make test` reports 521 passed with no runtime behaviour changed

**Required Tests:** None. `make typecheck` is the acceptance gate. Any code change made to satisfy
mypy (for example the `users/signals.py` attribute handling) must be covered by the existing
`users/tests/test_champion_signal.py`, which must pass unchanged.

---

## 6. Fix the 8 ruff findings and enable the enforcing rule set

**Goal:** `make lint` is green and the rules that forbid deferred imports and blind excepts are
switched on.

- [x] Remove the 5 unused locals: `matches/tests/test_match_scoring.py:215` (`match`),
      `matches/tests/test_update_matches_command.py:146` (`mock_signal_receiver` — verify the mock
      is still connected before deleting the binding),
      `predictions/tests/test_views.py:1291` (`lines`),
      `scoring/tests/test_integration.py:548` (`user`),
      `users/tests/test_ranking_view.py:267` (`user`)
- [x] `scoring/tests/test_ranking_service.py:358`: add an explicit `strict=` argument to `zip()`
- [x] `matches/models.py:26,103`: replace `null=True` on the two string fields with
      `blank=True, default=""`; generate the migration and add a `RunPython` step that backfills
      existing `NULL` values to `""` before the `AlterField`
- [x] Search for `is None` / `isnull` checks against those two fields and switch them to falsy /
      `exact=""` checks
- [x] Add `PLC0415`, `BLE001`, `TID` and `RUF` to `[tool.ruff.lint] select` in `pyproject.toml`
- [x] Add `[tool.ruff.lint.per-file-ignores]` entries only for the documented exceptions:
      `scoring/apps.py` and `users/apps.py` → `PLC0415`; `tipapp/settings/*.py` → `F403`, `F405`;
      `scripts/verify_scoring.py` → `BLE001`, `T201` (settings keep their inline `noqa`; migrations,
      tests, `conftest.py` and `manage.py` also need `PLC0415`)
- [x] Run `ruff check .` and resolve everything the new rules surface, or justify each remaining
      `noqa` inline with a reason

**Scope:** `pyproject.toml`, the 6 test files with F841/B905, `matches/models.py`, one new
migration in `matches/migrations/`, plus call sites of the two changed fields.

**Out of Scope:** `ruff format` changes (the tree is already formatted), reordering imports beyond
what `I` requires, and any rule set beyond the four listed.

**Acceptance Criteria:**
- `make lint` exits 0
- `make format-check` still reports 0 files to reformat
- `select` contains `PLC0415`, `BLE001`, `TID` and `RUF`
- Adding a new function-level import anywhere outside the per-file-ignores list makes
  `ruff check .` fail — verified manually once
- The `matches` migration applies cleanly on a database containing `NULL` in both fields and leaves
  `""`
- `python manage.py makemigrations --check --dry-run` reports no missing migrations
- `make test` reports 521 passed

**Required Tests** (`matches/tests/test_models.py`):
- Both previously nullable string fields default to `""` on a newly created `Match`
- Code paths that previously branched on `None` for those fields behave identically with `""`
- A migration test (or an explicit assertion in the existing model tests) that no `Match` row can
  hold `NULL` in those fields

---

## 7. Move pure helpers from `predictions/views.py` into `predictions/services.py`

**Goal:** `predictions/views.py` orchestrates requests; the pure helper logic lives in the service
layer, as required by the documented architecture.

- [x] Move `get_polling_interval()` and the constants `POLLING_INTERVAL_ACTIVE`,
      `POLLING_INTERVAL_IDLE`, `MATCH_ACTIVE_WINDOW_MINUTES` from `predictions/views.py` to
      `predictions/services.py`
- [x] Move `get_phase_stats()` to `predictions/services.py`
- [x] Move `build_match_predictions_list()` to `predictions/services.py`
- [x] Keep function names, signatures, argument order and return shapes byte-identical — this is a
      move, not a refactor
- [x] Update the imports in `predictions/views.py` and in any test importing these names from
      `predictions.views`
- [x] Add or keep Google-style docstrings and full type hints on the three moved functions
- [x] Verify `predictions/views.py` no longer defines module-level business-logic helpers

**Scope:** `predictions/views.py`, `predictions/services.py`, `predictions/tests/test_views.py`,
`predictions/tests/test_services.py`.

**Out of Scope:** Splitting `get_context_data()` methods, changing query logic, changing the
polling interval values, template changes, URL changes, and any HTMX endpoint contract.

**Acceptance Criteria:**
- The three functions are defined in `predictions/services.py` and referenced from
  `predictions/views.py`
- `predictions/views.py` is at least 200 lines shorter
- The HTMX polling response returns the identical `polling_interval` value for the same match state
  as before the move
- The all-tips / match-predictions page renders the identical ordering and ranking as before
- `make test` reports 521 passed; the only test edits are import-path updates
- `make lint` and `make typecheck` stay green

**Required Tests** (`predictions/tests/test_services.py`):
- `get_polling_interval()` returns the active interval inside the match window and the idle
  interval outside it, using a frozen/injected time rather than the real clock
- `get_phase_stats()` returns the same counts as the existing view test asserts
- `build_match_predictions_list()` returns the same ordering, ranking and joker flags as the
  existing view test asserts

---

## 8. Remove remaining debug leftovers and record the outcome

**Goal:** No stdout debug output in migrations, and the architecture documentation reflects the new
module layout.

- [x] `scoring/migrations/0002_remove_weekly_snapshots.py:16`: replace `print(...)` with a
      `logging.getLogger(__name__).info(...)` call
- [x] Update [docs/project/architecture.md](../../../docs/project/architecture.md): remove any
      reference to `scoring/services.py`, and note that `predictions/services.py` now owns the
      three moved helpers
- [x] Add an entry to [docs/project/decisions.md](../../../docs/project/decisions.md) covering:
      the `reportlab` optional extra, the single mypy configuration, the `PLC0415`/`BLE001` rule
      set, and the two documented broad-except exceptions
- [x] Re-run the full baseline table from this file and record the new numbers in the change

**Final numbers after this change:**

| Check | Command | Before | After |
| --- | --- | --- | --- |
| Tests | `make test` | 521 passed | 539 passed |
| Format | `make format-check` | 144 files, 0 would change | 146 files, 0 would change |
| Lint | `make lint` | 8 errors | 0 errors |
| Types | `make typecheck` | 17 errors in 6 files | Success, no issues |
| `# type: ignore` | `grep -c` | 38 | 15 |

**Scope:** `scoring/migrations/0002_remove_weekly_snapshots.py`,
`docs/project/architecture.md`, `docs/project/decisions.md`.

**Out of Scope:** Rewriting migration logic, squashing migrations, converting
`scripts/verify_scoring.py` into a management command, and touching the 66 intentional `print()`
calls in that script.

**Acceptance Criteria:**
- `grep -rn "print(" --include='*.py' matches predictions scoring users notifications core tipapp | grep -v '/tests/'`
  returns nothing
- `python manage.py migrate` still applies `scoring.0002` without error on a fresh database
- `docs/project/architecture.md` contains no reference to `scoring/services.py`
- `docs/project/decisions.md` has a dated entry for each of the four decisions listed above
- Final state: `make check` exits 0 — lint, format-check, typecheck and 521+ tests all green

**Required Tests:** None. `make check` is the acceptance gate for this task.
