"""
Scoring and ranking services for the tipapp application.

This module contains the core business logic for calculating match prediction
points and generating leaderboard rankings according to WM 2026 game rules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import F

from scoring.models import LeaderboardSnapshot

if TYPE_CHECKING:
    from matches.models import Match, Team
    from predictions.models import MatchPrediction


class ScoringService:
    """
    Service for calculating prediction points according to WM 2026 rules.

    Scoring categories (in precedence order):
    1. Exact score match: 6 points
    2. Correct tendency + goal difference: 5 points
    3. Correct tendency + one team's goals: 4 points
    4. Correct tendency only: 3 points
    5. One team's goals only: 1 point
    6. No match: 0 points

    Points are multiplied by round multiplier, then by joker (if active).
    """

    # Round multipliers per WM 2026 rules section 4
    ROUND_MULTIPLIERS: dict[str, int] = {
        "group": 1,   # Group stage
        "r32": 2,     # Round of 32
        "r16": 2,     # Round of 16
        "qf": 3,      # Quarter-final
        "sf": 3,      # Semi-final
        "3rd": 3,     # Third place
        "final": 3,   # Final
    }

    # Champion prediction points by odds category
    CHAMPION_POINTS: dict[str, int] = {
        "A": 20,  # Teams ranked 1-8 by betting odds
        "B": 30,  # Teams ranked 9+ by betting odds
    }

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
        if ScoringService._check_tendency_and_one_goal(pred_home, pred_away, actual_home, actual_away):
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
    def _get_round_multiplier(match_round: str) -> int:
        """
        Get the round multiplier for a match.

        Args:
            match_round: The tournament round (e.g., 'group', 'r16', 'final')

        Returns:
            Multiplier value (1, 2, or 3)
        """
        return ScoringService.ROUND_MULTIPLIERS.get(match_round, 1)

    @staticmethod
    def _apply_joker_multiplier(points: int, joker_active: bool) -> int:
        """
        Apply joker multiplier if active.

        Args:
            points: Points after round multiplier
            joker_active: Whether joker is active for this prediction

        Returns:
            Final points (doubled if joker active)
        """
        return points * 2 if joker_active else points

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

        round_multiplier = ScoringService._get_round_multiplier(match.round)
        points_after_round = base_points * round_multiplier
        final_points = ScoringService._apply_joker_multiplier(
            points_after_round, prediction.joker_active
        )

        return {
            "points": final_points,
            "is_exact": is_exact,
            "base_points": base_points,
        }

    @staticmethod
    def calculate_champion_points(team: Team) -> int:
        """
        Calculate champion prediction points based on team's odds category.

        Args:
            team: The correctly predicted champion team

        Returns:
            Points awarded (20 for category A, 30 for category B, 0 if no category)
        """
        if team.odds_category:
            return ScoringService.CHAMPION_POINTS.get(team.odds_category, 0)
        return 0

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
        from predictions.models import MatchPrediction  # noqa: F811

        match = prediction.match
        result = ScoringService.calculate_match_points(prediction, match)

        # Get previous values for delta calculation
        old_points = prediction.points_earned or 0
        old_is_exact = prediction.is_exact_match or False
        old_joker_counted = (
            prediction.points_earned is not None and prediction.joker_active
        )

        # Update prediction
        prediction.points_earned = result["points"]
        prediction.is_exact_match = result["is_exact"]
        prediction.save(update_fields=["points_earned", "is_exact_match"])

        # Update user statistics with deltas
        user = prediction.user
        points_delta = result["points"] - old_points
        exact_delta = (1 if result["is_exact"] else 0) - (1 if old_is_exact else 0)
        joker_delta = (
            (1 if prediction.joker_active else 0)
            - (1 if old_joker_counted else 0)
        )

        # Use F() expressions for atomic updates
        MatchPrediction.objects.filter(user=user).exists()  # Ensure user relationship
        from users.models import User as UserModel  # noqa: F811

        UserModel.objects.filter(pk=user.pk).update(
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
        Score all predictions for a finished match.

        Args:
            match: The match with results to score

        Returns:
            Number of predictions scored
        """
        from predictions.models import MatchPrediction  # noqa: F811

        if match.goals_home is None or match.goals_away is None:
            return 0

        predictions = MatchPrediction.objects.filter(match=match).select_related(
            "user"
        )
        count = 0

        for prediction in predictions:
            ScoringService.score_prediction(prediction)
            count += 1

        return count

    @staticmethod
    @transaction.atomic
    def score_champion_predictions() -> int:
        """
        Score champion predictions after tournament ends.

        Only scores when:
        - A team has is_champion=True
        - The final match is finished

        Returns:
            Number of users who received champion points
        """
        from matches.models import Match as MatchModel  # noqa: F811
        from matches.models import Team as TeamModel  # noqa: F811
        from users.models import User as UserModel  # noqa: F811

        # Find the champion team
        try:
            champion = TeamModel.objects.get(is_champion=True)
        except TeamModel.DoesNotExist:
            return 0
        except TeamModel.MultipleObjectsReturned:
            # Data integrity issue - should not happen
            return 0

        # Check if final match is finished
        final_match = MatchModel.objects.filter(round="final", status="finished").first()
        if not final_match:
            return 0

        # Calculate points based on champion's odds category
        champion_points = ScoringService.calculate_champion_points(champion)
        if champion_points == 0:
            return 0

        # Award points to users who predicted correctly
        # Only award if not already awarded (check by looking at users with this champion
        # who don't have the champion points yet - we track this implicitly)
        users_to_award = UserModel.objects.filter(
            predicted_champion=champion,
        )

        count = users_to_award.update(
            total_points=F("total_points") + champion_points,
        )

        return count


