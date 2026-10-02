# Configurable Tournament - Design

## Context

The tipping game currently encodes the format of one specific tournament — the 2026 World Cup with
48 teams, 72 group matches, a round of 32 and a third-place match — across four Python dictionaries
in three modules plus a `choices` list on `Match.round`. Changing to a European Championship, which
has 24 teams, no round of 32 and no third-place match, means editing every one of those places and
shipping a migration.

The codebase is otherwise in good shape for this work. The `code-hygiene-cleanup` change is
archived, which means the duplicate `scoring/services.py` — a second, dead copy of
`ROUND_MULTIPLIERS` and `CHAMPION_POINTS` — is already gone, and scoring lives in exactly one place
per concern (`scoring/match_scoring.py`, `scoring/champion_scoring.py`,
`scoring/ranking_service.py`). The measured baseline is 539 passing tests, 0 ruff findings and 0
mypy errors across 146 files.

Two properties of the current data model shape every decision below:

**Points are denormalised.** `MatchPrediction.points_earned` is computed once when a result is
entered and stored. `User.total_points`, `exact_match_count`, `jokers_used`,
`champion_bonus_points` and `global_rank` are caches over those rows. Nothing recomputes on read.
Configuration that feeds the points formula therefore cannot be changed freely once results exist.

**User statistics are single-valued.** There is one `total_points` per user, one
`predicted_champion` per user. They belong to a tournament, not to a user, but there is nowhere else
to put them without introducing a per-tournament participant table.

The second property would normally force either a participant table or a tournament filter on every
aggregation. The project decided instead that switching tournaments starts with dropping the
database. That decision removes the problem rather than solving it, and it is what makes this change
tractable.

## Goals / Non-Goals

### Goals

- An administrator can create a tournament and define its rounds, with per-round score multiplier,
  joker count, joker multiplier, joker pool and prediction limit, entirely through the Django admin.
- The same configuration can be created from the command line, using the same code path, so tests
  and a post-wipe bootstrap do not diverge from what the admin produces.
- Tournaments with and without a third-place match, with and without a round of 32, and with any
  number of group matches are expressible without code changes.
- Champion bonus points are set per team as a plain number.
- The football-data.org sync follows the configured competition and stage names.
- Round labels have exactly one source of truth, and `r32` is labelled correctly.
- The 539-test baseline does not regress, and no scoring result changes as a side effect of the
  refactor.

### Non-Goals

- Two tournaments coexisting in one database.
- Preserving predictions, points or rankings across a tournament switch.
- Making the 6/5/4/3/1/0 scoring categories, their precedence or the tie-breaker order configurable.
- A prediction limit shared across multiple rounds.
- Bonus predictions other than the champion pick.
- Implementing the payout rules.

## Decisions

### 1. Rounds are rows, not an enum

`Round` becomes a table with one row per round per tournament. Every per-round parameter is a column
on that row.

```
Round
  tournament        FK → Tournament, on_delete=CASCADE, related_name="rounds"
  code              CharField(10)    "group", "r32", "3rd"
  label             CharField(50)    "Sechzehntelfinale"
  order             PositiveSmallIntegerField
  multiplier        PositiveSmallIntegerField   default 1
  joker_count       PositiveSmallIntegerField   default 0
  joker_multiplier  PositiveSmallIntegerField   default 2
  joker_pool        CharField(20), blank
  prediction_limit  PositiveSmallIntegerField, null=True
  is_final          BooleanField                default False
  api_stage         CharField(30)    "ROUND_OF_32"
```

This is the decision that makes everything else fall out. Three consequences are worth naming
explicitly:

- **"Is there a third-place match?" is not a flag.** A World Cup configuration contains a `3rd` row;
  a European Championship configuration does not. No `has_third_place` boolean, no branch in the
  scoring or prediction code, no special case in the phase navigation.
- **"Which rounds exist?" is a query,** replacing `ROUND_ORDER`. `Round.objects.filter(
  tournament=t).order_by("order")` is the ordered list, and `ranking_service`'s round cutoff uses
  `order` instead of a list index.
- **Labels are data.** A European Championship's round of 16 is "Achtelfinale"; a 48-team World Cup
  additionally has a "Sechzehntelfinale". The same code can carry a different label in a different
  tournament, which the current `ROUND_LABELS` dict cannot express.

**Alternative rejected:** keeping the round codes as an enum and adding a configuration table keyed
by code. This keeps a fixed superset of rounds in code, so any future format with a round the
superset does not contain still needs a migration — which is the problem this change exists to
remove.

### 2. `Tournament` and `Round` live in the `matches` app

