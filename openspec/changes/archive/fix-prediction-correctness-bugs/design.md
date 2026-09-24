# Fix Prediction Correctness Bugs - Design

## Context

The affected code paths as they exist today:

- **`predictions/views.py` → `PredictionSaveView.post()`**
  Order of operations is: lock check → `MatchPrediction.objects.get_or_create()` →
  `if created and match.round == "group": can_add_group_stage_prediction(user)` → delete on
  failure. `PredictionLimitService.can_add_group_stage_prediction()` returns
  `get_group_stage_prediction_count(user) < GROUP_STAGE_LIMIT` with `GROUP_STAGE_LIMIT = 36`, and
  the count already contains the row created a moment earlier.

- **`matches/models.py` → `Match.save()`**
  Loads the previous row (`Match.objects.get(pk=self.pk)`), keeps `old_home`/`old_away`, calls
  `super().save()`, then sends `match_result_entered` only when both goals are set *and* one of
  the two goal values changed. `winner` and `status` are ignored, although
  `get_current_champion_team()` in `scoring/champion_scoring.py` explicitly depends on both
  (`status == "scheduled"` → no champion; draw → `winner` decides the penalty-shootout champion).

- **`scoring/signals.py` → `score_predictions_on_result()`**
  Calls `ScoringService.score_all_predictions_for_match()`, then
  `update_live_champion_bonuses()` for finals, then `RankingService.update_all_user_ranks()`,
  all inside a single `try/except Exception: logger.exception(...)`.

- **`matches/services.py` → `sync_matches_from_api()` / `_sync_match()`**
  Iterates API payloads and calls `Match.objects.update_or_create()`, which runs inside a Django
  `transaction.atomic()` block and triggers `Match.save()` and therefore the signal. Any exception
  from a single match currently aborts the whole sync iteration; `update_matches` catches it at
  loop level, logs, and sleeps 60s.

Relevant existing guarantees that the design can rely on:

- `ScoringService.score_prediction()` updates user aggregates via **deltas** against the stored
  `points_earned`/`is_exact_match`, so re-scoring an already scored match is idempotent.
- `update_live_champion_bonuses()` resets all bonuses before re-awarding, so it is idempotent too.
- `MatchPrediction.points_earned` is `null` until a prediction has been scored, and
  `MatchPrediction.match` uses `related_name="predictions"`. This makes "match has goals but
  unscored predictions" a reliable, derivable failure signal — no extra state needed.

## Goals / Non-Goals

**Goals:**

- A user can save exactly 36 group-stage predictions; the 37th is rejected with the existing error
  partial and without side effects.
- A change to `winner` or `status` that affects scoring triggers `match_result_entered`, while
  saves touching only unrelated fields do not.
- Scoring failures are atomic, surfaced to the caller, detectable from the data, and repairable
  via a management command.
- `update_matches` stays resilient: one bad match must not kill the loop.
- Each of the three fixes stays independently reviewable and independently revertible.

**Non-Goals:**

- Changing the scoring formula, round multipliers, or joker rules.
- Introducing a queue, retry daemon, or background worker.
- Adding a model/migration that persists scoring state.
- Reworking the HTMX polling or version-key issues from §15 Priority 2.

## Decisions

### 1. Check the group-stage limit before creating the prediction row

**Decision:** In `PredictionSaveView.post()`, look the prediction up first and only check the
limit when the save would actually create a new group-stage row:

```python
with transaction.atomic():
    prediction = MatchPrediction.objects.filter(user=user, match=match).first()
    created = prediction is None

    if created and match.round == "group" and not (
        PredictionLimitService.can_add_group_stage_prediction(user)
    ):
        return render(request, "predictions/prediction_error.html", {...}, status=400)

    if created:
        prediction = MatchPrediction.objects.create(
            user=user,
            match=match,
            predicted_goals_home=0,
            predicted_goals_away=0,
        )
```

With 35 stored predictions the 36th passes (`35 < 36`), with 36 stored predictions the 37th is
rejected (`36 < 36` is `False`). Editing an existing prediction never hits the limit check.

**Rationale:**

- `can_add_group_stage_prediction()` already has the correct "can I add one more?" semantics; the
  bug is purely the call order. Keeping the service untouched keeps the existing service tests
  valid and the blast radius minimal.
