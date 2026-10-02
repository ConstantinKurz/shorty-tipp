# Configurable Tournament - Tasks

Six tasks. Each is reviewable, testable and revertible on its own. Implement **one task at a time**
and commit it separately.

**Baseline that must never regress** (measured on `make-game-programmable` before this change):

| Check | Command | Baseline |
| --- | --- | --- |
| Tests | `make test` | 539 passed |
| Format | `make format-check` | 0 files would change |
| Lint | `make lint` | 0 errors |
| Types | `make typecheck` | 0 errors in 146 source files |

Run `make lint && make typecheck && make test` after every task.

**Order matters — implement 1 through 6 in sequence.** Task 1 decouples the test suite from the
`Match` schema that task 3 changes. Task 2 creates the tables that task 4 reads. Task 3 must land
before task 4, because task 4's services navigate `match.round.multiplier`. Task 5 depends on
`Round.api_stage` existing and being populated. Task 6 packages what tasks 2–5 built.

Phase 0 of the plan — the `code-hygiene-cleanup` change — is already archived on this branch and
requires no work here.

---

## 1. Add a `make_match()` test factory

**Goal:** No test constructs a `Match` directly, so the foreign-key migration in task 3 touches one
factory instead of roughly 120 call sites.

**Scope:** `conftest.py` and the test files listed below. Test code only.

**Out of scope:** Any production module. Any change to what the tests assert. Any new test case.

- [x] Add `make_match(*, team_home, team_away, kickoff=None, round="group", **kwargs) -> Match` to
      [conftest.py](../../../conftest.py), accepting the round as a string for now so the signature
      survives task 3 unchanged
- [x] Add a `make_team(name, fifa_code, **kwargs)` helper if the same duplication exists for `Team`
- [x] Migrate every direct `Match.objects.create(...)` call to the factory in:
      `matches/tests/test_api_integration.py`, `matches/tests/test_match_scoring.py`,
      `matches/tests/test_models.py`, `matches/tests/test_services.py`,
      `matches/tests/test_update_matches_command.py`, `notifications/tests/test_email_service.py`,
      `predictions/tests/test_match_predictions_page.py`, `predictions/tests/test_services.py`,
      `predictions/tests/test_views.py`, `scoring/tests/test_champion_scoring.py`,
      `scoring/tests/test_exports.py`, `scoring/tests/test_integration.py`,
      `scoring/tests/test_management_commands.py`, `scoring/tests/test_ranking_service.py`,
      `scoring/tests/test_scoring_aggregates.py`, `scoring/tests/test_scoring_service.py`,
      `users/tests/test_ranking_view.py`, `users/tests/test_settings_view.py`
- [x] Leave `matches/tests/test_models.py` cases that deliberately test `Match` construction and
      validation using the model directly, and add a comment stating why
- [x] Verify no `Match.objects.create(` remains outside `conftest.py`,
      `matches/tests/test_models.py` and `predictions/management/commands/create_wm2026_testdata.py`:
      `grep -rn "Match.objects.create(" --include='*.py' .`

**Acceptance criteria:**

- The test count is exactly 539 before and after; no test is added, removed, renamed or skipped
- `grep` for `Match.objects.create(` returns only the three allowed locations
- No file outside `conftest.py` and `*/tests/*` is modified

**Required tests:** None new. The existing suite is the regression test — an unchanged pass count at
539 is the acceptance signal.

---

## 2. Add `Tournament` and `Round`, seed the 2026 World Cup, fix the `r32` label

**Goal:** The configuration tables exist, are populated with exactly today's values, and are
editable in the admin. No production code reads them yet.

**Scope:** `matches/models.py`, `matches/admin.py`, new migrations in `matches/`, new tests.

**Out of scope:** `Match.round` (task 3). Any service reading the new tables (task 4). `Team`
fields (task 4). Presets and the management command (task 6).

- [x] Add `Tournament` to [matches/models.py](../../../matches/models.py) with `name`, `slug`
      (unique), `api_competition_code`, `api_season` (nullable), `lock_buffer_minutes`
      (default 3), `is_active`