`Team` and `Match` are already in `matches`, and `Round` has a one-to-many relationship with `Match`.
Putting the new models in the same app avoids a cross-app migration dependency chain and a new app
registration for roughly 150 lines of model code.

**Alternative rejected:** a dedicated `tournaments` app. Conceptually cleaner and consistent with the
project's modular app convention, but it buys nothing here: the models are inseparable from `Match`
and would import `matches.Team` anyway. If `matches` later grows further, extracting the two models
is a mechanical move.

### 3. `Match.round` becomes a `ForeignKey` with `on_delete=PROTECT`

```
- round = CharField(max_length=10, choices=ROUND_CHOICES)
+ round = ForeignKey(Round, on_delete=PROTECT, related_name="matches")
```

`PROTECT` is the point: an administrator editing the round list cannot delete the third-place round
while matches reference it. Without referential integrity, a deleted round leaves matches pointing at
a code that no longer resolves, and the failure surfaces as a `KeyError` during scoring rather than
as a validation error in the admin.

The cost is real: about 120 `Match.objects.create(..., round="group")` call sites across 16 test
files, plus roughly 30 production query sites that change from `round="group"` to
`round__code="group"` and from `match__round__in=[...]` to `match__round__code__in=[...]`. Decision
12 exists to isolate the test portion of that cost into its own reviewable task.

Queries that traverse `match.round.multiplier` need `select_related("round")`. The scoring path
already loads matches individually; the prediction list and ranking views need their existing
`select_related` calls extended.

**Alternative rejected:** keeping `Match.round` as a `CharField` and resolving the configuration
through a service lookup. It avoids the test sweep entirely, but gives up cascade protection and
admin dropdowns, and allows a match to reference a round that does not exist.

### 4. Exactly one active tournament, enforced in the database

```python
constraints = [
    models.UniqueConstraint(
        fields=["is_active"],
        condition=Q(is_active=True),
        name="unique_active_tournament",
    ),
]
```

Access goes through a single accessor:

```python
def get_active_tournament() -> Tournament:
    """Return the active tournament, or raise if none is configured."""
```

Strictly, with one tournament per database, the flag is redundant. It is kept because the failure
mode without it is invisible: `Tournament.objects.first()` silently returns an arbitrary row if a
second one is ever created, and the application then reads its multipliers from the wrong
configuration. Two lines of constraint turn that into an impossible state.

The accessor raises rather than returning `None`. An application without a configured tournament
cannot do anything meaningful, and a loud failure at the first request is better than `None`
propagating into the scoring formula. No module-level caching: an administrator changing a
multiplier must see the effect on the next request, and per-request query cost for a single-row
lookup is negligible at this scale.

### 5. Joker pools are a shared key with an equality invariant

The current rules give the semi-final, third-place match and final a shared pool of two jokers.
`Round.joker_pool` generalises this: rounds carrying the same non-empty `joker_pool` value draw from
one pool. The effective pool key is `joker_pool or code`, so a round with a blank pool is its own
pool.

The pool limit is `joker_count`, and a formset-level validation requires every round in a pool to
declare the same `joker_count`. For a European Championship without a third-place match, the same
pool simply contains two rounds instead of three.

**Alternative rejected:** a separate `JokerPool(tournament, name, limit)` table. It removes the
equality invariant and is the more normalised design, but adds a third inline to the tournament admin
for a configuration that has exactly one non-trivial pool in every known tournament format. If the
equality validation proves annoying in practice, promoting the pool to its own table is a contained
follow-up.

### 6. `Round.prediction_limit` replaces `GROUP_STAGE_LIMIT` and deletes the group-stage special case

`prediction_limit` is nullable; `NULL` means every match in the round may be predicted. The group
stage of a World Cup sets `36`; the same round in a European Championship sets whatever the
administrator chooses.

This generalisation removes three hardcoded group-stage branches:

- `PredictionLimitService.can_add_group_stage_prediction()` becomes
  `can_add_prediction(user, round)`
- `get_phase_stats()`'s `if phase == "group": display_total = GROUP_STAGE_LIMIT` becomes
  `display_total = round.prediction_limit or match_count`
- `predictions/views.py`'s `"is_group_stage": round_code == "group"` becomes
  `"has_prediction_limit": round.prediction_limit is not None`

The group stage stops being a special kind of round and becomes a round that happens to have a
limit.

### 7. `Round.is_final` replaces `filter(round="final")`

Three call sites locate the final by string comparison:
`scoring/champion_scoring.py::get_current_champion_team()`, `scoring/signals.py`, and
`scoring/management/commands/repair_scoring.py`. All three switch to `round__is_final=True`.