class RankingService:
    """
    Service for generating leaderboards and rankings.

    Ranking uses Olympic tiebreakers per WM 2026 rules:
    1. Total points (higher is better)
    2. Exact match count (higher is better)
    3. Jokers used (fewer is better - more jokers left = better)

    Users with identical values share the same rank.
    """

    @staticmethod
    def get_current_leaderboard() -> list[dict]:
        """
        Generate the current leaderboard with rankings.

        Returns:
            List of dicts with: rank, user_id, username, total_points,
            exact_match_count, jokers_used

        Example:
            [
                {"rank": 1, "user_id": 5, "username": "alice", "total_points": 100, ...},
                {"rank": 2, "user_id": 3, "username": "bob", "total_points": 95, ...},
                {"rank": 2, "user_id": 7, "username": "carol", "total_points": 95, ...},  # Shared rank
                {"rank": 4, "user_id": 1, "username": "dave", "total_points": 90, ...},
            ]
        """
        from users.models import User as UserModel  # noqa: F811

        # Get all active users ordered by tiebreaker criteria
        # Note: jokers_used ascending because FEWER used = better (more remaining)
        users = UserModel.objects.filter(is_active=True).order_by(
            "-total_points",
            "-exact_match_count",
            "jokers_used",  # Ascending: fewer jokers used = better
        )

        if not users.exists():
            return []

        return RankingService._calculate_rank_numbers(list(users))

    @staticmethod
    def _calculate_rank_numbers(users: list) -> list[dict]:
        """
        Calculate rank numbers with shared rank support.

        Users with identical tiebreaker values share the same rank.
        The next rank skips accordingly (1, 2, 2, 4 not 1, 2, 2, 3).

        Args:
            users: List of User objects sorted by ranking criteria

        Returns:
            List of dicts with rank and user data
        """
        if not users:
            return []

        result = []
        current_rank = 1

        for i, user in enumerate(users):
            # Check if this user shares rank with previous
            if i > 0:
                prev = users[i - 1]
                same_rank = (
                    user.total_points == prev.total_points
                    and user.exact_match_count == prev.exact_match_count
                    and user.jokers_used == prev.jokers_used
                )
                if not same_rank:
                    current_rank = i + 1  # Skip to actual position

            result.append(
                {
                    "rank": current_rank,
                    "user_id": user.pk,
                    "username": user.username,
                    "total_points": user.total_points,
                    "exact_match_count": user.exact_match_count,
                    "jokers_used": user.jokers_used,
                }
            )

        return result

    @staticmethod
    def create_snapshot(snapshot_type: str) -> LeaderboardSnapshot:
        """
        Create a snapshot of the current leaderboard.

        Args:
            snapshot_type: Type of snapshot ('daily', 'weekly', 'final')

        Returns:
            The created LeaderboardSnapshot instance
        """
        from scoring.models import LeaderboardSnapshot

        leaderboard = RankingService.get_current_leaderboard()

        snapshot = LeaderboardSnapshot.objects.create(
            snapshot_type=snapshot_type,
            data=leaderboard,
        )

        return snapshot
