# Design: Architecture Documentation

## Overview

Add one new file, `docs/project/architecture.md`, without touching application code. The document is derived from an external write-up of a sibling project but rewritten and corrected against this repository's actual source.

## Fact-check results (right vs. wrong from the source material)

| Claim from source doc | Verdict for `django-tipapp` | Evidence |
|---|---|---|
| Django monolith, server-rendered templates + HTMX, PostgreSQL | **Correct** | [tipapp/settings/base.py](tipapp/settings/base.py), `templates/` |
| App split: `tipapp`, `core`, `users`, `matches`, `predictions`, `scoring`, `templates` | **Correct**, but incomplete | `INSTALLED_APPS` in [tipapp/settings/base.py](tipapp/settings/base.py) lists exactly these 5 local apps |
| A `notifications` app exists and is part of the architecture | **Wrong as stated** | `notifications/` directory exists on disk (migrations, management, tests folders) but has no `models.py`/`apps.py` and is **not** in `INSTALLED_APPS` — it is inactive scaffolding, not a working app |
| Forum for tippers to communicate | **Not implemented** | No forum-related models/views found anywhere; only mentioned as a product-boundary goal in `.github/copilot-instructions.md` |
| User model fields (`predicted_champion`, `total_points`, `exact_match_count`, `jokers_used`, `global_rank`, `theme_preference`) | **Correct**, plus one extra field | [users/models.py](users/models.py) also has `champion_bonus_points` (not mentioned in source doc) |
| `Match` model fields incl. `winner` separate from goals for penalty shootouts | **Correct** | [matches/models.py](matches/models.py) |
| `MatchPrediction` unique per `(user, match)` | **Correct** | [predictions/models.py](predictions/models.py) |
| `LeaderboardSnapshot` stores JSON, decoupled from FK | **Correct** | [scoring/models.py](scoring/models.py) |
| URL routing structure (`predictions/`, `scoring/`, users at root, password reset) | **Correct**, plus a redirect | [tipapp/urls.py](tipapp/urls.py) also has `ranking/` → redirect to `/` (legacy URL kept working) |
| Scoring categories (6/5/4/3/1/0) and round multipliers (1×/2×/2×/3×/3×/3×/3×) | **Correct, exact match** | [scoring/match_scoring.py](scoring/match_scoring.py) `ROUND_MULTIPLIERS` |
| Joker limits per round + combined sf/final/3rd pool of 2 | **Correct, exact match** | [predictions/services.py](predictions/services.py) `JOKER_LIMITS`, `COMBINED_ROUNDS` |
| Lock buffer 3 minutes before kickoff | **Correct** | [predictions/services.py](predictions/services.py) `LOCK_BUFFER_MINUTES` |
| Olympic ranking algorithm (shared ranks, skip after ties) | **Correct** | [core/ranking.py](core/ranking.py) `apply_olympic_ranking` |
| Signal-based scoring (`match_result_entered`) | **Correct** | [matches/signals.py](matches/signals.py), [scoring/signals.py](scoring/signals.py) |
| Result-import polling intervals (10s live / 30s active window / 60s <30min / 5min <2h / 10min else / 30min none) | **Correct, exact match** | [matches/management/commands/update_matches.py](matches/management/commands/update_matches.py) `_calculate_sleep_interval` |
| API client respects `Retry-After`, exponential backoff on 5xx | **Correct** | [matches/api_client.py](matches/api_client.py) |
| Tailwind via CDN, no build pipeline | **Correct** | `templates/base.html` line 10 loads `cdn.tailwindcss.com`; `static/` is empty |
| `requests` + `python-dotenv` dependencies | **Correct** | [pyproject.toml](pyproject.toml) |
| **Issue 1** – empty HTTP 200 on unchanged version + `innerHTML` swap can blank `#predictions-content` | **Confirmed present** | [predictions/views.py](predictions/views.py) `MatchPredictionsUpdateView.get` returns `HttpResponse("")` when `is_locked and client_version == current_version`; [templates/predictions/match_predictions_page.html](templates/predictions/match_predictions_page.html) uses `hx-swap="innerHTML"` |
| **Issue 2** – finished match may not reach open prediction list | **Confirmed present** | [predictions/views.py](predictions/views.py) `PredictionUpdatesView.get` explicitly `.exclude(status="finished")` |
| **Issue 3** – champion lock is UI-only | **Confirmed present** | [users/views.py](users/views.py) `can_change_champion()` only affects template rendering; [users/forms.py](users/forms.py) `UserSettingsForm` has no server-side check preventing a champion change after kickoff |
| **Issue 4** – 36-prediction group limit is effectively 35 | **Confirmed present** | [predictions/views.py](predictions/views.py) `PredictionSaveView.post` calls `get_or_create()` first (so the new row already counts), then checks `can_add_group_stage_prediction()` which compares `count < 36`; the 36th attempt sees count already at 36 and is rejected |
| **Issue 5** – winner/status-only change does not re-trigger scoring | **Confirmed present** | [matches/models.py](matches/models.py) `Match.save()` only compares `goals_home`/`goals_away`, not `winner` or `status` |
| **Issue 6** – scoring errors are silently logged only | **Confirmed present** | [scoring/signals.py](scoring/signals.py) `score_predictions_on_result` wraps everything in a bare `except Exception: logger.exception(...)` |
| **Issue 7** – duplicate autosave (input `hx-trigger` + global JS submit) | **Confirmed present** | [templates/predictions/prediction_row.html](templates/predictions/prediction_row.html) inputs use `hx-trigger="input delay:500ms"`; [templates/base.html](templates/base.html) also has a global 500ms debounce that calls `htmx.trigger(form, 'submit')` |
| **Issue 8-10, 12-16** (versioning granularity, homepage match cards not live, static intervals, N+1-ish joker counts, missing champion bonus in match-detail totals, settings/wsgi defaulting, validation text mismatch, dependency lock) | **Applicable, same root causes** | Verified against corresponding files; see architecture doc "Known Issues" section for the up-to-date list with this repo's file paths |
| **Issue 16 (lockfile)** | **Partially different** | `pyproject.toml` has `requests`/`python-dotenv`, but this repo already standardizes on `uv` per `.github/copilot-instructions.md`; recommendation narrowed to "ensure `uv.lock` is committed and CI installs from it" |

## Document Structure

`docs/project/architecture.md` sections:
1. One-sentence summary
2. Mental model (3 flows: browser↔Django, background sync↔football-data.org, signal-driven scoring) + Mermaid diagram
3. Why this architecture (decision table, reused from `decisions.md` style)
4. Module breakdown (`tipapp`, `core`, `users`, `matches`, `predictions`, `scoring`, `notifications` marked inactive, `templates`)
5. Data model + Mermaid ERD
6. URL routing map
7. Page-by-page walkthrough (home, prediction list, match detail, settings, rules, admin/export) with exact view/class names
8. Prediction write flow (Mermaid sequence diagram)
9. HTMX pattern reference table (attributes used, OOB swap explanation)
10. Scoring & ranking pipeline (formulas, joker rules, signal flow, Olympic ranking)
11. Result import scheduling (management command + API client)
12. "Where do I change what" map
13. Debugging checklist
14. Known issues (prioritized, verified, with exact file references)
15. Recommended next steps

## Rationale for doc-only change

No code is modified. Documentation changes do not require spec deltas per `openspec/specs/` (currently empty — this repo has not been populating capability specs) and match the pattern of other structural/no-behavior-change entries such as `code-structure-review`, which also carried no spec deltas.
