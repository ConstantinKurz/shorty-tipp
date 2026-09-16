# Document System Architecture

## Why

The project has `docs/project/decisions.md` (individual ADRs) and `docs/rules/wm2026-rules.md` (game rules), but no single document explains how the system fits together: request flow, app boundaries, data model, HTMX polling design, scoring/ranking pipeline, and result-import scheduling. New contributors (human or AI) have to reconstruct this by reading code across `matches/`, `predictions/`, `scoring/`, `users/`, `core/`, and `templates/`.

An external architecture write-up for a sibling project ("Shorty-Tipp") was supplied as a starting point. It was **fact-checked line-by-line against this repository's actual code** (models, views, urls, signals, templates, settings, management commands). Almost all of its structural description and its "open issues" list matches `django-tipapp` directly, since this codebase shares the same design. A few details needed correction for this repo specifically (app names already match, but `notifications` app, INSTALLED_APPS state, and exact URL/view names needed verification).

## What Changes

- Add `docs/project/architecture.md`: a verified architecture reference covering the mental model, module breakdown, data model (ERD), URL routing, page-by-page walkthrough, prediction write flow, HTMX polling patterns, scoring/ranking pipeline, result-import scheduling, a "where do I change what" map, a debugging checklist, and a prioritized list of **verified** known issues.
- No application code changes. This is a documentation-only change.

## Verification Method

Every claim reused from the source document was checked against this repository:
- Models: `users/models.py`, `matches/models.py`, `predictions/models.py`, `scoring/models.py`
- Views/URLs: `tipapp/urls.py`, `tipapp/views.py`, `predictions/urls.py`, `predictions/views.py`, `scoring/urls.py`, `scoring/views.py`, `users/urls.py`, `users/views.py`, `users/forms.py`
- Signals/services: `matches/signals.py`, `scoring/signals.py`, `scoring/match_scoring.py`, `predictions/services.py`, `core/ranking.py`
- Background sync: `matches/management/commands/update_matches.py`, `matches/api_client.py`
- Settings/deployment: `tipapp/wsgi.py`, `tipapp/settings/__init__.py`, `tipapp/settings/base.py`, `tipapp/settings/production.py`
- Templates/HTMX: `templates/base.html`, `templates/home.html`, `templates/partials/ranking_updates.html`, `templates/predictions/prediction_list.html`, `templates/predictions/prediction_row.html`, `templates/predictions/match_predictions_page.html`
- Dependencies: `pyproject.toml`, `static/` (empty, confirms no Tailwind build step)

## Capabilities

### New Capabilities

- `project-documentation`: Adds a maintained architecture reference document for onboarding and change planning.

## Impact

- No behavior change, no migrations, no tests required (docs only).
- Improves future OpenSpec proposals/design docs by giving a single reference for existing conventions and known trouble spots.
