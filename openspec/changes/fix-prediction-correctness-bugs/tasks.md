# Fix Prediction Correctness Bugs - Tasks

Three independent tasks, one per issue in
[docs/project/architecture.md](../../../docs/project/architecture.md) §15.
Each task is reviewable, testable and revertible on its own. Implement one task at a time.

---

## 1. Group-stage limit accepts exactly 36 predictions (§15 issue #4)

**Goal:** A user can save 36 group-stage predictions; the 37th is rejected without creating a row.

- [x] Reorder `PredictionSaveView.post()` in `predictions/views.py`: look up the existing
      prediction with `MatchPrediction.objects.filter(user=user, match=match).first()` instead of
      `get_or_create()`
- [x] Run the limit check *before* creating a new group-stage prediction and return the existing
      `predictions/prediction_error.html` partial with status 400 when the limit is reached
- [x] Create the prediction only after the check passes, with the current defaults
      (`predicted_goals_home=0`, `predicted_goals_away=0`)
- [x] Wrap lookup, check and create in `transaction.atomic()`
- [x] Keep the invalid-form path correct: delete only rows this request created, otherwise
      `refresh_from_db()`
- [x] Mark issue #4 as resolved in `docs/project/architecture.md` §15

**Scope:** `predictions/views.py`, tests, architecture doc entry for issue #4.

**Out of Scope:** `PredictionLimitService` semantics, joker limits, lock-time behaviour, the error
partial's markup or wording, `PredictionDeleteView`.

**Acceptance Criteria:**
- Saving a group-stage prediction with 35 existing group-stage predictions succeeds and the stored
  count is 36
- Saving a group-stage prediction with 36 existing group-stage predictions returns status 400 with
  the "Limit erreicht" partial and the stored count stays 36
- A rejected request creates no `MatchPrediction` row (no create-then-delete)
- Editing one of the 36 existing predictions is never blocked by the limit
- Knockout-round predictions are unaffected by the group-stage limit
- `PredictionLimitService.can_add_group_stage_prediction()` keeps its current signature and
  semantics, and `predictions/tests/test_services.py` passes unchanged

**Required Tests** (`predictions/tests/test_views.py`):
- 36th group-stage prediction is accepted (status 200, count becomes 36)
- 37th group-stage prediction is rejected (status 400, count stays 36)
- Rejected request leaves the prediction count unchanged and creates no row
- Updating an existing group-stage prediction at the 36-prediction limit still succeeds
- A knockout prediction succeeds while 36 group-stage predictions exist

---

## 2. Winner/status changes trigger scoring (§15 issue #5)

**Goal:** A change to a scoring-relevant match field triggers `match_result_entered`; unrelated
saves do not.

- [x] Add `SCORING_RELEVANT_FIELDS = ("goals_home", "goals_away", "winner", "status")` to `Match`
      in `matches/models.py` with a short docstring/comment explaining why each field matters
- [x] Load the previous values with
      `Match.objects.filter(pk=self.pk).values(*SCORING_RELEVANT_FIELDS).first()`
- [x] Send `match_result_entered` when both goals are set and any tracked field changed, or when
      the row was newly created with both goals set
- [x] Do not send the signal when only untracked fields (`kickoff`, `round`, teams, `external_id`)
      changed
- [x] Update the `Match.save()` docstring to describe the new trigger condition
- [x] Mark issue #5 as resolved in `docs/project/architecture.md` §15

**Scope:** `matches/models.py`, tests, architecture doc entry for issue #5.

**Out of Scope:** the scoring formula, `scoring/signals.py` error handling (task 3),
`matches/services.py` field mapping, champion-bonus calculation rules.

**Acceptance Criteria:**
- Changing only `winner` on a match with both goals set sends `match_result_entered` exactly once
- Changing only `status` (e.g. `live` → `finished`) on a match with both goals set sends
  `match_result_entered` exactly once
- Changing `goals_home`/`goals_away` still sends the signal (existing behaviour preserved)
- Saving with no change to any tracked field sends nothing
- Saving a change to `kickoff` only sends nothing
- No signal is sent while `goals_home` or `goals_away` is `None`
- A penalty-shootout final that stays 1:1 and only gets `winner="away"` results in the champion
  bonus being awarded to the users who predicted the away team

