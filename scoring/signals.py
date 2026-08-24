"""
Signal receivers for scoring-related events.

This module contains signal receivers that handle automatic scoring
when match results are entered or updated.
"""

import logging

from django.dispatch import receiver

from matches.signals import match_result_entered
from scoring.champion_scoring import update_live_champion_bonuses
from scoring.match_scoring import ScoringService
from scoring.ranking_service import RankingService

logger = logging.getLogger(__name__)


@receiver(match_result_entered)
def score_predictions_on_result(sender, match, **kwargs):
    """
    Score all predictions when a match result is entered.
    After scoring, update all global ranks.

    This receiver is triggered when match goals are set or updated.
    It automatically scores all predictions for the match.

    Args:
        sender: The Match model class
        match: The Match instance with updated results
        **kwargs: Additional signal arguments
    """
    try:
        scored_count = ScoringService.score_all_predictions_for_match(match)
        logger.info(
            "Scored %d predictions for match %s",
            scored_count,
            match,
        )
        if match.round == "final":
            live_bonus_count = update_live_champion_bonuses()
            logger.info(
                "Updated live champion bonuses for %d users",
                live_bonus_count,
            )

        
        # Update global ranks after scoring
        rank_count = RankingService.update_all_user_ranks()
        logger.info(
            "Updated global ranks for %d users",
            rank_count,
        )
    except Exception:
        logger.exception(
            "Error scoring predictions for match %s",
            match,
        )
