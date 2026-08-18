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

logger = logging.getLogger(__name__)


@receiver(match_result_entered)
def score_predictions_on_result(sender, match, **kwargs):
    """
    Score all predictions when a match result is entered.

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
    except Exception:
        logger.exception(
            "Error scoring predictions for match %s",
            match,
        )


@receiver(match_result_entered)
def update_champion_bonus_on_final(sender, match, **kwargs):
    """
    Update champion bonuses when the final match result changes.

    This receiver is triggered when any match result is entered,
    but only processes champion bonuses if it's the final match.

    Args:
        sender: The Match model class
        match: The Match instance with updated results
        **kwargs: Additional signal arguments
    """
    if match.round != "final":
        return

    try:
        live_bonus_count = update_live_champion_bonuses()
        logger.info(
            "Updated live champion bonuses for %d users",
            live_bonus_count,
        )
    except Exception:
        logger.exception(
            "Error updating champion bonuses for final match %s",
            match,
        )
