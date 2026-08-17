"""Prediction limit services for the tipapp application."""

from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from predictions.models import MatchPrediction

if TYPE_CHECKING:
    from matches.models import Match
    from users.models import User


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
    def is_match_locked(cls, match: "Match", reference_time=None) -> bool:
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
        return reference_time >= lock_time
