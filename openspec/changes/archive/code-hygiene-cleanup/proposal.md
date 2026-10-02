# Code Hygiene Cleanup

## Why

The codebase has accumulated structural debt that makes it harder to read, type-check and change
safely. A full sweep over the production packages (`core/`, `matches/`, `notifications/`,
`predictions/`, `scoring/`, `tipapp/`, `users/`, `scripts/`, `conftest.py`, `manage.py`) found the
following concrete problems:

1. **Imports are hidden inside functions and `try`/`except ImportError` blocks.**
   28 import statements outside module scope, of which only 12 are legitimate `if TYPE_CHECKING:`
   guards. The rest hide real dependencies:
   - `manage.py:12` wraps `from dotenv import load_dotenv` in `try: ... except ImportError: pass`,
     even though `python-dotenv>=1.0` is a hard dependency in `pyproject.toml`. If the package is
     ever genuinely missing, `.env` is silently ignored and the app starts with the wrong settings.
   - `scoring/exports.py:61-72` and `scoring/management/commands/export_leaderboard.py:78-91`
     both `try`-import `reportlab` and raise a hand-written `ImportError`. `reportlab` is declared
     in **neither** `[project.dependencies]` nor `[project.optional-dependencies]`, so PDF export
     is an undocumented, unresolvable dependency.
   - `notifications/services.py:37-39,118-120`, `scoring/exports.py:175-176`,
     `scoring/ranking_service.py:230`, `scoring/champion_scoring.py:55,103`,
     `scoring/match_scoring.py:281,327`, `scoring/management/commands/repair_scoring.py:32` and
     `users/signals.py:52` import models inside functions. The import graph shows this is
     unnecessary: no model module imports `scoring` or `notifications`, and
     `scoring/ranking_service.py` already imports `users.models` at module level.
   - `scoring/services.py:295-419` needs five `# noqa: F811` suppressions purely to silence the
     re-imports it creates for itself.

2. **`scoring/services.py` (671 lines) is dead code.** Nothing in the codebase imports it — the
   only remaining references are in archived OpenSpec documents. It duplicates
   `scoring/match_scoring.py`, `scoring/champion_scoring.py` and `scoring/ranking_service.py`
   verbatim (`_calculate_base_points`, `_check_exact_score`, `_get_tendency`,
   `_check_tendency_and_diff`, `ROUND_MULTIPLIERS`, `CHAMPION_POINTS`). It also produces 3 of the
   17 current mypy errors. Two copies of the scoring rules is a correctness hazard: a rule fix
   applied to one copy silently leaves the other wrong.

3. **Broad exception handling swallows failures.** 11 `except Exception` handlers in production
   code. Two are actively dangerous because they continue a loop after failure:
   `matches/services.py:154` skips a match during API sync, and
   `scoring/management/commands/repair_scoring.py:82` skips a match during repair — in both cases
   the failure only reaches the log file.

4. **Tooling is contradictory.** `pyproject.toml` sets `[tool.mypy] strict = true`, but the
   separate `mypy.ini` takes precedence and sets `disallow_untyped_defs = False` plus
   `ignore_missing_imports = True`. The project therefore believes it runs strict mypy while it
   does not — `mypy .` reports 4 `[annotation-unchecked]` notes for function bodies it never
   checked. `ruff check .` reports 8 outstanding violations (5 × F841, 2 × DJ001, 1 × B905).

5. **Leftovers.** `scoring/exports.py:14` contains an empty `if TYPE_CHECKING: pass` block,
   `scoring/migrations/0002_remove_weekly_snapshots.py:16` writes to stdout with `print()`, and
   `predictions/views.py` is 927 lines with pure helper logic (`get_polling_interval`,
   `get_phase_stats`, `build_match_predictions_list`) living in the view module instead of
   `predictions/services.py`, contradicting the documented architecture rule "keep business logic
   out of views".

## What Changes

