# System Architecture

> Verified reference document. Every claim below was checked against this repository's
> source code (models, views, urls, signals, templates, settings, management commands)
> on 2026-09-16; the tournament-configuration and email-notification claims were
> re-verified on 2026-10-23 against the `configurable-tournament` and `email-init`
> changes. File paths are exact.

## 1. One-sentence summary

`django-tipapp` is a private tipping game for one football tournament at a time —
currently the 2026 World Cup: logged-in users predict match scores, use a limited number
of jokers, pick a champion, and compare points on a leaderboard. The tournament format
(rounds, multipliers, jokers, limits) is data in the database, not code. Django renders
pages server-side; HTMX refreshes small HTML fragments without full page reloads.

## 2. What the app currently offers

- Login, logout, password reset (Django auth views)
- Per-user settings: username, email, theme, champion pick
- Chronological match list with client-side phase filtering
- Prediction and joker limits per round, read from the tournament configuration
  (the seeded 2026 setup: 36 group-stage predictions, jokers in the knockout rounds)
- Autosave of predictions, a dedicated "all predictions for this match" page
- Live-ish updates of match rows and leaderboard via HTMX polling
- Automatic result import from football-data.org
- Automatic scoring and Olympic-style ranking
- Programmable tournament: rounds, multipliers, joker counts/pools, prediction limits,
  lock buffer and champion bonus points are editable in the admin; new tournaments are
  created from a preset via `python manage.py create_tournament` or the admin add form
  (see the runbook in [README.md](../../README.md))
- Django admin, staff-only CSV leaderboard export
- Outgoing email: password reset (Django auth), a daily leaderboard report to the admin
  address and daily reminders to users with missing predictions, sent by the
  `notification_daemon` management command (see §12.2)

Not yet implemented (present only as product-boundary goals in
[.github/copilot-instructions.md](../../.github/copilot-instructions.md)):
- A forum/discussion feature for tippers
- In-app notifications: the `notifications` app
  ([notifications/](../../notifications/)) is registered in `INSTALLED_APPS` but is
  service-only — `models.py`, `views.py` and `admin.py` are empty stubs, there are no
  migrations and no URLs. It sends email; it does not store or display notifications.

## 3. Mental model

Four independent flows:

1. **Browser ↔ Django.** Loads pages, saves predictions, polls for HTML fragments.
2. **Background process ↔ football-data.org.** `update_matches` management command
   fetches scores and writes them to PostgreSQL.
3. **Signal-driven scoring.** A changed match result triggers scoring and ranking
   recalculation.
4. **Background process ↔ SMTP.** `notification_daemon` reads the database on a schedule
   and sends leaderboard reports and prediction reminders by email. It never writes
   domain data.

```mermaid
flowchart TD
    B["Browser: Templates + HTMX"] -->|GET / POST| D["Django monolith"]
    D --> P[(PostgreSQL)]
    U["update_matches command"] -->|API GET| F["football-data.org"]
    U -->|Match.save| P
    U --> S["match_result_entered signal"]
    S --> P
    N["notification_daemon command"] -->|read| P
    N -->|send_mail| M["SMTP server"]
```

The browser's HTMX polling never calls football-data.org directly — it only reads the
current state from PostgreSQL via Django views.

## 4. Why this architecture

| Decision | Why it fits here |
|---|---|
| Django monolith | Low operational overhead for a hobby-scale app (~50-100 users) |
| PostgreSQL | Relational model fits users/matches/predictions/teams naturally |
| Django templates | No separate frontend project, no duplicated API/UI logic |
| HTMX | Interactive UI without a JS framework or bespoke JSON API |
| Tailwind via CDN | `templates/base.html` loads `cdn.tailwindcss.com` directly; `static/` is empty — there is no production Tailwind build step today |
| Separate management command for sync | API calls don't block web request/response cycle |
| Tournament format as data (`Tournament`/`Round` rows, presets as defaults) | A new tournament is a configuration change, not a code change; no round codes or point factors are hardcoded |
| Django signals (`match_result_entered`) | Small, event-based coupling between `matches` and `scoring` (see [docs/project/decisions.md](decisions.md)) |
| Cached `total_points` / `global_rank` on `User` | Leaderboard reads become cheap; see the 2026-08-24 decision in [decisions.md](decisions.md) |

This is a reasonable fit for the current scale. WebSockets, Celery, Redis, or a
microservice split are not warranted without a measured, concrete bottleneck (also see
`.github/copilot-instructions.md`, which explicitly disallows introducing them without an
OpenSpec-documented reason).

## 5. Module breakdown

```text
tipapp/         Project root: URLs, settings, HomeView, RankingUpdatesView
core/           Shared ranking algorithm (Olympic-style tie handling)
users/          Custom User model, settings/rules views, forms
matches/        Tournament/Round/Team/Match models, round presets, tournament factory,
                football-data.org client, sync + create_tournament commands, signals
predictions/    MatchPrediction model, limit/lock service, HTMX views, forms
scoring/        Scoring formulas, champion bonus, ranking service, signals, CSV export
notifications/  EmailService + notification_daemon/test_email commands, email templates;
                no models, no views, no URLs
templates/      Full pages + reusable partials (predictions row is shared between pages)
```

