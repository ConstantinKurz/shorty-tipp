# Architectural Decisions

This document tracks major architectural and design decisions made during the development of the tipapp project.

## 2026-08-17: Code Structure Refactoring

**Context**: The original `scoring/services.py` file had grown to 700+ lines containing multiple service classes (`ScoringService` and `RankingService`) with different responsibilities. The codebase also had 10+ inline imports to work around circular dependency issues, and the `Match.save()` method directly imported and called `ScoringService`, creating tight coupling between the matches and scoring apps.

**Decision**: Refactor the code structure to improve separation of concerns and reduce coupling:

1. **Split services into focused modules**:
   - `scoring/match_scoring.py` - Match prediction scoring logic
   - `scoring/champion_scoring.py` - Champion prediction scoring logic
   - `scoring/ranking_service.py` - Leaderboard and ranking logic
   - `scoring/services.py` - Backward-compatibility facade

2. **Implement signal-based scoring**:
   - Created `matches/signals.py` with `match_result_entered` signal
   - Created `scoring/signals.py` with receivers for automatic scoring
   - Updated `Match.save()` to send signals instead of directly calling services
   - Registered signal receivers in `scoring/apps.py` ready() method

3. **Document remaining inline imports**:
   - TYPE_CHECKING imports for type hints (zero runtime cost)
   - Lazy imports in functions to avoid circular dependencies at runtime
   - All inline imports now have comments explaining why they're necessary

**Consequences**:

*Positive*:
- Better separation of concerns - each module has a single focus
- Decoupled architecture - matches app doesn't depend on scoring app
- Improved testability - can test signal receivers independently
- Better code navigation - easier to find specific functionality
- Consistent with Django patterns - uses signals like `users/signals.py`
- Backward compatible - existing imports continue to work via facade

*Negative*:
- Slightly more files to navigate (4 new files)
- Signal-based architecture adds indirection (but improves decoupling)
- Some inline imports still necessary for circular dependency avoidance

**Status**: Implemented

**Related Files**:
- `scoring/match_scoring.py`
- `scoring/champion_scoring.py`
- `scoring/ranking_service.py`
- `scoring/signals.py`
- `scoring/services.py` (facade)
- `matches/signals.py`
- `matches/models.py` (Match.save())
- `scoring/apps.py` (signal registration)

## 2026-08-24: Global Rank Caching

**Context**: Every leaderboard request was computing Olympic-style ranking via Python loop. With HTMX-heavy UI and concurrent users, this caused redundant calculations. During live matches with ~50 concurrent users, identical rank calculations were performed repeatedly for every leaderboard view.

**Decision**: Store computed `global_rank` on User model, updated via signal after match scoring.

**Implementation**:
- Added `global_rank` IntegerField to User model with database index
- Created `RankingService.update_all_user_ranks()` for bulk rank calculation
- Signal receiver calls `update_all_user_ranks()` after match scoring
- `get_current_leaderboard()` uses stored ranks when available, falls back to dynamic calculation
- Created `seed_global_ranks` management command for initial population and recovery

**Consequences**:

*Positive*:
- Leaderboard queries simplified to `ORDER BY global_rank`
- Single-column index scan vs. multi-column sort + Python loop
- Rank computed once per match result, read many times
- Atomic updates ensure consistency
- Backward compatible - fallback to dynamic calculation if ranks not populated

*Negative*:
- Ranks must be re-seeded if data is manually modified
- Additional field on User model
- Round-filtered rankings remain dynamic (acceptable trade-off)

*Mitigation*:
- Management command available for re-seeding
- Signal-based updates ensure ranks stay current
- Round-filtered views continue working as before

**Status**: Implemented

## 2026-09-24: Single mypy Configuration in `pyproject.toml`

**Context**: The project carried two type-checker configurations. `pyproject.toml` declared
`[tool.mypy] strict = true`, but a separate `mypy.ini` took precedence and set
`disallow_untyped_defs = False` plus `ignore_missing_imports = True`. Because `mypy.ini` won, the
`django-stubs` plugin configured in `pyproject.toml` was never loaded and `mypy .` reported
`[annotation-unchecked]` notes for function bodies it never checked.

**Decision**: Delete `mypy.ini` and keep one authoritative `[tool.mypy]` block in `pyproject.toml`
with `strict = true` plus explicit, commented per-module overrides instead of a global opt-out.

