"""Prediction models for the tipapp application."""

from django.db import models


class MatchPrediction(models.Model):
    """
    User prediction for a match result.

    Stores the predicted goals for both teams and tracks whether
    the user activated a joker (double points) for this match.
    Enforces one prediction per user per match via unique_together.

    Scoring fields (points_earned, is_exact_match) are populated by
    the ScoringService when match results are entered.
    """

    user: models.ForeignKey = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="match_predictions",
        help_text="The user making this prediction",
    )

    match: models.ForeignKey = models.ForeignKey(
        "matches.Match",
        on_delete=models.CASCADE,
        related_name="predictions",
        help_text="The match being predicted",
    )

    predicted_goals_home: models.IntegerField = models.IntegerField(
        help_text="Predicted goals for home team"
    )

    predicted_goals_away: models.IntegerField = models.IntegerField(
        help_text="Predicted goals for away team"
    )

    joker_active: models.BooleanField = models.BooleanField(
        default=False,
        help_text="Whether joker is active for this prediction (double points)",
    )

    points_earned: models.IntegerField = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points earned after match result entered (calculated by ScoringService)",
    )

    is_exact_match: models.BooleanField = models.BooleanField(
        default=False, help_text="Whether prediction was an exact score match (6 base points)"
    )

    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True,
        help_text="When this prediction was created",
    )

    updated_at: models.DateTimeField = models.DateTimeField(
        auto_now=True,
        help_text="When this prediction was last updated",
    )

    class Meta:
        db_table = "predictions_matchprediction"
        unique_together = [["user", "match"]]
        ordering = ["match__kickoff"]
        verbose_name = "match prediction"
        verbose_name_plural = "match predictions"

    def __str__(self) -> str:
        return f"{self.user.username}: {self.match} ({self.predicted_goals_home}-{self.predicted_goals_away})"