Tournament configuration lives in `matches`:
[matches/presets.py](../../matches/presets.py) holds the round presets (`wm48`, `wm32`,
`em24`) as frozen `RoundSpec` dataclasses, and
[matches/tournament.py](../../matches/tournament.py) is the single factory
(`create_tournament()`, `create_rounds_from_preset()`) plus the single accessor
(`get_active_tournament()`). Admin, management command and test fixtures all go through
it, so a configuration cannot differ depending on where it was created.

The split follows domain boundaries, not technical layers — each app owns its models,
forms, views, URLs, and services.

## 6. Data model

```mermaid
erDiagram
    TOURNAMENT ||--o{ ROUND : defines
    ROUND ||--o{ MATCH : groups
    USER ||--o{ MATCH_PREDICTION : submits
    TEAM ||--o{ MATCH : home_team
    TEAM ||--o{ MATCH : away_team
    MATCH ||--o{ MATCH_PREDICTION : has
    TEAM ||--o{ USER : predicted_champion
    LEADERBOARD_SNAPSHOT }o--|| USER : "JSON copy only, no FK"
```

### `users.User` ([users/models.py](../../users/models.py))

Extends `AbstractUser`. Cached/denormalized ranking fields:

```python
predicted_champion: models.ForeignKey  # matches.Team, nullable
total_points: models.IntegerField      # includes champion bonus
exact_match_count: models.IntegerField
jokers_used: models.IntegerField
champion_bonus_points: models.IntegerField  # copy of the champion team's Team.champion_points
global_rank: models.IntegerField       # nullable, indexed, Olympic-style
theme_preference: models.CharField     # light/dark/system
```

`total_points`, `exact_match_count`, `jokers_used`, `champion_bonus_points`, and
`global_rank` are denormalizations updated by services/signals, not computed on read.

### `matches.Tournament` / `matches.Round` ([matches/models.py](../../matches/models.py))

`Tournament` holds the installation-wide settings: `name`, `slug`, `api_competition_code`,
`api_season`, `lock_buffer_minutes` and `is_active`. A partial unique index allows exactly one
active tournament; `matches/tournament.py::get_active_tournament()` is the only accessor and
raises when none is configured.

`Round` holds every per-round parameter: `code`, `label`, `order`, `multiplier`, `joker_count`,
`joker_multiplier`, `joker_pool`, `prediction_limit`, `is_final` and `api_stage`. Rounds belong
to one tournament and are unique per tournament by `code`, `order` and `api_stage`, with at most
one `is_final`. "Which rounds exist" is a query, not a constant.

Switching tournaments is an operational procedure that drops the database (see the README
runbook), so no query is scoped by tournament.

Rounds are created either from a preset in [matches/presets.py](../../matches/presets.py)
(`wm48`, `wm32`, `em24`) or by hand in the admin inline. The admin enforces the
configuration rules that a single row cannot express
([matches/admin.py](../../matches/admin.py), `RoundInlineFormSet.clean()`): exactly one
round is the final, `code`/`order`/`api_stage` are unique within the tournament, and all
rounds sharing a `joker_pool` must declare the same `joker_count`.

### `matches.Team` / `matches.Match` ([matches/models.py](../../matches/models.py))

`Team` has `fifa_code` and `champion_points` (the bonus a user receives for picking this team as
champion; `0` awards nothing). `Match` stores `external_id` (football-data.org ID),
`kickoff`, `round` (a `ForeignKey` to `Round` with `on_delete=PROTECT`),
`goals_home`/`goals_away`, `winner` (needed separately from goals —
knockout matches can be 1:1 after 120 minutes but have a penalty-shootout winner), and
`status` (`scheduled`/`live`/`finished`).

`Match.save()` only compares `goals_home`/`goals_away` against the previous DB values; if
either changed and both are non-null, it fires `match_result_entered`. **It does not
compare `winner` or `status`** — see Known Issues §5.

### `predictions.MatchPrediction` ([predictions/models.py](../../predictions/models.py))

One row per `(user, match)` via `unique_together`. Holds the prediction, `joker_active`,
and the scoring outputs `points_earned` / `is_exact_match` populated by
`ScoringService`.

### `scoring.LeaderboardSnapshot` ([scoring/models.py](../../scoring/models.py))

Stores a historical ranking as JSON (`data` field) rather than FKs, so a snapshot stays
readable even if users are later modified or deleted.

## 7. URL routing