**Overrides and their blockers**:
- `*.migrations.*`, `manage`, `verify_scoring` → `ignore_errors`: generated code, entry point and
  standalone diagnostic script are not part of the typed application surface.
- `*.tests.*`, `conftest` → untyped/incomplete defs, generics, unreachable code and `attr-defined`
  relaxed: pytest and pytest-django provide no usable stubs for fixtures, for the monkey-patched
  test client response or for Django field introspection.
- `*.management.commands.*` → untyped defs relaxed: `BaseCommand.handle` and `add_arguments` are
  untyped in `django-stubs`.
- `*.models`, `*.forms`, `*.admin`, `*.views` → `disallow_any_generics` relaxed: `django-stubs`
  requires explicit generic parameters on `Field`, `ModelForm`, `ModelAdmin` and the generic views.
- `reportlab.*` → `ignore_missing_imports`: reportlab publishes no type stubs.

**Consequences**: `make typecheck` is green and honest about what it checks. Enabling the
`django-stubs` plugin made 22 existing `# type: ignore` comments unnecessary; they were removed,
bringing the total from 38 down to 16. Strict checking also surfaced a real bug in
`matches/management/commands/sync_teams.py`, which unpacked two values from the three-tuple
returned by `sync_teams_from_api()`.

**Status**: Implemented

## 2026-09-24: `reportlab` as a Named Optional Extra

**Context**: `scoring/exports.py` and `scoring/management/commands/export_leaderboard.py` each
imported `reportlab` inside a function guarded by `try`/`except ImportError`, and each contained
its own copy of the PDF table builder. `reportlab` was declared in neither
`[project.dependencies]` nor `[project.optional-dependencies]`, so PDF export was an undocumented,
unresolvable dependency.

**Decision**: Declare `pdf = ["reportlab>=4.0"]` under `[project.optional-dependencies]`, import
`reportlab` at the top of `scoring/exports.py`, and let `export_leaderboard.py` call
`generate_leaderboard_pdf()` instead of rebuilding the PDF. `make install` now runs
`uv pip install -e ".[dev,pdf]"`.

**Consequences**: The PDF layout exists exactly once. A missing dependency now fails loudly at
import time instead of silently at export time. Environments that want PDF export must install the
`pdf` extra.

**Status**: Implemented

## 2026-09-24: Ruff Rule Set Enforces Module-Level Imports and Narrow Excepts

**Context**: The cleanup hoisted 16 function-level imports to module level and narrowed nine
exception handlers. Without lint enforcement both classes of problem would return.

**Decision**: Add `PLC0415` (import not at top level), `BLE001` (blind `except Exception`), `TID`
and `RUF` to `[tool.ruff.lint] select`.

**Documented exceptions** (`per-file-ignores`): `scoring/apps.py` and `users/apps.py` (Django
requires signal imports inside `AppConfig.ready()`), `manage.py` (Django's generated entry point),
`**/migrations/*.py`, `**/tests/*.py` and `conftest.py` (function-level imports are idiomatic
there), and `scripts/verify_scoring.py` (standalone diagnostic script). `RUF012` is ignored
globally because Django declares `Meta` options, field choices and admin lists as plain class
lists; `RUF001`–`RUF003` are ignored because the German rule texts use typographic characters.

**Two remaining broad handlers**, both documented inline with a comment instead of a `noqa`
directive, because ruff does not flag handlers that re-raise:
`matches/management/commands/update_matches.py` and
`notifications/management/commands/notification_daemon.py` are supervisor loops that must not die
on an unexpected error, and `scoring/signals.py` logs the match id and re-raises.

**Status**: Implemented

## 2026-09-24: Empty String Instead of NULL on Two Character Fields

**Context**: `Team.odds_category` and `Match.winner` allowed both `NULL` and `""` for the same
"no value" state (ruff DJ001).

**Decision**: Replace `null=True` with `default="", blank=True` on both fields. Migration
`matches.0007` backfills existing `NULL` values to `""` before the `AlterField` operations.

**Consequences**: Code reading these fields uses falsy checks, which behave identically for `""`.
`matches/services.py` now writes `""` rather than `None` when the API reports no winner.

**Status**: Implemented