- [x] Add a `UniqueConstraint(fields=["is_active"], condition=Q(is_active=True),
      name="unique_active_tournament")`
- [x] Add `Round` with `tournament` (FK, `CASCADE`, `related_name="rounds"`), `code`, `label`,
      `order`, `multiplier` (`MinValueValidator(1)`), `joker_count`, `joker_multiplier`,
      `joker_pool` (blank), `prediction_limit` (nullable), `is_final`, `api_stage`
- [x] Add unique constraints on `(tournament, code)`, `(tournament, order)`,
      `(tournament, api_stage)`, and a partial unique constraint on `is_final=True` per tournament
- [x] Add `Meta.ordering = ["order"]` to `Round` and `__str__` returning the label
- [x] Add `matches/tournament.py` with `get_active_tournament() -> Tournament`, raising a clear
      exception when no active tournament exists
- [x] Add `Round.effective_joker_pool` returning `self.joker_pool or self.code`
- [x] Create the schema migration
- [x] Create a data migration seeding tournament "WM 2026" (`slug="wm-2026"`,
      `api_competition_code="WC"`, `api_season=2026`, `lock_buffer_minutes=3`, `is_active=True`)
      and its seven rounds with exactly the current hardcoded values:

      | code | label | order | mult | jokers | joker× | pool | limit | final | api_stage |
      | --- | --- | --: | --: | --: | --: | --- | --: | :-: | --- |
      | group | Gruppenphase | 1 | 1 | 0 | 2 | | 36 | | GROUP_STAGE |
      | r32 | Sechzehntelfinale | 2 | 2 | 3 | 2 | | | | ROUND_OF_32 |
      | r16 | Achtelfinale | 3 | 2 | 3 | 2 | | | | ROUND_OF_16 |
      | qf | Viertelfinale | 4 | 3 | 2 | 2 | | | | QUARTER_FINALS |
      | sf | Halbfinale | 5 | 3 | 2 | 2 | ko_final | | | SEMI_FINALS |
      | 3rd | Spiel um Platz 3 | 6 | 3 | 2 | 2 | ko_final | | | THIRD_PLACE |
      | final | Finale | 7 | 3 | 2 | 2 | ko_final | | x | FINAL |

- [x] Note in the migration that `r32` is deliberately seeded as "Sechzehntelfinale", correcting the
      "Achtelfinale" label currently in `matches/constants.py`
- [x] Add `TournamentAdmin` with a `Round` inline (`TabularInline`, `extra=0`)
- [x] Add inline formset validation rejecting: more than one `is_final`, zero `is_final`, duplicate
      `code`/`order`/`api_stage`, and unequal `joker_count` among rounds sharing a non-empty
      `joker_pool`
- [x] Verify `python manage.py check` and `python manage.py migrate` succeed on an empty database
      and on a database seeded by `create_wm2026_testdata`

**Acceptance criteria:**

- Migrating an existing development database produces exactly one `Tournament` and seven `Round`
  rows with the values in the table above
- The active-tournament constraint rejects a second `Tournament` with `is_active=True` at the
  database level
- The `is_final` constraint rejects a second final within one tournament
- An administrator can add, edit, reorder and delete rounds through the tournament change form
- Formset validation rejects each of the five invalid configurations listed above with a readable
  message
- No existing test changes behaviour; the count rises only by the new tests below

**Required tests** (`matches/tests/test_tournament_models.py`,
`matches/tests/test_tournament_admin.py`):

- `test_only_one_active_tournament_allowed` — creating a second active tournament raises
  `IntegrityError`
- `test_only_one_final_round_per_tournament`
- `test_round_code_order_and_api_stage_unique_per_tournament`
- `test_two_tournaments_may_share_round_codes` — the same `code` in two tournaments is allowed
- `test_effective_joker_pool_falls_back_to_code`
- `test_get_active_tournament_raises_when_none_configured`
- `test_seed_migration_creates_wm2026_with_expected_rounds` — asserts all seven rows and their
  values, including the `Sechzehntelfinale` label