[tipapp/urls.py](../../tipapp/urls.py):

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", HomeView.as_view(), name="home"),
    path("login/", auth_views.LoginView.as_view(...), name="login"),
    path("logout/", auth_views.LogoutView.as_view(...), name="logout"),
    path("ranking/", RedirectView.as_view(url="/", permanent=False), name="ranking"),  # legacy URL kept working
    path("predictions/", include("predictions.urls")),
    path("scoring/", include("scoring.urls")),
    path("", include("users.urls")),
    # password-reset/*, password-reset-confirm/*, password-reset-complete/
]
```

[predictions/urls.py](../../predictions/urls.py) (`app_name = "predictions"`):

| Path | View | Name |
|---|---|---|
| `/predictions/` | `PredictionListView` | `prediction-list` |
| `/predictions/updates/` | `PredictionUpdatesView` | `prediction-updates` |
| `/predictions/phase-stats/` | `PhaseStatsView` | `phase-stats` |
| `/predictions/match/<id>/all/` | `MatchPredictionsView` | `match-predictions` |
| `/predictions/match/<id>/updates/` | `MatchPredictionsUpdateView` | `match-predictions-updates` |
| `/predictions/<id>/save/` | `PredictionSaveView` | `prediction-save` |
| `/predictions/<id>/delete/` | `PredictionDeleteView` | `prediction-delete` |
| `/predictions/<id>/joker/` | `PredictionJokerView` | `prediction-joker` |

[scoring/urls.py](../../scoring/urls.py) (`app_name = "scoring"`):

| Path | View | Name |
|---|---|---|
| `/scoring/ranking-updates/` | `RankingUpdatesView` (defined in `tipapp/views.py`) | `ranking-updates` |
| `/scoring/admin/download-leaderboard/` | `DownloadLeaderboardView` (staff-only) | `download-leaderboard` |

[users/urls.py](../../users/urls.py) (`app_name = "users"`):

| Path | View | Name |
|---|---|---|
| `/rules/` | `RulesView` | `rules` |
| `/settings/` | `UserSettingsView` | `settings` |

Note: `RankingView` (full/HTMX-partial ranking page, `templates/ranking.html`) lives in
[users/views.py](../../users/views.py) but is not currently wired into `users/urls.py` —
the home page (`HomeView`) is the primary ranking surface today via
`_get_ranking_context()` in [tipapp/views.py](../../tipapp/views.py).

Standard flow: `URL → View → Form/Service → Context → Template → HTML`. HTMX requests
follow the same path; only the template returned is a smaller fragment.

## 8. Page-by-page walkthrough

### 8.1 Login / logout / password reset
Standard Django auth views (see `tipapp/urls.py`), templates in `templates/registration/`
and `templates/login.html`. Other pages use `LoginRequiredMixin`. Password-reset mails use
the configured Django email backend (§12.2).

### 8.2 Home (`/`) — `tipapp.views.HomeView`
Combines: personal rank card, ranking (compact + full via
`_get_ranking_context()`), and the next 3 upcoming matches
(`Match.objects.filter(kickoff__gt=now).order_by("kickoff")[:3]`). Match rows reuse
`templates/predictions/prediction_row.html` via `{% include %}` — a single source of
truth for the prediction UI.

Ranking polling on home:
```html
<div hx-get="{% url 'scoring:ranking-updates' %}..." hx-trigger="every {{ ranking_interval }}s" hx-swap="none"></div>
```
The poller element itself is not swapped; the response uses OOB fragments (see §9) to
update `#compact-ranking` and `#ranking-content` in one round trip. **The 3 upcoming
match cards on home are not covered by any poller** — see Known Issue §9.

### 8.3 "My predictions" (`/predictions/`) — `PredictionListView`
Loads all matches + the user's predictions in two queries, builds a `prediction_map`
keyed by match ID to avoid N+1 lookups, groups by date. Phase filtering
(group/r32/.../final) is done client-side via `data-match-stage` attributes — no server
round-trip on filter change. `PhaseStatsView` (`/predictions/phase-stats/`) returns JSON
used to refresh the progress/joker counters after a save/delete/joker toggle.

Live polling:
```html
<div hx-get="{% url 'predictions:prediction-updates' %}" hx-trigger="load, every {{ polling_interval }}s" hx-swap="none"></div>
```
`get_polling_interval()` in [predictions/services.py](../../predictions/services.py) returns 15s
if any match is within its active window (kickoff to kickoff+160min), else 60s. The
server can push a new interval via the `HX-Trigger: {"pollingInterval": ...}` response
header, and client JS in `prediction_list.html` updates the `hx-trigger` attribute
accordingly.

### 8.4 The prediction row — `templates/predictions/prediction_row.html`
The reusable component. `id="match-{{ match.id }}"` is the stable anchor used both for
normal `hx-target`/`outerHTML` swaps (on save/delete/joker) and for OOB updates from the
polling endpoints. `PredictionSaveView.post()` (and delete/joker equivalents) always
re-render this same partial from freshly saved DB state after mutating.

### 8.5 "All predictions for a match" (`/predictions/match/<id>/all/`) — `MatchPredictionsView`
Shows the match, the current user's own form (rendered *outside* the polling
container so an in-flight poll response cannot clobber values while typing), and all
users' predictions/points, sortable by match points or total points via
`build_match_predictions_list()`.