A partial unique index allows at most one final per tournament, and formset validation requires at
least one. Deriving the final from the highest `order` would work for today's configuration — where
`3rd` is ordered before `final` — but breaks silently the moment someone orders the third-place match
last, which is how the matches are actually scheduled in some tournaments.

### 8. Champion points are a number per team; `Team.points` is reused

```
Team
  name
  fifa_code
  champion_points   IntegerField, default 0   # was: points (dead) + odds_category
```

`CHAMPION_POINTS = {"A": 20, "B": 30}` and `Team.odds_category` are removed.
`calculate_champion_points(team)` collapses to `team.champion_points`.

`Team.points` already exists with `help_text="Championship points"` and is never read or written by
production code — only by `TeamAdmin.list_display` and three tests asserting its default. Renaming it
avoids adding a field whose name would collide conceptually with a dead one.

The current A/B scheme remains expressible: set eight teams to 20 and the rest to 30. The change is a
strict superset of today's behaviour, and the seed migration derives `champion_points` from the
existing `odds_category` so no bonus changes value.

This *is* a game-rule change, not just a refactor. `docs/rules/wm2026-rules.md` section 8 describes
categories A and B as the rule, so the rules document and `docs/project/decisions.md` are updated as
part of this change rather than left to drift. It also closes open clarification 3 in section 15,
which asks how the documented maximum score of 802 reconciles with a category-B champion worth 30.

**Alternative rejected:** a `TournamentTeam(tournament, team, champion_points)` through-table. It is
required if one team needs different points in two coexisting tournaments — which decision 9 rules
out.

### 9. No tournament scoping in queries; the database wipe is the invariant

Every aggregation over `MatchPrediction` — in `ranking_service`, `signals`, `exports`,
`notifications` and `repair_scoring` — stays exactly as it is today. None of them gains a
`match__round__tournament=...` filter.

This is safe only because of the operating model: switching tournaments drops the database. The
invariant is therefore

> `MatchPrediction` and `Match` only ever contain rows belonging to the one configured tournament.

and it is maintained by the runbook, not by query filters.

The alternative — keeping old data and filtering every aggregation — was considered and rejected. It
requires getting a filter right in five modules, and a single omission silently adds a previous
tournament's points to the current leaderboard. That is a defect with no visible symptom until
someone checks the arithmetic. Deleting the data makes the failure impossible rather than unlikely.

The trade-off is accepted explicitly: the previous tournament's final standings are gone, and so is
every user's previous champion pick. The project has stated it does not want that history.

### 10. Configuration is read live, with an explicit recalculation action

Because points are denormalised (see Context), editing `Round.multiplier` or `Round.joker_multiplier`
after results have been scored leaves `MatchPrediction.points_earned` and the `User` caches stale.
Nothing in the current code detects this.

Three options were weighed:

| Option | Behaviour | Assessment |
| --- | --- | --- |
| Freeze | Round fields become read-only once scored predictions exist | Safe, but a genuine typo becomes uncorrectable |
| Auto-recalculate | Saving a round triggers recalculation | Consistent, but one click silently starts a bulk write |
| Warn and offer | Admin sees the affected count and an explicit action | Visible, deliberate, reversible |

The third is chosen. `RoundAdmin` and the tournament change form display a warning when scored
predictions exist for the tournament, and a "Recalculate scores" admin action reuses the existing
`recalculate_scores` management command logic. No new scoring machinery is introduced.

### 11. Presets are code, shared by admin, CLI and tests

`matches/presets.py` holds `TOURNAMENT_PRESETS: dict[str, list[RoundSpec]]` with `wm48`, `wm32` and
`em24`. A single function creates a tournament from a preset:

```python
def create_tournament(
    *,
    name: str,
    slug: str,
    api_competition_code: str,
    api_season: int | None = None,
    preset: str | None = None,
    activate: bool = False,
) -> Tournament
```

```
                 create_tournament()
                  ▲        ▲        ▲
                  │        │        │
   admin add-form │   management    │  pytest fixture
   preset dropdown │   command      │
```

Three consumers, one code path. The test fixture exercising the same function the administrator
clicks is the main argument for this shape — it removes the possibility of the tested configuration
and the produced configuration diverging.

Presets live in code rather than in the database because the database is dropped between
tournaments; a preset stored in a table would not survive the event it exists to support. A preset is
only a set of default values: after creation the rounds are ordinary rows with no reference back to
the preset, and every field remains editable.

Creating a tournament without a preset is fully supported and produces a tournament with no rounds,
to be filled in through the admin inline.

### 12. The test factory lands before the schema change