- No row is created and deleted for a rejected request, so no phantom rows, no wasted primary
  keys, and no `post_save` side effects for predictions that were never accepted.

**Alternatives considered:**

- *Keep `get_or_create()` and compare `count <= 36`:* rejected — it encodes "one row already
  exists" into the service, makes `can_add_group_stage_prediction()` mean two different things
  depending on the caller, and still creates/deletes rows.
- *Enforce the limit in `MatchPrediction.save()` or a DB constraint:* rejected — the limit is a
  per-user aggregate rule that PostgreSQL cannot express as a simple constraint, and moving it
  into the model would duplicate logic that already lives in the service.

**Concurrency:** the lookup, the check and the create run inside one `transaction.atomic()` block.
Two truly simultaneous requests could still both pass the check; the `unique_together
[["user", "match"]]` constraint prevents duplicates for the same match, and at ~50–100 users the
residual risk of a 37th row from two parallel requests for *different* matches is acceptable and
detectable. Documented here rather than solved with row locking.

### 2. Trigger scoring on any change to a scoring-relevant field

**Decision:** `Match` declares the fields that can influence scoring and `save()` compares all of
them:

```python
SCORING_RELEVANT_FIELDS = ("goals_home", "goals_away", "winner", "status")

def save(self, *args, **kwargs):
    previous = None
    if self.pk:
        previous = Match.objects.filter(pk=self.pk).values(*self.SCORING_RELEVANT_FIELDS).first()

    super().save(*args, **kwargs)

    if self.goals_home is None or self.goals_away is None:
        return

    changed = previous is None or any(
        previous[field] != getattr(self, field) for field in self.SCORING_RELEVANT_FIELDS
    )
    if changed:
        match_result_entered.send(sender=self.__class__, match=self)
```

**Rationale:**

- `winner` decides the champion after a penalty shootout and `status` gates
  `get_current_champion_team()`; both are scoring inputs and must be watched.
- Saves that only change `kickoff`, `external_id`, `round` or team FKs compare equal on all four
  tracked fields and send nothing, which satisfies "no redundant re-scoring on unrelated saves".
- A newly created match that already carries goals (first import of a finished match) triggers
  scoring, which today's code misses as well.
- `.values(*fields)` fetches only the four tracked columns instead of hydrating a full `Match`.

**Trade-off:** a `live → finished` transition with unchanged goals re-scores the match once. That
is intentional (it is exactly the case where the final result is confirmed) and harmless because
scoring is delta-based and idempotent. The named constant documents the rule and keeps the model
and the repair command in sync.

**Alternatives considered:**

- *Only add `winner`:* rejected — `status` changes alone flip `get_current_champion_team()` from
  `None` to a champion for the final.
- *Compare every field via `__dict__` diff:* rejected — kickoff or team corrections would trigger
  pointless re-scoring, which the requirement explicitly forbids.
- *Signal from the importer instead of the model:* rejected — admin edits bypass the importer and
  would stop scoring entirely.

### 3. Make scoring failures atomic and let them propagate

**Decision:** `score_predictions_on_result()` no longer swallows exceptions:

```python
@receiver(match_result_entered)
def score_predictions_on_result(sender, match, **kwargs):
    try:
        with transaction.atomic():
            scored_count = ScoringService.score_all_predictions_for_match(match)
            if match.round == "final":
                update_live_champion_bonuses()
            RankingService.update_all_user_ranks()
    except Exception:
        logger.exception("Scoring failed for match %s (id=%s)", match, match.pk)
        raise
```

**Rationale:**

- `transaction.atomic()` turns the three steps into one unit: either all predictions, the champion
  bonus and the ranks are consistent, or nothing is written. This removes the "partially scored
  match" state that currently cannot be distinguished from a correctly scored one.
- Re-raising gives the caller a chance to react. Django's `Signal.send()` propagates receiver
  exceptions, so the exception reaches `Match.save()` and the code that called it.
- In the importer path, `Match.objects.update_or_create()` already wraps the save in
  `transaction.atomic()`, so a scoring failure rolls the match update back as well. The next poll
  sees the values as changed again and retries automatically — the system self-heals.
- In the Django admin path there is no surrounding atomic block (`ATOMIC_REQUESTS` is not enabled),
  so the match row stays saved and the admin sees a hard error instead of a silent success. That
  case is covered by decision 5.