Polling here uses a version string built from `f"{goals_home}:{goals_away}"`
(`MatchPredictionsUpdateView`). If the match is locked **and** the client's version
matches the server's, it returns an empty `HttpResponse("")` — paired with
`hx-swap="innerHTML"` on `#predictions-content`
([templates/predictions/match_predictions_page.html](../../templates/predictions/match_predictions_page.html)),
this can blank the panel on a stray/duplicate poll. See Known Issue §1.

### 8.6 Settings (`/settings/`) — `UserSettingsView` / `UserSettingsForm`
`UpdateView` always operating on `request.user`. `can_change_champion()` checks whether
`timezone.now()` is before the first match's kickoff and is the single source of truth for the
lock: the view passes `champion_locked = not can_change_champion()` into the form via
`get_form_kwargs()`, and [users/forms.py](../../users/forms.py) removes `predicted_champion`
from `form.fields` when locked. A posted champion value is therefore never bound, validated or
written once the tournament has started, and an unrelated settings save cannot clear the pick.
The template renders the editable widget only when the form still exposes the field.

### 8.7 Rules (`/rules/`) — `RulesView`
Plain `TemplateView`; collapsible sections are pure client-side JS, no HTMX involved.

### 8.8 Admin & export
Django admin at `/admin/`. `/scoring/admin/download-leaderboard/` —
`DownloadLeaderboardView`, decorated with `staff_member_required`, streams CSV via
`scoring/exports.py`.

**Matches → Tournaments** is the configuration surface
([matches/admin.py](../../matches/admin.py)):
- The *add* form offers a `preset` dropdown and hides the round inline; the rounds are
  created by `create_rounds_from_preset()` in `save_model()`.
- The *change* form shows the round inline and warns when predictions are already scored
  (round changes then require the "Recalculate scores" action) and when teams still have
  `champion_points = 0`.
- The admin action "Recalculate scores for all finished matches" runs
  `recalculate_all_scores()`; the same work is available as
  `python manage.py recalculate_scores`.

## 9. Prediction write flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant V as PredictionSaveView
    participant L as PredictionLimitService
    participant DB as PostgreSQL
    B->>V: POST goals + CSRF
    V->>L: is_match_locked? can_add_group_stage_prediction?
    L->>DB: read match / prediction counts
    V->>DB: save prediction
    V-->>B: prediction_row.html (rendered from DB)
```

Server re-validates every rule on every request — a disabled HTML field is not a
security boundary since a user can craft the request directly.

## 10. HTMX pattern reference

| Attribute | Purpose | Where used |
|---|---|---|
| `hx-get` | Trigger polling / filters | ranking updates, prediction updates, match-detail updates |
| `hx-post` | Save/delete/joker toggle | `prediction_row.html` forms |
| `hx-trigger` | `load`, `input delay:500ms`, `every Ns` | autosave, polling |
| `hx-target` / `hx-swap` | `outerHTML` on the row's own save, `innerHTML` on list containers, `none` on invisible pollers | see below |
| `hx-swap-oob` | Update elements outside the response's own target in the same response | ranking (`#compact-ranking`, `#ranking-content`), multiple `#match-<id>` rows at once |

**OOB in this codebase**: the poller div uses `hx-swap="none"` (it must not disappear),
while the *response body* contains one or more elements with
`hx-swap-oob="innerHTML"`/`"true"` whose `id` matches an existing DOM node
(`templates/partials/ranking_updates.html`, `PredictionUpdatesView` in
`predictions/views.py`). HTMX applies all of them from a single HTTP response — this is
not a second request, it's "swap somewhere other than the original target."

**Known duplicate-trigger risk**: `prediction_row.html` inputs carry
`hx-trigger="input delay:500ms"` (fires the inherited `hx-post` directly), while
`templates/base.html` *also* has a global debounced listener that calls
`htmx.trigger(form, 'submit')` after its own 500ms. Both can fire a save request from a
single keystroke sequence. See Known Issue §7.

### Active poller inventory

| Page | Endpoint | Interval | Swap | Updates |
|---|---|---|---|---|
| Home | `/scoring/ranking-updates/` | fixed at page load (15s or 60s via `get_polling_interval()`) | `none` + OOB | compact + full ranking |
| Prediction list | `/predictions/updates/` | dynamic 15s/60s, adjusted live via `HX-Trigger` | `none` + OOB | active-window match rows (excludes `status="finished"`, see Known Issue §2) |
| Match detail | `/predictions/match/<id>/updates/` | fixed at page load | `innerHTML` | full predictions list for that match |

Only the prediction list dynamically re-adjusts its interval while the page stays open;
home and match-detail keep their initial interval.

## 11. Scoring and ranking

### Scoring formula ([scoring/match_scoring.py](../../scoring/match_scoring.py))

Precedence order (first match wins):

| Match type | Base points |
|---|---|
| Exact score | 6 |
| Tendency + goal difference | 5 |
| Tendency + one team's goals | 4 |
| Tendency only | 3 |
| One team's goals only | 1 |
| No match | 0 |