- `test_round_inline_rejects_two_finals`, `test_round_inline_rejects_no_final`,
  `test_round_inline_rejects_mismatched_joker_counts_in_pool`

---

## 3. Convert `Match.round` to a `ForeignKey`

**Goal:** Matches reference a `Round` row. Scoring output is bit-for-bit identical before and after.

**Scope:** `matches/models.py`, migrations, every query filtering or reading `Match.round`,
`conftest.py`'s factory, `predictions/management/commands/create_wm2026_testdata.py`.

**Out of scope:** Reading any configuration value from `Round` — multipliers, joker counts and
limits still come from the existing constants after this task. `Team` fields. API sync.

- [x] Add `round_fk = ForeignKey(Round, on_delete=PROTECT, related_name="matches", null=True)`
- [x] Data migration mapping each `Match.round` code to the `Round` of the seeded tournament; the
      migration must fail loudly if any match has a code with no matching round
- [x] Migration making `round_fk` non-nullable, dropping `round`, renaming `round_fk` to `round`
- [x] Delete `Match.ROUND_CHOICES`
- [x] Update `make_match()` in [conftest.py](../../../conftest.py) to resolve the round string to a
      `Round` instance, keeping its call signature unchanged
- [x] Update query sites from `round="x"` to `round__code="x"` and `match__round__in=[...]` to
      `match__round__code__in=[...]` in [predictions/services.py](../../../predictions/services.py),
      [predictions/views.py](../../../predictions/views.py),
      [scoring/ranking_service.py](../../../scoring/ranking_service.py),
      [scoring/champion_scoring.py](../../../scoring/champion_scoring.py),
      [scoring/signals.py](../../../scoring/signals.py),
      [scoring/exports.py](../../../scoring/exports.py),
      [scoring/management/commands/repair_scoring.py](../../../scoring/management/commands/repair_scoring.py),
      [users/views.py](../../../users/views.py), [tipapp/views.py](../../../tipapp/views.py)
- [x] Extend `select_related` to include `round` wherever `match.round` is read in a loop —
      specifically the prediction list, the ranking views and `scoring/exports.py`
- [x] Update `MatchAdmin.list_filter` and `list_display` for the relation
- [x] Update `predictions/management/commands/create_wm2026_testdata.py` to resolve rounds
- [x] Update `templates/predictions/partials/match_header.html` and
      `templates/predictions/prediction_row.html` to emit `{{ match.round.code }}` in
      `data-match-stage`

**Acceptance criteria:**

- Deleting a `Round` that has matches raises `ProtectedError`
- `Match.objects.filter(round__code="group").count()` returns what
  `Match.objects.filter(round="group").count()` returned before the migration
- Running `manage.py recalculate_scores` on a database seeded with
  `create_wm2026_testdata` produces identical `User.total_points`, `exact_match_count`,
  `jokers_used` and `champion_bonus_points` values compared to before this task
- No N+1 regression: the prediction list and ranking views issue no more queries than before
- All 539 existing tests pass unchanged

**Required tests** (`matches/tests/test_models.py`, `matches/tests/test_tournament_models.py`):

- `test_match_round_is_protected_from_deletion`
- `test_match_round_relation_resolves_label_and_multiplier`
- `test_round_backfill_migration_maps_all_existing_codes` — migration test asserting no match is
  left unmapped
- Query-count assertions for the prediction list and ranking views using `django_assert_num_queries`

---

## 4. Read configuration from the database

**Goal:** Round multipliers, joker counts, joker multipliers, prediction limits, the lock buffer and
champion points all come from `Tournament`, `Round` and `Team`. This is the task that makes the game
configurable.

**Scope:** `scoring/match_scoring.py`, `scoring/champion_scoring.py`, `scoring/ranking_service.py`,
`scoring/signals.py`, `predictions/services.py`, `predictions/views.py`, `matches/models.py`
(`Team`), `matches/admin.py`, `users/forms.py`, `users/templatetags/user_tags.py`,
`templates/predictions/prediction_list.html`, `matches/constants.py` (deleted), docs.

