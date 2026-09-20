"""
Leaderboard and ranking service.

This module handles generation of leaderboards with Olympic-style ranking.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q, Sum

from core.ranking import apply_olympic_ranking
from matches.constants import ROUND_ORDER
from scoring.models import LeaderboardSnapshot
from users.models import User as UserModel


class RankingService:
    """
    Service for generating leaderboards and rankings.

    Ranking uses Olympic tiebreakers per Shortytipp rules:
    1. Total points (higher is better)
    2. Exact match count (higher is better)
    3. Jokers used (fewer is better - more jokers left = better)

    Users with identical values share the same rank.
    """

    @staticmethod
    def get_leaderboard_up_to_round(round_code: str | None = None) -> list[dict]:
        """
        Generate leaderboard including matches up to a specific round.

        Args:
            round_code: Tournament round ('group', 'r32', 'r16', 'qf', 'sf', '3rd', 'final')
                       If None or 'final' or invalid, returns live view using cached User fields

        Returns:
            List of dicts with: rank, user_id, username, total_points,
            exact_match_count, jokers_used

        Example:
            >>> RankingService.get_leaderboard_up_to_round('group')
            [{"rank": 1, "user_id": 5, "username": "alice", "total_points": 30, ...}]
        """
        # For live view (None), final, or invalid codes, use cached User fields
        # This includes champion bonus points which are not in match predictions
        if round_code is None or round_code == "final" or round_code not in ROUND_ORDER:
            users = UserModel.objects.filter(is_active=True).order_by(
                "-total_points",
                "-exact_match_count",
                "jokers_used",  # Ascending: fewer jokers used = better
            )
            if not users.exists():
                return []

            # No need to calculate live bonuses here - they're already in total_points
            # Just return the sorted users
            return RankingService._calculate_rank_numbers(list(users))

        # For round-filtered view, calculate from match predictions
        # Determine which rounds to include
        cutoff_index = ROUND_ORDER.index(round_code)
        included_rounds = ROUND_ORDER[: cutoff_index + 1]

        # Build filter for matches in included rounds
        match_filter = Q(
            match_predictions__match__round__in=included_rounds,
            match_predictions__match__status="finished",
            match_predictions__points_earned__isnull=False,
        )

        # Aggregate user statistics (use different names to avoid model field conflicts)
        users = (
            UserModel.objects.filter(is_active=True)
            .annotate(
                filtered_total_points=Sum(
                    "match_predictions__points_earned",
                    filter=match_filter,
                    default=0,
                ),
                filtered_exact_count=Count(
                    "match_predictions",
                    filter=match_filter & Q(match_predictions__is_exact_match=True),
                ),
                filtered_jokers_used=Count(
                    "match_predictions",
                    filter=match_filter & Q(match_predictions__joker_active=True),
                ),
            )
            .order_by(
                "-filtered_total_points",
                "-filtered_exact_count",
                "filtered_jokers_used",  # ASC: fewer used = better
            )
        )

        # Convert QuerySet to list and update attributes for _calculate_rank_numbers
        user_list = []
        for user in users:
            # Create a simple object with the attributes expected by _calculate_rank_numbers
            # We temporarily override the model fields with filtered values from annotate()
            user.total_points = user.filtered_total_points  # type: ignore[attr-defined]
            user.exact_match_count = user.filtered_exact_count  # type: ignore[attr-defined]
            user.jokers_used = user.filtered_jokers_used  # type: ignore[attr-defined]
            user_list.append(user)

        return RankingService._calculate_rank_numbers(user_list)

    @staticmethod
    def get_current_leaderboard() -> list[dict]:
        """
        Generate the current leaderboard with rankings.

        Uses stored global_rank for efficiency. Falls back to dynamic
        calculation if ranks are not populated.

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
        # Check if ranks are populated
        has_ranks = UserModel.objects.filter(is_active=True, global_rank__isnull=False).exists()

        if has_ranks:
            # Use stored ranks
            users = UserModel.objects.filter(is_active=True, global_rank__isnull=False).order_by(
                "global_rank"
            )

            return [
                {
                    "rank": user.global_rank,
                    "user_id": user.pk,
                    "username": user.username,
                    "total_points": user.total_points,
                    "exact_match_count": user.exact_match_count,
                    "jokers_used": user.jokers_used,
                }
                for user in users
            ]

        # Fallback: Calculate dynamically
        return RankingService.get_leaderboard_up_to_round(round_code=None)

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

        # Convert users to dicts
        result = [
            {
                "user_id": user.pk,
                "username": user.username,
                "total_points": user.total_points,
                "exact_match_count": user.exact_match_count,
                "jokers_used": user.jokers_used,
            }
            for user in users
        ]

        # Apply Olympic-style ranking
        def tiebreaker(a: dict, b: dict) -> bool:
            return (
                a["total_points"] == b["total_points"]
                and a["exact_match_count"] == b["exact_match_count"]
                and a["jokers_used"] == b["jokers_used"]
            )

        apply_olympic_ranking(result, tiebreaker)

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
        leaderboard = RankingService.get_current_leaderboard()

        snapshot = LeaderboardSnapshot.objects.create(
            snapshot_type=snapshot_type,
            data=leaderboard,
        )

        return snapshot

    @staticmethod
    @transaction.atomic
    def recalculate_user_score(user: UserModel) -> None:
        """
        Recalculate scoring for a single user.

        Recalculates total_points, exact_match_count, and jokers_used
        based on all scored predictions. Champion bonus points are NOT
        included here - they are managed separately via update_live_champion_bonuses.

        Args:
            user: User instance to recalculate
        """
        # Lazy import to avoid circular dependency
        from predictions.models import MatchPrediction

        # Calculate points from match predictions
        predictions = MatchPrediction.objects.filter(
            user=user,
            points_earned__isnull=False,
        )

        total_points = 0
        exact_match_count = 0
        jokers_used = 0

        for prediction in predictions:
            total_points += prediction.points_earned or 0
            if prediction.is_exact_match:
                exact_match_count += 1
            if prediction.joker_active:
                jokers_used += 1

        # Update user with recalculated values
        # Note: Champion bonus is handled separately by update_live_champion_bonuses
        user.total_points = total_points + user.champion_bonus_points
        user.exact_match_count = exact_match_count
        user.jokers_used = jokers_used
        user.save(update_fields=["total_points", "exact_match_count", "jokers_used"])

    @staticmethod
    @transaction.atomic
    def update_all_user_ranks() -> int:
        """
        Calculate Olympic-style ranking and persist to User.global_rank.

        Uses the same tiebreaker logic as get_current_leaderboard():
        1. Total points (higher is better)
        2. Exact match count (higher is better)
        3. Jokers used (fewer is better)

        Returns:
            Number of users updated
        """
        # Get all active users sorted by ranking criteria
        users = list(
            UserModel.objects.filter(is_active=True)
            .select_for_update()
            .order_by("-total_points", "-exact_match_count", "jokers_used")
        )

        if not users:
            return 0

        # Apply Olympic ranking
        current_rank = 1
        users_at_rank = 0
        prev_user = None

        for user in users:
            if prev_user is not None:
                same_rank = (
                    user.total_points == prev_user.total_points
                    and user.exact_match_count == prev_user.exact_match_count
                    and user.jokers_used == prev_user.jokers_used
                )
                if not same_rank:
                    current_rank += users_at_rank
                    users_at_rank = 1
                else:
                    users_at_rank += 1
            else:
                users_at_rank = 1

            user.global_rank = current_rank
            prev_user = user

        # Bulk update all ranks
        UserModel.objects.bulk_update(users, ["global_rank"])

        return len(users)
