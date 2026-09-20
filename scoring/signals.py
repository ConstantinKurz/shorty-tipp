"""
Signal receivers for scoring-related events.

This module contains signal receivers that handle automatic scoring
when match results are entered or updated.
"""

import logging

from django.db import transaction
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

    This receiver is triggered when a scoring-relevant match field changes.
    Scoring, champion bonus and rank update run in one atomic block, so a failure
    leaves no partially scored state. Failures are logged with the match id and
    re-raised to the caller instead of being swallowed.

    Args:
        sender: The Match model class
        match: The Match instance with updated results
        **kwargs: Additional signal arguments

    Raises:
        Exception: Any error raised while scoring, after logging and rollback.
    """
    try:
        with transaction.atomic():
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
            "Scoring failed for match %s (id=%s)",
            match,
            match.pk,
        )
        raise
