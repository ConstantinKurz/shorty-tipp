# Tasks: Document System Architecture

## 1. Fact-check source material

- [x] Compare source doc's app/module breakdown against `INSTALLED_APPS` and directory tree
- [x] Verify all model fields against `users/models.py`, `matches/models.py`, `predictions/models.py`, `scoring/models.py`
- [x] Verify URL routing against `tipapp/urls.py`, `predictions/urls.py`, `scoring/urls.py`, `users/urls.py`
- [x] Verify scoring formula and round multipliers against `scoring/match_scoring.py`
- [x] Verify joker limits and lock buffer against `predictions/services.py`
- [x] Verify Olympic ranking algorithm against `core/ranking.py`
- [x] Verify signal-based scoring against `matches/signals.py` and `scoring/signals.py`
- [x] Verify result-import polling intervals against `matches/management/commands/update_matches.py`
- [x] Verify API client retry/backoff behavior against `matches/api_client.py`
- [x] Verify HTMX polling/OOB patterns against `templates/base.html`, `templates/home.html`, `templates/partials/ranking_updates.html`, `templates/predictions/*.html`
- [x] Verify each of the 16 "open issues" from the source doc against current code, note which apply as-is, which differ, which don't apply

## 2. Write architecture documentation

- [x] Create `docs/project/architecture.md` with verified content only (no unverified claims carried over)
- [x] Include Mermaid diagrams: system mental model, ERD, prediction write-flow sequence
- [x] Include "Known Issues" section with exact file references for this repo
- [x] Include "where do I change what" map and debugging checklist

## 3. Wire up discoverability

- [x] Add a link to `docs/project/architecture.md` from `README.md`

## Acceptance Criteria

- [x] `docs/project/architecture.md` exists and contains no claims contradicted by the actual codebase
- [x] Every "known issue" listed includes a concrete file/line reference from this repository
- [x] No application code or tests were changed
- [x] `README.md` links to the new document