**Out of scope:** API sync (task 5). Presets and the management command (task 6).

- [x] Rename `Team.points` to `Team.champion_points`, update the help text to describe the champion
      bonus, and remove `Team.odds_category` and `Team.ODDS_CATEGORY_CHOICES`
- [x] Data migration deriving `champion_points` from `odds_category` (`A` → 20, `B` → 30, blank → 0)
      **before** the column is dropped
- [x] Update `TeamAdmin` to `list_display`/`list_editable` on `champion_points`, remove the
      `odds_category` filter
- [x] Replace `ScoringService.ROUND_MULTIPLIERS`, `VALID_ROUNDS` and `_get_round_multiplier()` with
      `match.round.multiplier`
- [x] Replace the hardcoded joker factor with `match.round.joker_multiplier`
- [x] Replace `champion_scoring.CHAMPION_POINTS` and `calculate_champion_points()` with
      `team.champion_points`
- [x] Replace `Match.objects.filter(round="final")` with `round__is_final=True` in
      `scoring/champion_scoring.py`, `scoring/signals.py` and
      `scoring/management/commands/repair_scoring.py`
- [x] Replace `PredictionLimitService.JOKER_LIMITS` and `COMBINED_ROUNDS` with `round.joker_count`
      and `Round.effective_joker_pool`; `get_joker_count_for_round` counts across all rounds sharing
      the pool
- [x] Replace `GROUP_STAGE_LIMIT` and `can_add_group_stage_prediction()` with
      `round.prediction_limit` and `can_add_prediction(user, round)`
- [x] Replace `LOCK_BUFFER_MINUTES` with `tournament.lock_buffer_minutes` in `is_match_locked()`
- [x] Replace `get_phase_stats()`'s `if phase == "group"` branch with
      `round.prediction_limit or match_count`
- [x] Replace `predictions/views.py`'s `"is_group_stage"` context key with
      `"has_prediction_limit"` and update the templates that consume it
- [x] Replace `ROUND_ORDER` index arithmetic in
      [scoring/ranking_service.py](../../../scoring/ranking_service.py) with `Round.order`
      comparisons
- [x] Replace the hardcoded label dict in
      [users/templatetags/user_tags.py](../../../users/templatetags/user_tags.py) `round_label`
      with a `Round.label` lookup
- [x] Replace the `phaseLabels` JavaScript object in
      [templates/predictions/prediction_list.html](../../../templates/predictions/prediction_list.html)
      with labels passed through the existing `data-phase-stats` context, removing the
      "Achtelfinale (R32)" / "Achtelfinale (R16)" workaround
- [ ] Scope `UserSettingsForm.predicted_champion`'s queryset to teams of the active tournament
      — **not implemented**: `Team` has no tournament relation and design decision 9 states no
      query is scoped by tournament, so `Team.objects.all()` already *is* the active
      tournament's team list. Revisit only if tournaments ever coexist.
- [x] Delete [matches/constants.py](../../../matches/constants.py) and update its importers
      (`predictions/services.py`, `predictions/views.py`, `scoring/ranking_service.py`,
      `users/views.py`)
- [x] Add a "Recalculate scores" admin action on `TournamentAdmin` reusing the
      `recalculate_scores` command logic
- [x] Add a warning on the tournament change form when scored predictions exist, stating that round
      changes require recalculation
- [x] Add a warning on the tournament change form counting teams with `champion_points = 0`
- [x] Update [docs/rules/wm2026-rules.md](../../../docs/rules/wm2026-rules.md) section 8 to describe
      per-team champion points, and resolve open clarification 3 in section 15
- [x] Add decision records to [docs/project/decisions.md](../../../docs/project/decisions.md) for
      configuration-in-database and for replacing the A/B champion categories
- [x] Update [docs/project/architecture.md](../../../docs/project/architecture.md) — the model
      diagram and the constants listing at lines 339–348

