# Configurable Tournament

## Why

The application hardcodes the format of the 2026 World Cup in seven different places. Running the
same tipping game for a European Championship — or for any World Cup with a different number of
teams — currently requires a code change, a migration and a deployment.

The hardcoded assumptions are:

| Assumption | Location | Value |
| --- | --- | --- |
| Which rounds exist, and in which order | [matches/constants.py](../../../matches/constants.py) `ROUND_ORDER` | `group, r32, r16, qf, sf, 3rd, final` |
| Which rounds exist (second copy) | [matches/models.py](../../../matches/models.py) `Match.ROUND_CHOICES` | same seven codes |
| Round labels | [matches/constants.py](../../../matches/constants.py) `ROUND_LABELS`, [users/templatetags/user_tags.py](../../../users/templatetags/user_tags.py) `round_label`, [templates/predictions/prediction_list.html](../../../templates/predictions/prediction_list.html) `phaseLabels` | three copies |
| Round multipliers | [scoring/match_scoring.py](../../../scoring/match_scoring.py) `ROUND_MULTIPLIERS` | `1/2/2/3/3/3/3` |
| Joker multiplier | [scoring/match_scoring.py](../../../scoring/match_scoring.py) | hardcoded `× 2` |
| Jokers per round and the shared `sf`/`3rd`/`final` pool | [predictions/services.py](../../../predictions/services.py) `JOKER_LIMITS`, `COMBINED_ROUNDS` | `0/3/3/2/2/2/2`, pool of 2 |
| Group-stage prediction limit | [predictions/services.py](../../../predictions/services.py) `GROUP_STAGE_LIMIT` | `36` |
| Prediction lock buffer | [predictions/services.py](../../../predictions/services.py) `LOCK_BUFFER_MINUTES` | `3` |
| Champion bonus points | [scoring/champion_scoring.py](../../../scoring/champion_scoring.py) `CHAMPION_POINTS` | `A = 20`, `B = 30` |
| API competition | [matches/api_client.py](../../../matches/api_client.py), [matches/services.py](../../../matches/services.py) | `competition="WC"` |
| API stage → round mapping | [matches/services.py](../../../matches/services.py) `API_ROUND_MAP` | seven fixed pairs |

A European Championship differs from a World Cup in exactly the dimensions this table covers: it has
no round of 32, it has no third-place match, it has fewer group matches, and it is a different
competition in the football-data.org API. None of these differences are conceptually special — they
are all "which rounds exist and what are their parameters".

Two defects fall out of the same analysis and are fixed here:

1. **`r32` is labelled "Achtelfinale" in all three label copies.** The correct German label is
   "Sechzehntelfinale". The templates work around the bug by rendering "Achtelfinale (R32)" and
   "Achtelfinale (R16)" so the two rounds can be told apart.
2. **`Team.points` is dead code.** The field is declared with `help_text="Championship points"` and
   is never read or written by any production code path — only `TeamAdmin.list_display` and three
   tests that assert its default. It was superseded by `Team.odds_category` and has occupied the
   name this change needs.

## What Changes

Move tournament format from Python constants into two database tables that an administrator can
create and edit, and make every consumer read from them.

- Add a `Tournament` model holding tournament-wide settings (name, API competition code, API season,
  prediction lock buffer, active flag). Exactly one tournament may be active at a time, enforced by
  a partial unique index.
- Add a `Round` model holding all per-round settings: code, label, order, score multiplier, joker
  count, joker multiplier, joker pool, prediction limit and API stage name. Rounds belong to one
  tournament; nothing is shared between tournaments.
- Convert `Match.round` from a `CharField` with a fixed `choices` list into a `ForeignKey` to
  `Round` with `on_delete=PROTECT`.
- Replace `Team.odds_category` and the dead `Team.points` field with a single `Team.champion_points`
  integer. Champion bonus points are set per team, not derived from two fixed categories.
- Rewrite `ScoringService`, `PredictionLimitService` and `champion_scoring` to read their parameters
  from `Round` and `Tournament` instead of module-level dicts.
- Drive the football-data.org sync from the active tournament: competition code from
  `Tournament.api_competition_code`, stage mapping from `Round.api_stage`. Remove the silent
  `API_ROUND_MAP.get(stage, "group")` fallback that would otherwise import unknown stages as group
  matches.
- Add tournament and round administration to the Django admin, including an inline round editor,
  validation of round invariants, and a "recalculate scores" action for when configuration changes
  after matches have already been scored.
- Add a `create_tournament` management command and a matching admin template dropdown, both backed
  by the same preset definitions (`wm48`, `wm32`, `em24`) and the same creation function used by
  the test fixtures.