- **Delete `scoring/services.py`.** The module is unreferenced; `scoring/match_scoring.py`,
  `scoring/champion_scoring.py` and `scoring/ranking_service.py` stay the single source of truth
  for scoring, champion bonus and ranking.
- **Move every non-`TYPE_CHECKING`, non-optional import to module level** in
  `notifications/services.py`, `scoring/exports.py`, `scoring/ranking_service.py`,
  `scoring/champion_scoring.py`, `scoring/match_scoring.py`,
  `scoring/management/commands/repair_scoring.py`, `users/signals.py` and
  `predictions/management/commands/create_wm2026_testdata.py`. Remove the five `# noqa: F811`
  suppressions together with the module that needed them.
- **Declare `reportlab` as an optional extra** (`[project.optional-dependencies] pdf`) and replace
  the two hand-written `try`/`except ImportError` blocks with a single top-level import in
  `scoring/exports.py`; `export_leaderboard.py` delegates to `generate_leaderboard_pdf()` instead
  of rebuilding the PDF.
- **Remove the `try`/`except ImportError` around `dotenv`** in `manage.py`; the dependency is
  declared and required.
- **Narrow exception handling**: every remaining handler catches the exception types it can
  actually recover from; loop-continue handlers record the failure in the command's result and
  cause a non-zero exit code instead of only logging.
- **Consolidate mypy configuration** into `pyproject.toml` and delete `mypy.ini`, with explicit,
  documented per-module relaxations instead of one global opt-out.
- **Fix the 8 outstanding ruff findings** and extend the enabled rule set so the class of problem
  this change removes (`PLC0415` deferred imports, `BLE001` blind except, `TID` banned imports)
  is caught by `make lint` from now on.
- **Move pure helpers out of `predictions/views.py`** into `predictions/services.py` without
  changing behaviour, and remove the empty `TYPE_CHECKING` block and the migration `print()`.

## Capabilities

### Changed Capabilities

- `code-structure`: Imports are declared at module level. Deferred imports are allowed only for
  `if TYPE_CHECKING:` blocks and are enforced by a lint rule. Scoring, champion-bonus and ranking
  logic exists exactly once.
- `dependency-declaration`: Every third-party import is declared in `pyproject.toml`, either as a
  required dependency or as a named optional extra. No dependency is discovered at runtime through
  `try`/`except ImportError`.
- `error-handling`: Production code catches specific exception types. Handlers that continue a
  loop report every skipped item and surface a non-zero exit code to the caller.
- `static-analysis`: `make check` runs one authoritative mypy configuration and a ruff rule set
  that rejects deferred imports and blind `except Exception`.

## Impact

- No database schema changes, no migrations, no user-visible behaviour change.
- `scoring/services.py` is deleted (671 lines). Any external code importing
  `scoring.services.ScoringService` must import `scoring.match_scoring.ScoringService` instead —
  no such caller exists in this repository.
- PDF export now requires `pip install -e ".[pdf]"`. `make install` is updated so the existing
  development setup keeps working unchanged.
- `mypy.ini` is deleted; `mypy .` will report a different (initially larger) error set until the
  per-module relaxations in `pyproject.toml` are in place. Task 6 must leave `make typecheck`
  green.
- Baseline to preserve: 521 passing tests, `ruff format --check .` clean.

## Out of Scope

- Changing any game rule, scoring formula, multiplier or ranking algorithm. This change is strictly
  behaviour-preserving with respect to [docs/rules/wm2026-rules.md](../../../docs/rules/wm2026-rules.md).
- The three correctness bugs tracked in `fix-prediction-correctness-bugs`.
- Removing or rewriting the 38 `# type: ignore` comments caused by `django-stubs` limitations.
- Restructuring templates, HTMX endpoints, URLs or the admin.
- Introducing new dependencies beyond declaring `reportlab`, which is already imported today.
- Performance optimisation and query tuning.