```python
final_points = base_points * match.round.multiplier * (
    match.round.joker_multiplier if joker_active else 1
)
```

The seeded 2026 configuration uses multipliers `group=1`, `r32=2`, `r16=2`, `qf=3`, `sf=3`,
`3rd=3`, `final=3` and `joker_multiplier=2` throughout. All of them are editable in the admin.

### Joker and prediction limits ([predictions/services.py](../../predictions/services.py))

Every limit is read from the `Round` of the match:

| Value | Source |
|---|---|
| Jokers per round | `Round.joker_count` |
| Shared joker pools | `Round.joker_pool` (rounds with the same non-empty key share one limit) |
| Joker factor | `Round.joker_multiplier` |
| Predictions per round | `Round.prediction_limit` (`NULL` means unlimited) |
| Lock buffer | `Tournament.lock_buffer_minutes` |

The seeded 2026 configuration sets joker counts `0/3/3/2/2/2/2`, pool `ko_final` over
`sf`/`3rd`/`final`, `prediction_limit=36` on the group stage and a lock buffer of 3 minutes.

### Champion bonus ([scoring/champion_scoring.py](../../scoring/champion_scoring.py))

The final is the round with `is_final=True`, not a hardcoded round code. The bonus a user
receives is `Team.champion_points` of the current champion (`0` awards nothing), so the
bonus table is data, not code. `update_live_champion_bonuses()` resets every stored bonus
first and re-awards from the current state of the final, which keeps the value correct
while the final is still live.

### Changing the configuration after matches were scored

`Round.multiplier`, `Round.joker_multiplier`, `Round.is_final` and `Team.champion_points`
are read at scoring time only. Editing them does not rewrite already-stored
`MatchPrediction.points_earned`; run the admin action "Recalculate scores for all finished
matches" or `python manage.py recalculate_scores` afterwards. The tournament change form
warns about this.

### Trigger: `Match.save()` → `match_result_entered` signal

[matches/signals.py](../../matches/signals.py) defines the signal;
[scoring/signals.py](../../scoring/signals.py) receives it and, in order:

1. `ScoringService.score_all_predictions_for_match(match)`
2. If `match.round.is_final`: `update_live_champion_bonuses()`
3. `RankingService.update_all_user_ranks()`

All three calls are wrapped in one `try/except Exception: logger.exception(...)` — an
error anywhere in this chain is logged but never surfaced or retried. See Known Issue §6.

### Incremental updates, not re-additions

`ScoringService` computes a point delta versus the previously stored score and applies it
with `F()` expressions, so correcting a result doesn't double-count previously awarded
points.

### Olympic ranking ([core/ranking.py](../../core/ranking.py))

`apply_olympic_ranking()` is the single shared algorithm used by both the leaderboard
and the match-detail predictions list: equal-ranked items share a rank number, and the
next distinct rank skips ahead (`1, 2, 2, 4`). `RankingService.update_all_user_ranks()`
persists the result to `User.global_rank` (see the 2026-08-24 entry in
[decisions.md](decisions.md) for why this is cached rather than computed per request).

## 12. Background processes

### 12.1 Result import

`python manage.py update_matches`
([matches/management/commands/update_matches.py](../../matches/management/commands/update_matches.py))
runs as a long-lived, separate process with adaptive sleep:

| Condition | Interval |
|---|---|
| Any match `status == "live"` | 10s |
| Match within kickoff −3h to +30min, status scheduled/live | 30s |
| Next scheduled match starts in < 30 min | 60s |
| Next scheduled match starts in < 2h | 5 min |
| Next scheduled match later than that | 10 min |
| No upcoming scheduled match | 30 min |

[matches/api_client.py](../../matches/api_client.py) sends the API key via the
`X-Auth-Token` header, respects `Retry-After` on HTTP 429, and uses exponential backoff
on 5xx responses. `sync_matches_from_api()` uses `Match.objects.update_or_create(external_id=...)`,
so `Match.save()` (and therefore the scoring signal) fires naturally whenever goals
change during import — no manual scoring call is needed in the command itself.

#### Tournament scoping of the sync

Both `update_matches` and `sync_teams` work on the active tournament
(`get_active_tournament()`) and accept `--tournament=<slug>` to target another one. The
competition requested from the API is `Tournament.api_competition_code` (plus
`api_season` where required) — no competition code is hardcoded.

The API `stage` of a match is resolved against `Round.api_stage` of that tournament
(`rounds_by_stage` in [matches/services.py](../../matches/services.py)). A stage that maps
to no round raises `UnknownApiStageError` and **aborts** the whole sync instead of
guessing a round; every other per-match failure is logged and skipped so the remaining
matches still import.

### 12.2 Email notifications

`python manage.py notification_daemon`
([notifications/management/commands/notification_daemon.py](../../notifications/management/commands/notification_daemon.py))
is the second long-lived process, built like `update_matches`: graceful SIGTERM/SIGINT
shutdown, `--once` for testing, a broad `except` so the loop survives an iteration
failure. It checks every `--interval` seconds (default 3600) and sends at most one of
each mail per calendar day:

