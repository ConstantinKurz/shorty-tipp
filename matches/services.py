"""
Service functions for syncing teams and matches from football-data.org API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from matches.api_client import FootballDataClient
from matches.models import Match, Team
from django.utils.dateparse import parse_datetime
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

# Round mapping from API to Django
API_ROUND_MAP = {
    "GROUP_STAGE": "group",
    "ROUND_OF_32": "r32",
    "ROUND_OF_16": "r16",
    "QUARTER_FINALS": "qf",
    "SEMI_FINALS": "sf",
    "THIRD_PLACE": "3rd",
    "FINAL": "final",
}

# Winner mapping from API to Django
API_WINNER_MAP = {
    "HOME_TEAM": "home",
    "AWAY_TEAM": "away",
    "DRAW": "draw",
}

def sync_teams_from_api(competition: str = "WC") -> tuple[int, int, int]:
    """
    Sync teams from football-data.org API to database.

    Fetches teams from the API and upserts them into the database,
    matching by fifa_code (API 'tla' field).

    Args:
        competition: Competition code (default: WC for World Cup)

    Returns:
        Tuple of (created_count, updated_count)

    Raises:
        FootballDataAPIError: If API request fails
    """
    client = FootballDataClient()
    teams_data = client.get_teams(competition)

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


def sync_matches_from_api(competition: str = "WC") -> list[MatchSyncResult]:
    """
    Sync matches from football-data.org API to database.

    Fetches matches from the API and upserts them into the database,
    matching by external_id. Detects goal changes and returns matches
    that need scoring updates.

    Args:
        competition: Competition code (default: WC for World Cup)

    Returns:
        List of MatchSyncResult with goal change information

    Raises:
        FootballDataAPIError: If API request fails
    """
    client = FootballDataClient()
    matches_data = client.get_matches(competition)

    results: list[MatchSyncResult] = []

    for match_data in matches_data:
        result = _sync_match(match_data)
        if result:
            results.append(result)

    logger.info(
        "Match sync complete: %d matches processed, %d with goal changes",
        len(results),
        sum(1 for r in results if r.goals_changed),
    )

    return results


def _sync_match(match_data: dict[str, Any]) -> MatchSyncResult | None:
    """
    Sync a single match from API data.

    Args:
        match_data: Match dictionary from API

    Returns:
        MatchSyncResult if successful, None if skipped
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

    stage_api = match_data.get("stage", "GROUP_STAGE")
    round_value = API_ROUND_MAP.get(stage_api, "group")

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
    winner = API_WINNER_MAP.get(winner_api) if winner_api else None

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
