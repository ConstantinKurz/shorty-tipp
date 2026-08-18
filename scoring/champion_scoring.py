"""
Champion prediction scoring logic.

This module handles scoring for champion predictions during and after the final match.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from matches.models import Team


# Champion prediction points by odds category
CHAMPION_POINTS: dict[str, int] = {
    "A": 20,  # Teams ranked 1-8 by betting odds
    "B": 30,  # Teams ranked 9+ by betting odds
}


def calculate_champion_points(team: Team) -> int:
    """
    Calculate champion prediction points based on team's odds category.

    Args:
        team: The correctly predicted champion team

    Returns:
        Points awarded (20 for category A, 30 for category B, 0 if no category)
    """
    if team.odds_category:
        return CHAMPION_POINTS.get(team.odds_category, 0)
    return 0


def get_current_champion_team() -> Team | None:
    """
    Get the current champion team based on final match state.

    Logic:
    - Final not started: None
    - Final live & one team leading: leading team is provisional champion
    - Final live & draw: team with is_champion=True (set by admin for penalty winner)
    - Final finished & one team won: winning team
    - Final finished & draw: team with is_champion=True

    Returns:
        Team instance or None if no champion can be determined
    """
    # Lazy imports to avoid circular dependencies at runtime
    # TYPE_CHECKING import above is only for type hints
    from matches.models import Match as MatchModel
    from matches.models import Team as TeamModel

    # Find the final match
    final_match = MatchModel.objects.filter(round="final").first()
    if not final_match:
        return None

    # Final not started yet
    if final_match.status == "scheduled":
        return None

    # Final has goals recorded
    if final_match.goals_home is not None and final_match.goals_away is not None:
        home_goals = final_match.goals_home
        away_goals = final_match.goals_away

        if home_goals > away_goals:
            # Home team is leading/won
            return final_match.team_home
        elif away_goals > home_goals:
            # Away team is leading/won
            return final_match.team_away
        else:
            # Draw - use is_champion flag (penalty shootout winner)
            try:
                return TeamModel.objects.get(is_champion=True)
            except (TeamModel.DoesNotExist, TeamModel.MultipleObjectsReturned):
                return None

    return None


@transaction.atomic
def update_live_champion_bonuses() -> int:
    """
    Update champion bonuses for all users during the final.

    This method:
    1. Resets all champion_bonus_points to 0 and adjusts total_points
    2. Calculates new bonuses based on current final state
    3. Updates total_points and champion_bonus_points

    Returns:
        Number of users who received bonuses
    """
    # Lazy import to avoid circular dependency
    from users.models import User as UserModel

    # Get current champion (None if final not started or no clear leader)
    current_champion = get_current_champion_team()

    # Calculate bonus points
    champion_points = 0
    if current_champion is not None:
        champion_points = calculate_champion_points(current_champion)

    # Reset all bonuses first
    users_with_bonus = UserModel.objects.filter(champion_bonus_points__gt=0)
    for user in users_with_bonus:
        user.total_points -= user.champion_bonus_points
        user.champion_bonus_points = 0
        user.save(update_fields=["total_points", "champion_bonus_points"])

    # If no champion or no points, we're done
    if current_champion is None or champion_points == 0:
        return 0

    # Award bonuses to correct predictors
    users_to_award = UserModel.objects.filter(predicted_champion=current_champion)

    count = 0
    for user in users_to_award:
        user.total_points += champion_points
        user.champion_bonus_points = champion_points
        user.save(update_fields=["total_points", "champion_bonus_points"])
        count += 1

    return count