| Flag | Default | Sends |
|---|---|---|
| `--leaderboard-hour` | 20 | Leaderboard report to `LEADERBOARD_ADMIN_EMAIL` |
| `--reminder-hour` | 10 | Prediction reminder to every user with missing predictions |

"At most once per day" is tracked in memory (`last_leaderboard_date`,
`last_reminder_date`), not in the database — a restart can therefore re-send a mail that
was already sent the same day, and the trigger is `current_hour >= configured_hour`, so a
daemon started late in the day sends immediately.

Both mails are built in `EmailService`
([notifications/services.py](../../notifications/services.py)) and rendered from
`notifications/templates/notifications/emails/` (HTML + plain-text variant each, sent
together via `send_mail(..., html_message=...)`):

- `send_leaderboard_to_admin()` takes the **newest `LeaderboardSnapshot`** — not the live
  ranking — enriches every entry with that user's predictions, and mails it to
  `LEADERBOARD_ADMIN_EMAIL`. Without a snapshot
  (`python manage.py create_snapshot`) or without that setting it returns
  `(False, reason)` and sends nothing.
- `get_users_with_missing_predictions()` collects matches with kickoff in the next 24h and
  `status="scheduled"`, then maps each active non-staff user to the matches they have not
  predicted. `send_prediction_reminder()` skips users without an email address.

Sending never raises into the caller: `SMTPException`, `OSError` and
`TemplateDoesNotExist` are caught, logged and returned as `(False, message)`. There is no
retry and no delivery log — a failed mail is only visible in the logs, and the next
attempt is the next scheduled run.

Configuration is environment-driven ([tipapp/settings/base.py](../../tipapp/settings/base.py)):
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `LEADERBOARD_ADMIN_EMAIL`. The backend depends on
the settings module: development defaults to the console backend and honours an `EMAIL_BACKEND`
override, tests use `locmem`, production falls back to Django's default SMTP backend
(`EMAIL_BACKEND` is read in `development.py` only). Verify a real SMTP setup with
`python manage.py test_email --leaderboard` or
`python manage.py test_email --reminder=<username>`.

Password-reset mails go through the same Django email backend but are sent by the auth
views, not by the daemon.

## 13. Where do I change what

| Task | Primary files |
|---|---|
| Add a URL | `tipapp/urls.py` or `<app>/urls.py` |
| Round config (multiplier, jokers, limits, final flag) | Django admin → Tournaments, or `matches/presets.py` for a new tournament |
| Add a tournament format preset | `matches/presets.py` |
| Tournament creation / active-tournament lookup | `matches/tournament.py`, `matches/management/commands/create_tournament.py` |
| Change the prediction row UI | `templates/predictions/prediction_row.html` |
| Save/delete a prediction | `predictions/views.py` |
| Lock / joker / prediction-limit *logic* (the values are data) | `predictions/services.py` |
| Polling interval, phase stats, match prediction list | `predictions/services.py` |
| Input validation | `predictions/forms.py` |
| Scoring formula | `scoring/match_scoring.py` |
| Champion bonus | `scoring/champion_scoring.py` (logic), `Team.champion_points` (values) |
| Ranking algorithm | `core/ranking.py`, `scoring/ranking_service.py` |
| Result import | `matches/api_client.py`, `matches/services.py` |
| Email content/recipients | `notifications/services.py`, `notifications/templates/notifications/emails/` |
| Email schedule | `notifications/management/commands/notification_daemon.py` (flags) |
| SMTP / sender / admin address | environment variables read in `tipapp/settings/base.py` |
| API polling intervals | `matches/management/commands/update_matches.py` |
| Browser polling intervals/targets | `predictions/services.py`, `predictions/views.py`, `tipapp/views.py`, corresponding templates |
| Home page | `tipapp/views.py`, `templates/home.html` |
| User profile/settings | `users/forms.py`, `users/views.py`, `templates/users/settings.html` |
| Global nav/JS (incl. autosave) | `templates/base.html` |
| Data model | app's `models.py` + migration |

## 14. Debugging checklist

**A UI region doesn't refresh**
1. Does the target element have a stable, unique `id`?
2. Does `hx-target` point at that `id`?
3. Does the endpoint return a full element (`outerHTML`) or just its contents (`innerHTML`)?
4. Does an OOB fragment share the exact `id` of the existing DOM node?
5. Is the poller element still in the DOM (not accidentally replaced)?
6. Does the network tab show an error or an unexpectedly empty 200?

**A prediction won't save**
1. Is the user authenticated?
2. Is the CSRF token present?
3. Is `timezone.now()` already within `Tournament.lock_buffer_minutes` of kickoff
   (3 minutes in the seeded 2026 configuration)?
4. Is the round's `prediction_limit` (36 for the seeded group stage) or its
   `joker_count` — shared across the `joker_pool` — already reached?
5. Are both goal fields present in the POST body?
6. What does `PredictionForm` validation say (goals must be 0–20, see
   `predictions/forms.py` — templates historically mentioned 99, verify current copy)?