`conftest.py` gains `make_match(round="group", ...)` plus tournament and round fixtures, and the
roughly 120 direct `Match.objects.create(...)` calls in the test suite are migrated to it — as a
separate task, with no production code touched and an unchanged test count.

Without this, the foreign-key migration arrives as one diff mixing 120 mechanical test edits with
about 30 semantic production changes, which is not reviewable. Afterwards, the schema change touches
the factory once.

## Risks / Trade-offs

**The foreign-key migration is the widest diff in the change.** Mitigated by decision 12, by the
requirement that scoring output is unchanged before and after, and by the 539-test baseline. The
migration itself is four steps — add nullable FK, backfill from the code column, make non-nullable,
drop the old column — so it is reversible up to the final step.

**`Team.odds_category` is dropped, not deprecated.** The seed migration derives `champion_points`
from it first, so no information is lost, but the column is gone afterwards and the change is not
reversible without restoring a dump. Acceptable: no production data exists on this branch, and the
project wipes the database between tournaments regardless.

**Configuration errors are silent at 0.** A round created with `multiplier=0`, or teams left at
`champion_points=0`, produces no error — just no points. Mitigated with `MinValueValidator(1)` on
`multiplier`, and with a visible warning in the tournament admin counting teams still at zero.
Neither is a hard constraint, because zero is legitimate for `joker_count`.

**football-data.org may not expose `EC` on the free tier.** This is an operational unknown that no
data model can solve; it can only be confirmed against the live endpoint. If the competition is
unavailable, the fallback is manual match entry through the existing `MatchAdmin` — unpleasant for
51 matches but not a blocker. Noted as a risk, not designed around.

**Removing the `API_ROUND_MAP` fallback turns a silent mis-import into a hard failure.** Today an
unrecognised stage silently becomes a group match. After this change the sync raises. This is the
intent — a European Championship stage name that nobody mapped must not appear as 51 group-stage
matches — but it does mean the first sync against a new competition will fail loudly until
`Round.api_stage` values are correct.

**Per-request configuration queries.** Reading `Tournament` and `Round` on every request instead of
from module constants adds queries. At roughly 100 users and 104 matches this is not measurable, and
`select_related("round")` keeps the match queries at their current count. Caching is deliberately
omitted so that admin edits take effect immediately.

## Migration Plan

Six tasks, implemented and committed in order. Phase 0 — the `code-hygiene-cleanup` change — is
already archived on this branch.

```
1  make_match() factory                      tests only, no production change
2  Tournament + Round + seed + admin          additive, nothing reads them yet
3  Match.round → ForeignKey                   schema change, behaviour identical
4  constants → configuration                  behaviour becomes configurable
5  API sync follows the tournament
6  create_tournament + presets + runbook
```

Task 2's data migration seeds a tournament named "WM 2026" with exactly the values that are
hardcoded today — multipliers `1/2/2/3/3/3/3`, joker counts `0/3/3/2/2/2/2`, joker multiplier `2`
throughout, pool `ko_final` covering `sf`/`3rd`/`final`, `prediction_limit=36` on the group stage,
`is_final` on `final`, `lock_buffer_minutes=3`, `api_competition_code="WC"` — and derives
`Team.champion_points` from `Team.odds_category` using 20 for A and 30 for B. The only intentional
difference from today is the `r32` label, which is seeded as "Sechzehntelfinale".

The acceptance criterion tying the plan together: after task 4, re-running
`manage.py recalculate_scores` on a database seeded with test data must produce byte-identical
`User.total_points`, `exact_match_count`, `jokers_used` and `champion_bonus_points` compared to
before the change. Configuration became editable; nothing became different.

Each task ends with `make lint && make typecheck && make test` against the baseline of 539 passing
tests, 0 ruff findings and 0 mypy errors in 146 files.

## Open Questions

1. **Does the football-data.org free tier include the `EC` competition, and what are its stage
   names?** Only answerable against the live API. It affects the `em24` preset's `api_stage` values
   but not the design. Resolve before task 6; task 5 can ship with `EC` unverified.

2. **Should `Round.code` be validated against a known vocabulary?** Free text maximises flexibility
   but allows typos that make nothing fail visibly. Current lean: free text, because `code` stops
   being semantically meaningful once labels and ordering are explicit columns — but `is_final` and
   `api_stage` carry the meaning that `code` used to, so this is worth a second look during
   implementation.

3. **Where should the "teams without champion points" warning appear** — on the tournament change
   form, in the team changelist, or as a Django system check? A system check surfaces it on every
   `manage.py` invocation, which may be noise during normal development. Decide during task 6.
