"""Prediction limit services for the tipapp application."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.ranking import apply_olympic_ranking, create_tiebreaker_from_keys
from matches.constants import ROUND_ORDER as TOURNAMENT_PHASES
from matches.models import Match
from predictions.models import MatchPrediction

if TYPE_CHECKING:
    from users.models import User

# Polling configuration
POLLING_INTERVAL_ACTIVE = 15  # seconds - during active matches (balance between freshness and load)
POLLING_INTERVAL_IDLE = 60  # seconds - no active matches
MATCH_ACTIVE_WINDOW_MINUTES = 160  # kickoff + 160 min covers extra time + penalties


class PredictionLimitService:
    """
    Service for checking prediction and joker limits.

    Enforces the game rules for:
    - Joker limits per tournament round
    - Combined joker pool for semi-final, final, and third-place matches
    - Group stage prediction limit (max 36)
    """

    # Joker limits per round (configurable)
    # Group stage: no jokers allowed
    # r32/r16: 3 each
    # qf: 2
    # sf/final/3rd: 2 combined (shared pool)
    JOKER_LIMITS: dict[str, int] = {
        "group": 0,  # No jokers in group stage
        "r32": 3,
        "r16": 3,
        "qf": 2,
        "sf": 2,  # sf + final + 3rd share pool of 2
        "final": 2,  # Combined with sf
        "3rd": 2,  # Combined with sf
    }

    # Combined rounds that share joker pool
    COMBINED_ROUNDS: frozenset[str] = frozenset({"sf", "final", "3rd"})

    # Maximum group stage predictions allowed
    GROUP_STAGE_LIMIT: int = 36

    # Lock buffer: predictions close N minutes before kickoff
    LOCK_BUFFER_MINUTES: int = 3

    @classmethod
    def get_joker_limit_for_round(cls, round_code: str) -> int:
        """
        Get the maximum jokers allowed for a round.

        Args:
            round_code: Tournament round code (group, r32, r16, qf, sf, final, 3rd)

        Returns:
            Maximum number of jokers allowed for the round.
            Returns 0 for unknown rounds.
        """
        return cls.JOKER_LIMITS.get(round_code, 0)

    @classmethod
    def get_joker_count_for_round(cls, user: "User", round_code: str) -> int:
        """
        Count jokers user has set in a round (or combined rounds).

        For sf/final/3rd rounds, counts jokers across all three as they
        share a combined pool.

        Args:
            user: The user to check jokers for.
            round_code: Tournament round code.

        Returns:
            Number of active jokers in the round (or combined rounds).
        """
        if round_code in cls.COMBINED_ROUNDS:
            rounds = list(cls.COMBINED_ROUNDS)
        else:
            rounds = [round_code]

        return MatchPrediction.objects.filter(
            user=user,
            match__round__in=rounds,
            joker_active=True,
        ).count()

    @classmethod
    def can_add_joker(cls, user: "User", round_code: str) -> bool:
        """
        Check if user can add another joker in this round.

        Args:
            user: The user wanting to add a joker.
            round_code: Tournament round code.

        Returns:
            True if user has not reached the joker limit for this round.
        """
        limit = cls.get_joker_limit_for_round(round_code)
        current = cls.get_joker_count_for_round(user, round_code)
        return current < limit

    @classmethod
    def get_group_stage_prediction_count(cls, user: "User") -> int:
        """
        Count user's group stage predictions.

        Args:
            user: The user to count predictions for.

        Returns:
            Number of predictions the user has made for group stage matches.
        """
        return MatchPrediction.objects.filter(
            user=user,
            match__round="group",
        ).count()

    @classmethod
    def can_add_group_stage_prediction(cls, user: "User") -> bool:
        """
        Check if user can add another group stage prediction.

        Args:
            user: The user wanting to add a prediction.

        Returns:
            True if user has not reached the 36 group stage prediction limit.
        """
        return cls.get_group_stage_prediction_count(user) < cls.GROUP_STAGE_LIMIT

    @classmethod
    def is_match_locked(cls, match: "Match", reference_time: datetime | None = None) -> bool:
        """
        Check if predictions are locked for a match.

        Predictions close LOCK_BUFFER_MINUTES (3) minutes before kickoff.

        Args:
            match: The match to check lock status for.
            reference_time: Optional datetime to use instead of now (for testing).

        Returns:
            True if predictions are locked (current time >= kickoff - 3 minutes).
        """
        if reference_time is None:
            reference_time = timezone.now()

        lock_time = match.kickoff - timedelta(minutes=cls.LOCK_BUFFER_MINUTES)
        return bool(reference_time >= lock_time)


def get_polling_interval() -> int:
    """
    Determine polling interval based on active match windows.

    Active window: from kickoff until kickoff + 160 minutes.
    This covers regulation (90 min), extra time (30 min), and breaks (~40 min).

    Returns:
        Polling interval in seconds (10 during matches, 60 otherwise).
    """
    now = timezone.now()
    window_end = now - timedelta(minutes=MATCH_ACTIVE_WINDOW_MINUTES)

    # Match is "active" if kickoff is in the past but within the active window
    active_match_exists = (
        Match.objects.filter(
            kickoff__lte=now,  # Started
            kickoff__gt=window_end,  # Within active window
        )
        .exclude(status="finished")
        .exists()
    )

    return POLLING_INTERVAL_ACTIVE if active_match_exists else POLLING_INTERVAL_IDLE


def get_phase_stats(user: "User") -> dict[str, dict[str, Any]]:
    """
    Calculate prediction and joker counts per tournament phase.

    Args:
        user: The authenticated user to get stats for.

    Returns:
        Dict mapping phase code to stats dict containing:
        - predictions: Number of predictions user has made
        - jokers: Number of active jokers user has set
        - total_matches: Total matches in this phase
        - joker_limit: Maximum jokers allowed for this phase
    """
    stats: dict[str, dict[str, Any]] = {}

    # Get match counts per phase in one query
    match_counts = dict(
        Match.objects.values("round").annotate(count=Count("id")).values_list("round", "count")
    )

    # Get prediction counts per phase in one query
    prediction_data = (
        MatchPrediction.objects.filter(user=user)
        .values("match__round")
        .annotate(
            count=Count("id"),
            joker_count=Count("id", filter=Q(joker_active=True)),
        )
    )
    # Build lookup: phase -> (count, joker_count)
    prediction_counts: dict[str, tuple[int, int]] = {
        row["match__round"]: (row["count"], row["joker_count"]) for row in prediction_data
    }

    for phase in TOURNAMENT_PHASES:
        pred_count, joker_count = prediction_counts.get(phase, (0, 0))

        # For group stage, use prediction limit (36) instead of total matches (72)
        if phase == "group":
            display_total = PredictionLimitService.GROUP_STAGE_LIMIT
        else:
            display_total = match_counts.get(phase, 0)

        stats[phase] = {
            "predictions": pred_count,
            "jokers": joker_count,
            "total_matches": display_total,
            "joker_limit": PredictionLimitService.get_joker_limit_for_round(phase),
        }

    return stats


def build_match_predictions_list(
    match: Match,
    sort_mode: str,
    current_user: "User",
) -> list[dict[str, Any]]:
    """
    Build the predictions list for a match with rankings and statistics.

    Queries all active users, their predictions for the given match, and
    aggregates statistics (total points, exact matches, jokers used, champion).
    Applies Olympic-style ranking based on the selected sort mode.

    Args:
        match: The match to get predictions for.
        sort_mode: "match" (sort by match points) or "total" (sort by total points).
        current_user: The authenticated user viewing the list (not used in computation
            but kept for consistency with context building).

    Returns:
        List of prediction dicts, each containing:
        - user: User object
        - rank: Olympic-style rank (1, 1, 3, not 1, 2, 3 for ties)
        - has_predicted: Whether user has a prediction
        - predicted_goals_home: Home goals prediction or None
        - predicted_goals_away: Away goals prediction or None
        - joker_active: Whether joker is active on this prediction
        - points_earned: Points earned for this match or None
        - match_points: Same as points_earned but 0 instead of None
        - champion: User's predicted champion Team or None
        - exact_count: Total exact matches across all predictions
        - jokers_count: Total jokers used across all predictions
        - total_points: Total points across all predictions
    """
    User = get_user_model()

    # Get all active users with aggregated statistics
    users = (
        User.objects.filter(is_active=True)
        .annotate(
            stats_total_points=Coalesce(Sum("match_predictions__points_earned"), 0),
            stats_exact_count=Count(
                "match_predictions", filter=Q(match_predictions__is_exact_match=True)
            ),
            stats_jokers_count=Count(
                "match_predictions", filter=Q(match_predictions__joker_active=True)
            ),
        )
        .select_related("predicted_champion")
    )

    # Prefetch predictions for this specific match
    predictions_by_user = {
        p.user_id: p for p in MatchPrediction.objects.filter(match=match).select_related("user")
    }

    # Build list of user prediction items with all statistics
    user_predictions: list[dict[str, Any]] = []
    for user in users:
        pred = predictions_by_user.get(user.id)
        match_points = pred.points_earned if pred and pred.points_earned is not None else 0

        user_predictions.append(
            {
                "user": user,
                "prediction": pred,
                "predicted_goals_home": pred.predicted_goals_home if pred else None,
                "predicted_goals_away": pred.predicted_goals_away if pred else None,
                "joker_active": pred.joker_active if pred else False,
                "points_earned": pred.points_earned if pred else None,
                "has_predicted": pred is not None,
                # Aggregated statistics
                "match_points": match_points,
                "champion": user.predicted_champion,
                "exact_count": user.stats_exact_count,
                "jokers_count": user.stats_jokers_count,
                "total_points": user.stats_total_points,
            }
        )

    # Sort based on mode
    if sort_mode == "total":
        # Sort by official tiebreaker criteria:
        # 1. Total points (desc)
        # 2. Exact match count (desc)
        # 3. Jokers used (asc - fewer = better)
        # 4. Username (asc - final tiebreaker)
        user_predictions.sort(
            key=lambda x: (
                -x["total_points"],
                -x["exact_count"],
                x["jokers_count"],  # Ascending: fewer jokers used = better
                x["user"].username.lower(),
            )
        )
    else:
        # Sort by match points, then same tiebreakers:
        # 1. Match points (desc)
        # 2. Exact match count (desc)
        # 3. Jokers used (asc - fewer = better)
        # 4. Username (asc - final tiebreaker)
        user_predictions.sort(
            key=lambda x: (
                -x["match_points"],
                -x["exact_count"],
                x["jokers_count"],  # Ascending: fewer jokers used = better
                x["user"].username.lower(),
            )
        )

    # Apply Olympic-style ranking based on sort criterion
    if sort_mode == "total":
        tiebreaker = create_tiebreaker_from_keys("total_points", "exact_count", "jokers_count")
    else:
        tiebreaker = create_tiebreaker_from_keys("match_points", "exact_count", "jokers_count")

    apply_olympic_ranking(user_predictions, tiebreaker)

    return user_predictions