**The app or a command errors out on startup / sync**
1. Is exactly one `Tournament` marked `is_active`? `get_active_tournament()` raises
   `NoActiveTournamentError` when none is.
2. Does the tournament have rounds, and exactly one with `is_final=True`?
3. Does every API stage the competition reports map to a `Round.api_stage`? An unmapped
   stage aborts `update_matches` with `UnknownApiStageError`.
4. Is `Tournament.api_competition_code` (and `api_season`, if needed) the one you expect?

**Points or rank look wrong**
1. Does the match have both goals saved?
2. Did `match_result_entered` actually fire (check logs for scoring/signals exceptions)?
3. Does the prediction have `points_earned` and `is_exact_match` set?
4. Was the round configuration (multiplier, joker multiplier, `is_final`) or
   `Team.champion_points` changed after scoring? Then run `recalculate_scores`.
5. Do `User.total_points` and `champion_bonus_points` look consistent?
6. Was `RankingService.update_all_user_ranks()` executed afterward?
7. Are you looking at the cached global ranking or a round-filtered (dynamic) view?

**No email arrives**
1. Which backend is active? Development defaults to the console backend (overridable with
   `EMAIL_BACKEND`) and tests use `locmem` — neither sends real mail. Production uses
   Django's default SMTP backend.
2. Are `EMAIL_HOST`/`EMAIL_PORT`/credentials and `DEFAULT_FROM_EMAIL` set in the
   environment? Test with `python manage.py test_email --leaderboard`.
3. Leaderboard mail only: is `LEADERBOARD_ADMIN_EMAIL` set and does a
   `LeaderboardSnapshot` exist (`python manage.py create_snapshot`)?
4. Reminder only: does the user have an email address, is the user active and non-staff,
   and is there a `scheduled` match within the next 24 hours they have not predicted?
5. Is `notification_daemon` running, and has its hour (`--reminder-hour`,
   `--leaderboard-hour`) already passed today in the server's timezone?
6. Check the logs — send failures are logged and swallowed, never retried.

## 15. Known issues (verified against this codebase, prioritized)

### Priority 1 — correctness

1. **Match-detail page can render empty.** `MatchPredictionsUpdateView` returns
   `HttpResponse("")` when locked and the version is unchanged; combined with
   `hx-swap="innerHTML"` on `#predictions-content`, a stray/duplicate poll can blank the
   panel. Fix options: always render, or return `HttpResponse(status=204)` instead of a
   200 with empty body. — [predictions/views.py](../../predictions/views.py)
2. **Finished match may not reach an open prediction list.** `PredictionUpdatesView`
   excludes `status="finished"` from the matches it refreshes; if a match's final goal
   and `finished` status land in the same update, an already-open list may show a stale
   score. — [predictions/views.py](../../predictions/views.py)
3. **~~Champion lock is UI-only.~~ RESOLVED** (change `enforce-champion-lock-server-side`).
   `UserSettingsView.get_form_kwargs()` passes `champion_locked` into `UserSettingsForm`, which
   removes `predicted_champion` from its fields once the first match has kicked off. A direct POST
   to `/settings/` after the tournament start can neither replace nor clear the pick. —
   [users/views.py](../../users/views.py), [users/forms.py](../../users/forms.py)
4. **~~36-prediction group limit is effectively 35.~~ RESOLVED** (change
   `fix-prediction-correctness-bugs`). `PredictionSaveView.post()` looks up an existing
   prediction first and checks `PredictionLimitService.can_add_prediction()` *before* creating a
   new row in a limited round, inside `transaction.atomic()`. With the seeded group-stage limit
   of 36 the 36th prediction is accepted, the 37th is rejected with the error partial and
   without creating a row. — [predictions/views.py](../../predictions/views.py)
5. **~~Winner/status-only change doesn't re-trigger scoring.~~ RESOLVED** (change
   `fix-prediction-correctness-bugs`). `Match.save()` compares all
   `Match.SCORING_RELEVANT_FIELDS` (`goals_home`, `goals_away`, `winner`, `status`) and sends
   `match_result_entered` when any of them changed while both goals are set. Saves that only touch
   unrelated fields still send nothing. — [matches/models.py](../../matches/models.py)
6. **~~Scoring errors are swallowed.~~ RESOLVED** (change `fix-prediction-correctness-bugs`).
   The signal receiver runs scoring, champion bonus and rank update in one
   `transaction.atomic()` block, logs failures with the match id and re-raises them, so a
   failure never leaves partially scored state. `sync_matches_from_api()` isolates each match,
   so one bad match is logged and skipped while the loop continues. Leftover damage is detected
   and fixed with `python manage.py repair_scoring --check` / `python manage.py repair_scoring`
   (idempotent, non-zero exit when work remains). — [scoring/signals.py](../../scoring/signals.py),
   [matches/services.py](../../matches/services.py),
   [scoring/management/commands/repair_scoring.py](../../scoring/management/commands/repair_scoring.py)

### Priority 2 — HTMX/consistency

