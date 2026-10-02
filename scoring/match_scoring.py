"""
Match prediction scoring service.

This module contains the core business logic for calculating match prediction
points according to Shortytipp game rules.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import F

from matches.models import Match
from predictions.models import MatchPrediction
from scoring.champion_scoring import update_live_champion_bonuses
from users.models import User


class ScoringService:
    """
    Service for calculating prediction points according to Shortytipp rules.

    Scoring categories (in precedence order):
    1. Exact score match: 6 points
    2. Correct tendency + goal difference: 5 points
    3. Correct tendency + one team's goals: 4 points
    4. Correct tendency only: 3 points
    5. One team's goals only: 1 point
    6. No match: 0 points

    Points are multiplied by the round multiplier, then by the round's joker
    multiplier when the prediction carries a joker. Both come from the ``Round`` row.
    """

    @staticmethod
    def _calculate_base_points(
        pred_home: int,
        pred_away: int,
        actual_home: int,
        actual_away: int,
    ) -> tuple[int, bool]:
        """
        Calculate base points for a match prediction.

        Evaluates prediction against actual result using the 6-category
        scoring system in strict precedence order.

        Args:
            pred_home: Predicted home team goals
            pred_away: Predicted away team goals
            actual_home: Actual home team goals
            actual_away: Actual away team goals

        Returns:
            Tuple of (base_points, is_exact_match)
        """
        # Check exact score (6 points)
        if ScoringService._check_exact_score(pred_home, pred_away, actual_home, actual_away):
            return 6, True

        # Check tendency + goal difference (5 points)
        if ScoringService._check_tendency_and_diff(pred_home, pred_away, actual_home, actual_away):
            return 5, False

        # Check tendency + one goal correct (4 points)
        if ScoringService._check_tendency_and_one_goal(
            pred_home, pred_away, actual_home, actual_away
        ):
            return 4, False

        # Check tendency only (3 points)
        if ScoringService._check_tendency_only(pred_home, pred_away, actual_home, actual_away):
            return 3, False

        # Check one goal only (1 point)
        if ScoringService._check_one_goal_only(pred_home, pred_away, actual_home, actual_away):
            return 1, False

        # No match (0 points)
        return 0, False

    @staticmethod
    def _check_exact_score(
        pred_home: int, pred_away: int, actual_home: int, actual_away: int
    ) -> bool:
        """Check if prediction exactly matches the result."""
        return pred_home == actual_home and pred_away == actual_away

    @staticmethod
    def _get_tendency(home: int, away: int) -> str:
        """Get match tendency: 'home', 'draw', or 'away'."""
        if home > away:
            return "home"
        elif home < away:
            return "away"
        return "draw"

    @staticmethod
    def _check_tendency_and_diff(
        pred_home: int, pred_away: int, actual_home: int, actual_away: int
    ) -> bool:
        """
        Check if tendency and goal difference are correct.

        Example: Predicted 3:2, actual 1:0 → tendency 'home' correct, diff 1 correct → 5 pts
        """
        pred_tendency = ScoringService._get_tendency(pred_home, pred_away)
        actual_tendency = ScoringService._get_tendency(actual_home, actual_away)

        if pred_tendency != actual_tendency:
            return False

        pred_diff = pred_home - pred_away
        actual_diff = actual_home - actual_away

        return pred_diff == actual_diff

    @staticmethod
    def _check_tendency_and_one_goal(
        pred_home: int, pred_away: int, actual_home: int, actual_away: int
    ) -> bool:
        """
        Check if tendency correct AND at least one team's goals correct.

        Example: Predicted 3:2, actual 3:0 → tendency 'home' correct, home goals (3) correct → 4 pts
        """
        pred_tendency = ScoringService._get_tendency(pred_home, pred_away)
        actual_tendency = ScoringService._get_tendency(actual_home, actual_away)

        if pred_tendency != actual_tendency:
            return False

        # At least one goal correct
        return pred_home == actual_home or pred_away == actual_away

    @staticmethod
    def _check_tendency_only(
        pred_home: int, pred_away: int, actual_home: int, actual_away: int
    ) -> bool:
        """
        Check if only tendency is correct (no other category matches).

        Example: Predicted 3:2, actual 7:0 → tendency 'home' correct, nothing else → 3 pts
        """
        pred_tendency = ScoringService._get_tendency(pred_home, pred_away)
        actual_tendency = ScoringService._get_tendency(actual_home, actual_away)

        return pred_tendency == actual_tendency

    @staticmethod
    def _check_one_goal_only(
        pred_home: int, pred_away: int, actual_home: int, actual_away: int
    ) -> bool:
        """
        Check if at least one goal is correct but tendency is wrong.

        Example: Predicted 3:2, actual 0:2 → tendency wrong, away goals (2) correct → 1 pt
        """
        pred_tendency = ScoringService._get_tendency(pred_home, pred_away)
        actual_tendency = ScoringService._get_tendency(actual_home, actual_away)

        # Tendency must be WRONG for this category
        if pred_tendency == actual_tendency:
            return False

        # At least one goal correct
        return pred_home == actual_home or pred_away == actual_away

    @staticmethod
    def _apply_joker_multiplier(points: int, joker_active: bool, joker_multiplier: int) -> int:
        """
        Apply the round's joker multiplier if the joker is active.

        Args:
            points: Points after round multiplier
            joker_active: Whether joker is active for this prediction
            joker_multiplier: Factor configured on the round

        Returns:
            Final points
        """
        return points * joker_multiplier if joker_active else points

    @staticmethod
    def calculate_match_points(
        prediction: MatchPrediction,
        match: Match,
    ) -> dict[str, int | bool]:
        """
        Calculate full points for a match prediction.

        Applies the formula: final_points = base_points * round_multiplier * joker_multiplier

        Args:
            prediction: The user's prediction
            match: The match with actual result

        Returns:
            Dict with keys: points, is_exact, base_points

        Example:
            >>> # Exact score in quarter-final with joker
            >>> # base: 6, round: x3, joker: x2 → 36 points
        """
        if match.goals_home is None or match.goals_away is None:
            return {"points": 0, "is_exact": False, "base_points": 0}

        base_points, is_exact = ScoringService._calculate_base_points(
            pred_home=prediction.predicted_goals_home,
            pred_away=prediction.predicted_goals_away,
            actual_home=match.goals_home,
            actual_away=match.goals_away,
        )

        round_multiplier = match.round.multiplier
        points_after_round = base_points * round_multiplier
        final_points = ScoringService._apply_joker_multiplier(
            points_after_round, prediction.joker_active, match.round.joker_multiplier
        )

        return {
            "points": final_points,
            "is_exact": is_exact,
            "base_points": base_points,
        }

    @staticmethod
    @transaction.atomic
    def score_prediction(prediction: MatchPrediction) -> dict[str, int | bool]:
        """
        Score a single prediction and update the database.

        Updates:
        - prediction.points_earned
        - prediction.is_exact_match
        - user.total_points
        - user.exact_match_count
        - user.jokers_used

        Args:
            prediction: The prediction to score

        Returns:
            Dict with scoring details
        """
        match = prediction.match
        result = ScoringService.calculate_match_points(prediction, match)

        # Get previous values for delta calculation
        old_points = prediction.points_earned or 0
        old_is_exact = prediction.is_exact_match or False
        old_joker_counted = prediction.points_earned is not None and prediction.joker_active

        # Update prediction
        prediction.points_earned = result["points"]
        prediction.is_exact_match = result["is_exact"]
        prediction.save(update_fields=["points_earned", "is_exact_match"])

        # Update user statistics with deltas
        user = prediction.user
        points_delta = result["points"] - old_points
        exact_delta = (1 if result["is_exact"] else 0) - (1 if old_is_exact else 0)
        joker_delta = (1 if prediction.joker_active else 0) - (1 if old_joker_counted else 0)

        # Use F() expressions for atomic updates
        User.objects.filter(pk=user.pk).update(
            total_points=F("total_points") + points_delta,
            exact_match_count=F("exact_match_count") + exact_delta,
            jokers_used=F("jokers_used") + joker_delta,
        )

        # Refresh user from DB to get updated values
        user.refresh_from_db()

        return result

    @staticmethod
    @transaction.atomic
    def score_all_predictions_for_match(match: Match) -> int:
        """
        Score all predictions for a match.

        Args:
            match: The match with results to score

        Returns:
            Number of predictions scored
        """
        if match.goals_home is None or match.goals_away is None:
            return 0

        predictions = MatchPrediction.objects.filter(match=match).select_related("user")
        count = 0

        for prediction in predictions:
            ScoringService.score_prediction(prediction)
            count += 1

        return count


@transaction.atomic
def recalculate_all_scores() -> int:
    """
    Reset and recompute every score from the current configuration.

    Clears user statistics and prediction scores, re-scores all finished matches and
    refreshes champion bonuses. Used after round or team configuration changed.

    Returns:
        Number of predictions scored.
    """
    User.objects.update(total_points=0, exact_match_count=0, jokers_used=0, champion_bonus_points=0)
    MatchPrediction.objects.update(points_earned=None, is_exact_match=False)

    finished_matches = (
        Match.objects.filter(
            status="finished",
            goals_home__isnull=False,
            goals_away__isnull=False,
        )
        .select_related("round")
        .order_by("kickoff")
    )

    total_scored = 0
    for match in finished_matches:
        total_scored += ScoringService.score_all_predictions_for_match(match)

    update_live_champion_bonuses()

    return total_scored