**Acceptance criteria:**

- Changing `Round.multiplier` in the admin and running "Recalculate scores" changes
  `User.total_points` accordingly
- Changing `Round.joker_multiplier` to 3 makes a joker prediction in that round worth three times the
  round score
- Setting `Round.prediction_limit` to 10 rejects an eleventh prediction in that round
- Deleting the `3rd` round from a tournament without matches leaves scoring, joker pools and phase
  navigation working, with the `ko_final` pool now covering `sf` and `final` only
- Setting a team's `champion_points` to 45 awards exactly 45 bonus points when it wins
- `grep -rn "ROUND_MULTIPLIERS\|JOKER_LIMITS\|COMBINED_ROUNDS\|GROUP_STAGE_LIMIT\|CHAMPION_POINTS\|ROUND_ORDER\|ROUND_LABELS"` returns no hit in production code
- `round_label` and the phase navigation both render "Sechzehntelfinale" for `r32`
- Running `manage.py recalculate_scores` on the seeded configuration produces identical user
  statistics compared to before this task

**Required tests** (`scoring/tests/test_scoring_service.py`,
`scoring/tests/test_champion_scoring.py`, `predictions/tests/test_services.py`,
`matches/tests/test_tournament_models.py`, `users/tests/test_templatetags.py`):

- `test_round_multiplier_read_from_configuration` — a round with `multiplier=5` scores 5× base
- `test_joker_multiplier_read_from_configuration` — `joker_multiplier=3` triples the round score
- `test_joker_pool_limit_shared_across_pool_members`
- `test_joker_pool_limit_with_third_place_round_absent` — a two-round pool still enforces the limit
- `test_prediction_limit_enforced_per_round`
- `test_round_without_prediction_limit_allows_all_matches`
- `test_lock_buffer_read_from_tournament`
- `test_champion_points_read_from_team`
- `test_champion_points_zero_awards_no_bonus`
- `test_final_identified_by_is_final_flag`
- `test_round_label_r32_is_sechzehntelfinale` — replaces the existing assertion that encodes the bug
- `test_champion_queryset_scoped_to_active_tournament`
- `test_champion_points_backfilled_from_odds_category` — migration test, A → 20, B → 30, blank → 0
- A regression test asserting that the seeded 2026 configuration reproduces the documented worked
  examples from `docs/rules/wm2026-rules.md` sections 1–6

---

## 5. Drive the API sync from the active tournament

**Goal:** `sync_teams` and `sync_matches` use the configured competition code and stage names, and
an unmapped stage fails loudly instead of becoming a group match.

**Scope:** `matches/api_client.py`, `matches/services.py`,
`matches/management/commands/sync_teams.py`, `matches/management/commands/update_matches.py`.

**Out of scope:** Presets (task 6). Any change to the retry, rate-limit or backoff logic.

- [x] Change `FootballDataClient.get_teams()` and `get_matches()` to require an explicit competition
      code instead of defaulting to `"WC"`
- [x] Change `sync_teams_from_api()` and `sync_matches_from_api()` to take a `Tournament` and read
      `api_competition_code` from it
- [x] Replace `API_ROUND_MAP` with a lookup over the tournament's `Round.api_stage` values
- [x] Remove the `API_ROUND_MAP.get(stage_api, "group")` fallback at
      [matches/services.py](../../../matches/services.py) line 217; an unmapped stage raises with a
      message naming the stage and the configured stages
- [x] Replace the `--competition` option on `sync_teams` with `--tournament <slug>`, defaulting to
      the active tournament
- [x] Apply the same option to `update_matches`
- [x] Update [README.md](../../../README.md) sections on `sync_teams` and the `--competition` option

**Acceptance criteria:**

- `manage.py sync_teams` with no arguments syncs the active tournament's competition
- `manage.py sync_teams --tournament em-2028` syncs that tournament's competition
- A match payload with an unrecognised `stage` raises an error naming the stage; no match is created
- A tournament without a round for a returned stage fails the whole sync rather than importing
  partially