- Fix the `r32` label and collapse the three label copies into `Round.label`.
- Add a `make_match()` test factory so the test suite is decoupled from the `Match` schema before
  the foreign-key migration lands.

Switching between tournaments is an operational procedure, not a feature: the database is wiped,
migrations are re-run, a new tournament is created, and teams and matches are synced. Because no
data from a previous tournament ever coexists with the current one, no query needs to be scoped by
tournament and no historical data has to be preserved.

## Capabilities

### New Capabilities

- `tournament-configuration`: `Tournament` and `Round` models, their invariants, the admin
  interface, presets and the `create_tournament` command.
- `prediction-limits`: joker limits, joker pools, per-round prediction limits and the lock buffer,
  all read from configuration.
- `match-sync`: football-data.org synchronisation driven by the active tournament.

### Modified Capabilities

- `match-model`: `Match.round` becomes a foreign key to `Round`.
- `team-model`: `odds_category` and `points` are replaced by `champion_points`.
- `scoring-service`: round multiplier, joker multiplier and champion bonus are read from
  configuration; the final match is identified by `Round.is_final`.

## Impact

**New files**

- `matches/tournament.py` — `get_active_tournament()` accessor and `create_tournament()` factory
- `matches/presets.py` — `TOURNAMENT_PRESETS` definitions
- `matches/management/commands/create_tournament.py`
- `matches/tests/test_tournament_models.py`, `matches/tests/test_tournament_admin.py`,
  `matches/tests/test_create_tournament_command.py`

**Modified models and migrations**

- `matches/models.py` — new `Tournament`, `Round`; `Match.round` → FK; `Team.odds_category` removed,
  `Team.points` renamed to `champion_points`
- New migrations in `matches/`, including a data migration that seeds the 2026 World Cup with the
  values currently hardcoded and re-points existing matches

**Modified services and views**

- `scoring/match_scoring.py`, `scoring/champion_scoring.py`, `scoring/ranking_service.py`,
  `scoring/signals.py`, `scoring/exports.py`
- `predictions/services.py`, `predictions/views.py`
- `matches/services.py`, `matches/api_client.py`, `matches/admin.py`,
  `matches/management/commands/sync_teams.py`, `matches/management/commands/update_matches.py`
- `users/forms.py`, `users/views.py`, `users/templatetags/user_tags.py`

**Deleted**

- `matches/constants.py` (`ROUND_ORDER`, `ROUND_LABELS`, `get_available_rounds()` are replaced by
  `Round` queries)
- `Match.ROUND_CHOICES`, `ScoringService.ROUND_MULTIPLIERS`, `ScoringService.VALID_ROUNDS`,
  `PredictionLimitService.JOKER_LIMITS`, `PredictionLimitService.COMBINED_ROUNDS`,
  `PredictionLimitService.GROUP_STAGE_LIMIT`, `PredictionLimitService.LOCK_BUFFER_MINUTES`,
  `champion_scoring.CHAMPION_POINTS`, `matches/services.py::API_ROUND_MAP`

**Templates**

- `templates/predictions/prediction_list.html` — phase labels come from context instead of a
  JavaScript dictionary

**Documentation**

- `docs/rules/wm2026-rules.md` — section 8 (champion categories) and section 15 (open
  clarifications) updated to describe per-team champion points
- `docs/project/decisions.md` — decision record for configuration-in-database and for replacing the
  A/B champion categories
- `docs/project/architecture.md` — model diagram and the "hardcoded constants" section
- `README.md` — tournament setup and switching runbook

**Tests**

- `conftest.py` gains `make_match()` and tournament fixtures; roughly 120 `Match.objects.create(...)`
  call sites across 16 test files are migrated to the factory

## Non-Goals

- **Multiple tournaments at the same time.** Exactly one tournament exists per database. Archiving,
  cross-tournament leaderboards and historical views are explicitly out of scope.
- **Preserving data across a tournament switch.** Switching wipes the database. No snapshot, no
  migration path, no per-tournament user statistics.
- **Configurable scoring categories.** The 6/5/4/3/1/0 point categories, their precedence order and
  the tie-breaker order stay in code. They define the game, not the tournament format, and changing
  them should require review rather than an admin form.
- **A prediction limit shared across several rounds.** `prediction_limit` is per round. A pooled
  limit analogous to `joker_pool` is a plausible future addition but is not needed for any known
  tournament format.
- **Additional bonus predictions** such as top scorer or runner-up.
- **Payout calculation.** The payout rules in `docs/rules/wm2026-rules.md` are not implemented today
  and remain unimplemented.
- **An admin UI for switching tournaments.** Switching is a documented runbook that starts with
  dropping the database.