**Required Tests** (`matches/tests/test_models.py`, champion path in `scoring/tests/test_champion_scoring.py`
or `scoring/tests/test_integration.py`):
- Signal fires on `winner`-only change
- Signal fires on `status`-only change
- Signal fires on goal change (regression guard)
- Signal does not fire on `kickoff`-only change
- Signal does not fire on a no-op save
- Signal does not fire while goals are `None`
- Service-level: a 1:1 final updated with `winner="away"` triggers scoring and awards the champion
  bonus for the away team

---

## 3. Scoring failures are visible and recoverable (§15 issue #6)

**Goal:** A scoring failure is atomic, surfaced to the caller, detectable from the data, and
repairable via a management command — while the importer keeps running.

- [x] In `scoring/signals.py`, wrap scoring, champion bonus and rank update in a single
      `transaction.atomic()` block
- [x] Log the failure with match identification (`match`, `match.pk`) and re-raise instead of
      swallowing the exception
- [x] In `matches/services.py`, wrap the per-match `_sync_match()` call in `sync_matches_from_api()`
      in `try/except Exception`, log with the external match id, count failures, and continue the
      loop; keep the `list[MatchSyncResult]` return type
- [x] Include the failure count in the existing sync summary log line
- [x] Add `scoring/management/commands/repair_scoring.py` that finds matches with both goals set
      and at least one prediction with `points_earned IS NULL`
- [x] Support `--check` (detect only, no writes) and default repair mode; exit non-zero when work
      remains or a repair failed
- [x] Repair re-runs `ScoringService.score_all_predictions_for_match()` per match, then
      `update_live_champion_bonuses()` when a final is affected, then
      `RankingService.update_all_user_ranks()` once
- [x] Continue repairing remaining matches when one match fails, and report the failures
- [x] Document the command in `docs/project/architecture.md` §15 (issue #6 resolution) and in the
      operations/commands section of `README.md` if commands are listed there

**Scope:** `scoring/signals.py`, `matches/services.py`,
`scoring/management/commands/repair_scoring.py`, tests, docs.

**Out of Scope:** the scoring formula, a persistent scoring-state model or migration, retry/queue
infrastructure, `recalculate_scores` behaviour, the loop-level error handling in
`update_matches.py` (stays as-is).

**Acceptance Criteria:**
- A scoring failure raised inside the receiver propagates to the caller of `Match.save()` and is
  logged with the match id
- A failure leaves no partially scored state: predictions, champion bonus and ranks are rolled back
  together
- One failing match in `sync_matches_from_api()` does not prevent the remaining matches from being
  synced, and `update_matches --once` still completes
- `repair_scoring --check` lists affected matches, writes nothing, and exits non-zero when at least
  one match needs repair
- `repair_scoring --check` exits zero on a healthy database
- `repair_scoring` scores the previously unscored predictions and exits zero afterwards
- Running `repair_scoring` twice in a row does not change any points the second time (idempotent)
- Matches without any predictions are not reported as needing repair

**Required Tests** (`scoring/tests/test_integration.py`, `scoring/tests/test_management_commands.py`,
`matches/tests/test_services.py`):
- Receiver raises (not swallows) when `ScoringService.score_all_predictions_for_match` fails
- Failed scoring leaves predictions unscored and user totals unchanged (no partial write)
- `sync_matches_from_api()` continues after one match raises and still returns results for the
  healthy matches
- `repair_scoring --check` detects a match with goals and `points_earned=None` predictions and
  exits non-zero
- `repair_scoring` repairs that match, sets `points_earned`, and updates user totals and ranks
- `repair_scoring` is idempotent on an already healthy database (no point changes, exit code 0)
- `repair_scoring` continues after a single match fails and exits non-zero

---

## Verification (after each task)

- [ ] `ruff check .` and `ruff format --check .` (pre-existing repo-wide violations remain;
      the files touched by this change are clean apart from those pre-existing findings)
- [x] `mypy .` (clean for all files touched by this change; pre-existing errors elsewhere)
- [x] `pytest` (full suite; no unrelated tests broken)