- Existing API client tests for retries, rate limits and backoff pass unchanged

**Required tests** (`matches/tests/test_services.py`, `matches/tests/test_api_client.py`,
`matches/tests/test_sync_teams_command.py`, `matches/tests/test_update_matches_command.py`):

- `test_sync_uses_competition_code_from_active_tournament`
- `test_sync_uses_competition_code_from_named_tournament`
- `test_unknown_api_stage_raises_and_creates_no_match`
- `test_stage_mapping_uses_round_api_stage`
- `test_sync_teams_command_defaults_to_active_tournament`
- `test_sync_teams_command_accepts_tournament_option`
- Replace `test_sync_teams_command_default_competition` and
  `test_sync_teams_command_competition_option`, which assert the removed `--competition` option

---

## 6. Add presets, the `create_tournament` command and the switching runbook

**Goal:** A tournament can be created from a preset through the admin, the command line or a test
fixture, all through one code path. Switching tournaments is a documented procedure.

**Scope:** `matches/presets.py`, `matches/tournament.py`,
`matches/management/commands/create_tournament.py`, `matches/admin.py`, `conftest.py`, `README.md`.

**Out of scope:** Any change to scoring, limits or sync behaviour.

- [x] Add `matches/presets.py` with `TOURNAMENT_PRESETS` containing `wm48` (the seven rounds seeded
      in task 2), `wm32` (no round of 32) and `em24` (no round of 32, no third-place match)
- [x] Add `create_tournament(*, name, slug, api_competition_code, api_season=None, preset=None,
      activate=False) -> Tournament` to `matches/tournament.py`, creating the tournament and its
      rounds in one transaction
- [x] `preset=None` creates a tournament with no rounds
- [x] `activate=True` deactivates any currently active tournament first, inside the same transaction
- [x] Add the `create_tournament` management command exposing `--preset`, `--name`, `--slug`,
      `--competition`, `--season` and `--activate`
- [x] Add a preset dropdown to the tournament add form in the admin that pre-fills the round inline
      through the same function
- [x] Add `tournament` and `rounds` pytest fixtures to [conftest.py](../../../conftest.py) built on
      `create_tournament()`, and point `make_match()` at them
- [x] Document the tournament switching runbook in [README.md](../../../README.md): drop and recreate
      the database, `migrate`, `createsuperuser`, `create_tournament --preset ... --activate`,
      `sync_teams`, `sync_matches`, set champion points
- [x] State explicitly in the runbook that switching destroys all predictions, points and rankings,
      and that this is intended
- [x] Verify the `em24` preset's `api_stage` values against the live football-data.org `EC`
      competition, or record in the preset that they are unverified

**Acceptance criteria:**

- `manage.py create_tournament --preset em24 --name "EM 2028" --slug em-2028 --competition EC
  --activate` produces an active tournament with five rounds, no `r32` and no `3rd`
- `manage.py create_tournament --name "Leer" --slug leer` produces a tournament with zero rounds
- Creating a tournament from the `em24` preset in the admin produces rows identical to the command
- `--activate` leaves exactly one active tournament
- The `em24` preset's joker pool contains `sf` and `final` and enforces its limit across both
- Running the full suite against an `em24`-configured database produces no failures caused by a
  missing `r32` or `3rd` round

**Required tests** (`matches/tests/test_create_tournament_command.py`,
`matches/tests/test_tournament_admin.py`):

- `test_create_tournament_from_wm48_preset_creates_seven_rounds`
- `test_create_tournament_from_em24_preset_omits_r32_and_third_place`
- `test_create_tournament_without_preset_creates_no_rounds`
- `test_activate_deactivates_previous_tournament`
- `test_create_tournament_is_atomic` — a failing round spec leaves no tournament behind
- `test_admin_preset_dropdown_produces_same_rounds_as_command`
- `test_scoring_works_on_em24_configuration` — end-to-end: create `em24`, score a final, assert
  champion bonus and joker pool behaviour with no third-place round present
