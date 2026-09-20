# Fix Prediction Correctness Bugs

## Why

Three Priority-1 correctness bugs are documented in
[docs/project/architecture.md](../../../docs/project/architecture.md) §15 (issues #4, #5, #6).
All three silently produce wrong game results, which directly contradicts
[docs/rules/wm2026-rules.md](../../../docs/rules/wm2026-rules.md):

1. **Issue #4 — the group-stage limit is effectively 35, not 36.**
   `PredictionSaveView.post()` calls `MatchPrediction.objects.get_or_create()` *before*
   `PredictionLimitService.can_add_group_stage_prediction()`. The just-created row is already
   counted, so the legitimate 36th prediction evaluates `36 < 36 == False`, is rejected, and the
   freshly created row is deleted. Participants lose one of the 36 group-stage predictions the
   rules explicitly grant them (rules §"Each participant may predict only 36 group-stage
   matches"), and therefore up to 6 points of the 216 reachable group-stage points.

2. **Issue #5 — a winner/status-only change does not trigger scoring.**
   `Match.save()` only compares `goals_home`/`goals_away` before sending `match_result_entered`.
   A knockout match decided on penalties keeps its 1:1 full-time score while only `winner` and
   `status` change on a later import. Scoring and the champion bonus never run for that
   correction, so points and the champion bonus stay stale.

3. **Issue #6 — scoring errors are swallowed.**
   `score_predictions_on_result` wraps match scoring, champion bonus, and rank update in a single
   bare `except Exception: logger.exception(...)`. A partial failure leaves the match saved with
   missing points; because the next identical import detects no change, no new signal is sent and
   the system never self-heals. The damage is invisible outside the log file.

## What Changes

- `predictions/views.py`: check the group-stage limit **before** creating the prediction row, so
  exactly 36 group-stage predictions can be saved and the 37th is rejected.
- `matches/models.py`: compare all scoring-relevant fields (`goals_home`, `goals_away`, `winner`,
  `status`) in `Match.save()` and send `match_result_entered` when any of them changed, while
  saves that only touch unrelated fields still send nothing.
- `scoring/signals.py`: stop swallowing exceptions. Scoring, champion bonus and rank update run in
  one atomic block; failures are logged with match context and re-raised to the caller.
- `matches/services.py` / `matches/management/commands/update_matches.py`: isolate each match
  during sync so one failing match cannot abort the whole update loop.
- New management command `scoring/management/commands/repair_scoring.py` to detect and repair
  matches whose predictions were never scored, with a non-zero exit code in check mode.
- Tests for all three fixes and a documentation update in `docs/project/architecture.md` §15.

## Capabilities

### Changed Capabilities

- `group-stage-prediction-limit`: The limit is enforced against the count *excluding* the
  prediction being saved. 36 group-stage predictions are accepted; the 37th is rejected with the
  existing error partial.
- `match-result-scoring-trigger`: Scoring is triggered by any change to a scoring-relevant match
  field, not only by goal changes.
- `scoring-failure-handling`: Scoring failures are atomic, surfaced to the caller, detectable, and
  repairable via a management command instead of being silently logged.

## Impact

- No database schema changes, no migrations.
- Behavioural change for `Match.save()`: saves that change `winner` or `status` while goals are set
  now trigger scoring. Scoring is delta-based and idempotent, so re-scoring does not inflate
  points.
- Behavioural change for admins: a scoring failure now surfaces as an error instead of a silent
  success. The importer stays resilient — one bad match is logged and skipped, the loop continues.
- Affected files: `predictions/views.py`, `matches/models.py`, `matches/services.py`,
  `matches/management/commands/update_matches.py`, `scoring/signals.py`, plus new
  `scoring/management/commands/repair_scoring.py` and tests.

## Out of Scope

- Changing the scoring formula, round multipliers, or joker limits.
- Changing joker enforcement or the champion-pick lock (issue #3, already resolved).
- The remaining §15 issues (#1, #2, #7–#16), including HTMX polling and version-key changes.
- Introducing Celery, Redis, or any retry/queue infrastructure — recovery stays a management
  command per the project constraints.
- Adding a persistent scoring-state model or migration.
