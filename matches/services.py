"""
Service functions for syncing teams and matches from football-data.org API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.utils.dateparse import parse_datetime

from matches.api_client import FootballDataClient
from matches.models import Match, Round, Team, Tournament
from matches.tournament import get_active_tournament

logger = logging.getLogger(__name__)


@dataclass
class MatchSyncResult:
    """Result of syncing a single match."""

    match: Match
    goals_changed: bool


# Status mapping from API to Django
API_STATUS_MAP = {
    "SCHEDULED": "scheduled",
    "TIMED": "scheduled",
    "IN_PLAY": "live",
    "PAUSED": "live",
    "FINISHED": "finished",
}

# Round mapping comes from Round.api_stage of the tournament being synced.

# Winner mapping from API to Django
API_WINNER_MAP = {
    "HOME_TEAM": "home",
    "AWAY_TEAM": "away",
    "DRAW": "draw",
}


class UnknownApiStageError(ValueError):
    """Raised when the API reports a stage that no round of the tournament maps to."""


def sync_teams_from_api(tournament: Tournament) -> tuple[int, int, int]:
    """
    Sync teams from football-data.org API to database.

    Fetches teams from the API and upserts them into the database,
    matching by fifa_code (API 'tla' field).

    Args:
        tournament: Tournament whose ``api_competition_code`` is fetched

    Returns:
        Tuple of (created_count, updated_count, unchanged_count)

    Raises:
        FootballDataAPIError: If API request fails
    """
    client = FootballDataClient()
    teams_data = client.get_teams(tournament.api_competition_code)

    created_count = 0
    updated_count = 0
    unchanged_count = 0

    for team_data in teams_data:
        fifa_code = team_data.get("tla")
        name = team_data.get("name")

        if not fifa_code or not name:
            logger.warning("Skipping team with missing tla or name: %s", team_data)
            continue

        team, created = Team.objects.get_or_create(
            fifa_code=fifa_code,
            defaults={"name": name},
        )

        if created:
            created_count += 1
            logger.info("Created team: %s (%s)", name, fifa_code)
            continue

        changed_fields: list[str] = []

        if team.name != name:
            team.name = name
            changed_fields.append("name")

        if changed_fields:
            team.save(update_fields=changed_fields)
            updated_count += 1
            logger.info(
                "Updated team: %s (%s), changed fields: %s",
                name,
                fifa_code,
                changed_fields,
            )
        else:
            unchanged_count += 1
            logger.debug("Team unchanged: %s (%s)", name, fifa_code)

    logger.info(
        "Team sync complete: %d created, %d updated, %d unchanged",
        created_count,
        updated_count,
        unchanged_count,
    )

    return (created_count, updated_count, unchanged_count)


def sync_matches_from_api(tournament: Tournament | None = None) -> list[MatchSyncResult]:
    """
    Sync matches from football-data.org API to database.

    Fetches matches from the API and upserts them into the database,
    matching by external_id. Detects goal changes and returns matches
    that need scoring updates.

    A match that fails to sync (including a failure while scoring it) is logged
    and skipped so the remaining matches are still processed. A stage that no round
    maps to is not skipped: it aborts the sync.

    Args:
        tournament: Tournament to sync; defaults to the active tournament

    Returns:
        List of MatchSyncResult with goal change information

    Raises:
        FootballDataAPIError: If API request fails
        UnknownApiStageError: If the API reports a stage no round maps to
    """
    if tournament is None:
        tournament = get_active_tournament()

    client = FootballDataClient()
    matches_data = client.get_matches(tournament.api_competition_code)

    rounds_by_stage = {
        round_.api_stage: round_ for round_ in Round.objects.filter(tournament=tournament)
    }

    results: list[MatchSyncResult] = []
    failed_count = 0

    for match_data in matches_data:
        try:
            result = _sync_match(match_data, rounds_by_stage)
        except UnknownApiStageError:
            # A stage nobody mapped must not be imported as something else.
            raise
        except (ValueError, TypeError, KeyError, ValidationError, DatabaseError):
            failed_count += 1
            logger.exception("Failed to sync match %s", match_data.get("id"))
            continue

        if result:
            results.append(result)

    logger.info(
        "Match sync complete: %d matches processed, %d with goal changes, %d failed",
        len(results),
        sum(1 for r in results if r.goals_changed),
        failed_count,
    )

    return results


def _sync_match(
    match_data: dict[str, Any], rounds_by_stage: dict[str, Round]
) -> MatchSyncResult | None:
    """
    Sync a single match from API data.

    Args:
        match_data: Match dictionary from API
        rounds_by_stage: Rounds of the tournament keyed by their API stage name

    Returns:
        MatchSyncResult if successful, None if skipped

    Raises:
        UnknownApiStageError: If the match's stage maps to no round
    """
    external_id = match_data.get("id")
    if not external_id:
        logger.warning("Skipping match with no id: %s", match_data)
        return None

    # Extract team codes
    home_team_data = match_data.get("homeTeam", {})
    away_team_data = match_data.get("awayTeam", {})
    home_tla = home_team_data.get("tla")
    away_tla = away_team_data.get("tla")

    if not home_tla or not away_tla:
        logger.warning("Skipping match %d with missing team tla", external_id)
        return None

    # Look up teams
    try:
        team_home = Team.objects.get(fifa_code=home_tla)
        team_away = Team.objects.get(fifa_code=away_tla)
    except Team.DoesNotExist:
        logger.warning(
            "Skipping match %d: teams %s or %s not found in database",
            external_id,
            home_tla,
            away_tla,
        )
        return None

    # Extract match details
    status_api = match_data.get("status", "SCHEDULED")
    status = API_STATUS_MAP.get(status_api, "scheduled")

    stage_api = match_data.get("stage", "")
    if stage_api not in rounds_by_stage:
        raise UnknownApiStageError(
            f"API stage {stage_api!r} maps to no round. "
            f"Configured stages: {', '.join(sorted(rounds_by_stage))}"
        )
    round_value = rounds_by_stage[stage_api]

    kickoff_str = match_data.get("utcDate")
    if not kickoff_str:
        logger.warning("Skipping match %d with no utcDate", external_id)
        return None

    # Parse kickoff - API returns ISO 8601 format
    kickoff = parse_datetime(kickoff_str)
    if not kickoff:
        logger.warning("Skipping match %d with invalid utcDate: %s", external_id, kickoff_str)
        return None

    # Extract score - can be None for scheduled matches
    score = match_data.get("score", {})
    full_time = score.get("fullTime", {})
    goals_home = full_time.get("home")  # None for scheduled, 0+ for finished/live
    goals_away = full_time.get("away")

    # Extract winner - indicates match winner after penalties (if applicable)
    winner_api = score.get("winner")
    winner = API_WINNER_MAP.get(winner_api, "") if winner_api else ""

    # Check for existing match and detect goal changes
    # Only report goals_changed if both new values exist and differ
    try:
        existing_match = Match.objects.get(external_id=external_id)
        goals_changed = (
            goals_home is not None
            and goals_away is not None
            and (existing_match.goals_home != goals_home or existing_match.goals_away != goals_away)
        )
    except Match.DoesNotExist:
        existing_match = None
        goals_changed = False  # New match, not a change

    # Upsert match
    match, created = Match.objects.update_or_create(
        external_id=external_id,
        defaults={
            "team_home": team_home,
            "team_away": team_away,
            "kickoff": kickoff,
            "round": round_value,
            "status": status,
            "goals_home": goals_home,
            "goals_away": goals_away,
            "winner": winner,
        },
    )

    if created:
        logger.info(
            "Created match %d: %s vs %s",
            external_id,
            team_home.name,
            team_away.name,
        )
    else:
        logger.info(
            "Updated match %d: %s vs %s (goals changed: %s)",
            external_id,
            team_home.name,
            team_away.name,
            goals_changed,
        )

    return MatchSyncResult(match=match, goals_changed=goals_changed)