**Alternatives considered:**

- *`send_robust()`:* rejected — it is exactly today's behaviour with extra steps: errors are
  collected and dropped.
- *Retry loop inside the receiver:* rejected — hides latency inside a model save and conflicts
  with the project's "no queue/retry infrastructure" constraint.

### 4. Isolate each match during API sync

**Decision:** `sync_matches_from_api()` wraps the per-match call so that a failure affects only
that match:

```python
for match_data in matches_data:
    try:
        result = _sync_match(match_data)
    except Exception:
        failed_count += 1
        logger.exception("Failed to sync match %s", match_data.get("id"))
        continue
    if result:
        results.append(result)
```

The failure count is logged in the sync summary, and `update_matches` keeps its existing loop-level
`except Exception` as a last resort.

**Rationale:**

- Without this, decision 3 would let one broken match abort the whole sync iteration and stall
  every other live match for 60 seconds.
- The return type `list[MatchSyncResult]` stays unchanged, so `update_matches` and the existing
  `matches/tests/test_update_matches_command.py` keep working.
- The failing match rolled back (see decision 3), so it is retried on the next poll.

**Alternative considered:** extending `MatchSyncResult` with a `failed` flag — rejected for now;
the log line plus the repair command cover the need without changing the public return shape.

### 5. Detect and repair unscored matches with a management command

**Decision:** New command `scoring/management/commands/repair_scoring.py`:

```bash
python manage.py repair_scoring --check   # detect only, exit code 1 if work remains
python manage.py repair_scoring           # repair, exit code 1 if a repair failed
```

Detection derives the broken state from existing data:

```python
Match.objects.filter(
    goals_home__isnull=False,
    goals_away__isnull=False,
    predictions__points_earned__isnull=True,
).distinct().order_by("kickoff")
```

Repair re-runs `ScoringService.score_all_predictions_for_match()` per affected match, then
`update_live_champion_bonuses()` if a final is among them (or a final is finished), then
`RankingService.update_all_user_ranks()` once at the end. Per-match failures are reported and the
command exits non-zero, so a human or a monitoring job notices.

**Rationale:**

- No new model, no migration, no state that can drift from reality: an unscored prediction for a
  match that has goals *is* the failure.
- Scoring and champion bonuses are idempotent, so running the command on a healthy database is a
  no-op besides the queries.
- `--check` gives an explicit, scriptable health signal; `recalculate_scores` remains the
  heavyweight "reset everything" tool, while `repair_scoring` is the targeted, non-destructive one.

**Alternatives considered:**

- *`MatchScoringStatus` model with `pending/ok/failed`:* rejected — extra migration and a second
  source of truth that itself can fail to be written during the same outage.
- *Reuse `recalculate_scores`:* rejected — it resets every user aggregate and every prediction,
  which is far too destructive for a single failed match during a live tournament.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Re-scoring on `live → finished` with unchanged goals | Scoring is delta-based and idempotent; the extra pass touches only that match's predictions |
| A failing signal now aborts an admin save or an API match update | Intentional (failures must be visible); importer isolates per match, and `repair_scoring` repairs anything left over |
| Wider ranking updates when `status` changes trigger scoring | `RankingService.update_all_user_ranks()` already runs on every goal change; frequency rises only marginally at this scale |
| `--check` false positives for matches nobody predicted | Query only flags matches that *have* predictions with `points_earned IS NULL`; matches without predictions are not returned |
| Group-limit race between two parallel requests | `transaction.atomic()` plus `unique_together`; residual risk documented and detectable |

## Migration Plan

1. No database migrations. The change is code-only and can be deployed in one release.
2. Deploy order is irrelevant between the three fixes; each task is independently revertible.
3. After deployment run `python manage.py repair_scoring --check` once to surface matches that were
   silently left unscored by the old behaviour, then run `python manage.py repair_scoring` to fix
   them.
4. Rollback: revert the individual commit. No data cleanup required, since no fix writes new state
   formats.

## Open Questions

- Should `repair_scoring --check` be added to the `update_matches` loop as a periodic health probe,
  or stay an operator-triggered command? (Kept out of scope here; the command is the recovery
  surface, the loop stays a pure importer.)