7. **Duplicate autosave.** Inputs use `hx-trigger="input delay:500ms"` while
   `templates/base.html` independently debounces and calls
   `htmx.trigger(form, 'submit')`, risking multiple POSTs per edit. —
   [templates/predictions/prediction_row.html](../../templates/predictions/prediction_row.html),
   [templates/base.html](../../templates/base.html)
8. **Match-detail version key is narrow.** The version string is only
   `goals_home:goals_away`; status/winner/points/rank/champion-bonus changes aren't
   reflected in it, so those updates might not be pushed. —
   [predictions/views.py](../../predictions/views.py)
9. **Home page match cards aren't live.** Only the ranking is polled on `/`; the three
   upcoming-match cards can show a stale score or lock state until reload. —
   [templates/home.html](../../templates/home.html)
10. **Only one page adapts its polling interval live.** The prediction list updates its
    own `hx-trigger` interval via `HX-Trigger`; home and match-detail keep whatever
    interval was set at initial page load.

### Priority 3 — robustness / maintenance

11. **API stage mapping is configuration, so it must be verified per tournament.** Stage
    names come from `Round.api_stage`; an unmapped stage aborts the sync
    (`UnknownApiStageError`) instead of silently falling back, but the `em24` preset's
    stage names are explicitly unverified against the live football-data.org EC
    competition (see the comment in [matches/presets.py](../../matches/presets.py)).
    Status mapping (`API_STATUS_MAP`) still falls back to `scheduled` on unknown values. —
    [matches/services.py](../../matches/services.py)
12. **Repeated per-row limit/count queries** in `PredictionListView`/`_get_match_row_context`
    could be precomputed once per phase if this becomes a measured bottleneck (not
    currently a known problem at this scale).
13. **Match-detail totals only sum `MatchPrediction.points_earned`**, so champion bonus
    (stored on `User.total_points`) is not reflected in the per-match "total points"
    column. — `build_match_predictions_list()` in [predictions/services.py](../../predictions/services.py)
14. **Settings module can default to development in production.**
    `tipapp/wsgi.py` sets `DJANGO_SETTINGS_MODULE=tipapp.settings`, and
    `tipapp/settings/__init__.py` falls back to `development` settings whenever that
    module name is used unchanged; additionally
    `SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-key-change-in-production")`
    in `tipapp/settings/base.py` has an insecure fallback instead of failing hard when
    unset. **Security-relevant**: verify the deployment target always sets
    `DJANGO_SETTINGS_MODULE=tipapp.settings.production` and a real `SECRET_KEY`. —
    [tipapp/wsgi.py](../../tipapp/wsgi.py), [tipapp/settings/__init__.py](../../tipapp/settings/__init__.py),
    [tipapp/settings/base.py](../../tipapp/settings/base.py)
15. **Validation copy should be double-checked** against the actual `MaxValueValidator`
    bounds in `predictions/forms.py` (source doc mentioned a 99 vs. 20 mismatch — re-verify
    current form/template copy stays in sync whenever goal bounds change).
16. **Dependency reproducibility**: `pyproject.toml` lists `requests` and
    `python-dotenv`; per `.github/copilot-instructions.md` this project standardizes on
    `uv` — ensure `uv.lock` is committed and CI/deploy installs from it rather than a
    loose `pip install`.
17. **Email delivery has no state and no retry.** `notification_daemon` keeps
    "already sent today" only in memory, so a restart can re-send the same daily mail, and
    a failed send is logged but never retried or recorded. A per-day/per-recipient marker
    in the database would make both deterministic. —
    [notifications/management/commands/notification_daemon.py](../../notifications/management/commands/notification_daemon.py),
    [notifications/services.py](../../notifications/services.py)
18. **Leaderboard mail reports snapshot state, not live state.** It sends the newest
    `LeaderboardSnapshot`; if `create_snapshot` is not scheduled, the mail is either
    missing entirely or shows an outdated ranking. —
    [notifications/services.py](../../notifications/services.py),
    [scoring/management/commands/create_snapshot.py](../../scoring/management/commands/create_snapshot.py)
19. **Reminder mails scale per user.** `get_users_with_missing_predictions()` runs one
    prediction query per active user and `send_all_prediction_reminders()` one SMTP call
    per user, serially inside the daemon loop. Fine at ~50-100 users, not beyond. —
    [notifications/services.py](../../notifications/services.py)

## 16. Recommended next steps

The existing architecture does not need replacing for the current scale (~50-100 users).
Suggested order:
1. Fix the Priority 1 correctness issues above (each is small and independently
   reviewable via OpenSpec change tasks).
2. Unify the three polling implementations (home/list/detail) to reduce duplicated logic.
3. Measure query counts before optimizing §12 — don't guess.
4. Only introduce WebSockets/Redis/Celery when a concrete, measured need appears —
   already a hard constraint in `.github/copilot-instructions.md`.
5. Add a service-level test for every scoring/limit rule and a view/integration test for
   every permission-sensitive flow, per this repo's existing testing rules.
