from __future__ import annotations

import logging
from typing import Any

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from matches.signals import match_result_entered

logger = logging.getLogger(__name__)


class Tournament(models.Model):
    """Tournament-wide configuration for a single tipping game."""

    name: models.CharField = models.CharField(
        max_length=100, help_text="Tournament name (e.g., WM 2026)"
    )
    slug: models.SlugField = models.SlugField(
        max_length=50, unique=True, help_text="Short identifier (e.g., wm-2026)"
    )
    api_competition_code: models.CharField = models.CharField(
        max_length=10,
        help_text="football-data.org competition code (e.g., WC for World Cup, EC for Euro)",
    )
    api_season: models.IntegerField = models.IntegerField(
        null=True, blank=True, help_text="football-data.org season year, if the API requires one"
    )
    lock_buffer_minutes: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=3, help_text="Minutes before kickoff after which predictions are locked"
    )
    is_active: models.BooleanField = models.BooleanField(
        default=False, help_text="The one tournament this installation is currently running"
    )

    class Meta:
        db_table = "matches_tournament"
        ordering = ["name"]
        verbose_name = "Tournament"
        verbose_name_plural = "Tournaments"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="unique_active_tournament",
            ),
        ]

    def __str__(self) -> str:
        return str(self.name)


class Round(models.Model):
    """One round of a tournament together with its scoring and prediction parameters."""

    tournament: models.ForeignKey = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name="rounds",
        help_text="Tournament this round belongs to",
    )
    code: models.CharField = models.CharField(
        max_length=10, help_text="Short round code (e.g., group, r16, final)"
    )
    label: models.CharField = models.CharField(
        max_length=50, help_text="Display label (e.g., Sechzehntelfinale)"
    )
    order: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        help_text="Position of the round within the tournament, ascending"
    )
    multiplier: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Factor applied to the base points of every prediction in this round",
    )
    joker_count: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=0, help_text="Number of jokers available in this round or its joker pool"
    )
    joker_multiplier: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=2, help_text="Factor applied to the round score when a joker is active"
    )
    joker_pool: models.CharField = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Shared joker pool key; rounds with the same key share one joker limit",
    )
    prediction_limit: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of matches that may be predicted in this round; empty means all",
    )
    is_final: models.BooleanField = models.BooleanField(
        default=False, help_text="Marks the round that decides the champion"
    )
    api_stage: models.CharField = models.CharField(
        max_length=30, help_text="football-data.org stage name (e.g., ROUND_OF_16)"
    )

    class Meta:
        db_table = "matches_round"
        ordering = ["order"]
        verbose_name = "Round"
        verbose_name_plural = "Rounds"
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "code"], name="unique_round_code_per_tournament"
            ),
            models.UniqueConstraint(
                fields=["tournament", "order"], name="unique_round_order_per_tournament"
            ),
            models.UniqueConstraint(
                fields=["tournament", "api_stage"], name="unique_round_api_stage_per_tournament"
            ),
            models.UniqueConstraint(
                fields=["tournament"],
                condition=Q(is_final=True),
                name="unique_final_round_per_tournament",
            ),
        ]

    def __str__(self) -> str:
        return str(self.label)

    @property
    def effective_joker_pool(self) -> str:
        """Return the joker pool key, falling back to the round code for unpooled rounds."""
        return str(self.joker_pool or self.code)


class Team(models.Model):
    """Represents a country/team participating in the configured tournament."""

    name: models.CharField = models.CharField(max_length=100, help_text="Team name (e.g., Germany)")
    fifa_code: models.CharField = models.CharField(
        max_length=3, unique=True, help_text="FIFA country code (e.g., GER)"
    )
    champion_points: models.IntegerField = models.IntegerField(
        default=0,
        help_text="Bonus points awarded to users who picked this team as champion",
    )

    class Meta:
        db_table = "matches_team"
        ordering = ["name"]
        verbose_name = "Team"
        verbose_name_plural = "Teams"

    def __str__(self) -> str:
        return str(self.name)


class Match(models.Model):
    """
    Represents a match between two teams in World Cup 2026.

    When saved with goals_home and goals_away set, automatically triggers
    scoring of all predictions for this match via ScoringService.
    For the final match, also triggers champion prediction scoring.
    """

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("live", "Live"),
        ("finished", "Finished"),
    ]

    WINNER_CHOICES = [
        ("home", "Home Team"),
        ("away", "Away Team"),
        ("draw", "Draw"),
    ]

    # Fields that can change the outcome of scoring:
    # goals_home/goals_away feed the points formula, winner decides a penalty-shootout
    # champion, and status gates whether a final counts as decided.
    SCORING_RELEVANT_FIELDS = ("goals_home", "goals_away", "winner", "status")

    external_id: models.IntegerField = models.IntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="External match ID from football-data.org API",
        db_index=True,
    )
    team_home: models.ForeignKey = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name="home_matches", help_text="Home team"
    )
    team_away: models.ForeignKey = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name="away_matches", help_text="Away team"
    )
    kickoff: models.DateTimeField = models.DateTimeField(help_text="Match start time")
    round: models.ForeignKey = models.ForeignKey(
        Round, on_delete=models.PROTECT, related_name="matches", help_text="Tournament round"
    )
    goals_home: models.IntegerField = models.IntegerField(
        null=True, blank=True, help_text="Goals scored by home team"
    )
    goals_away: models.IntegerField = models.IntegerField(
        null=True, blank=True, help_text="Goals scored by away team"
    )
    winner: models.CharField = models.CharField(
        max_length=10,
        choices=WINNER_CHOICES,
        default="",
        blank=True,
        help_text="Match winner from API (home/away/draw). For knockout matches with penalties, "
        "this shows the actual winner while goals_home/goals_away contain the score before penalties.",
    )
    status: models.CharField = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="scheduled", help_text="Match status"
    )

    class Meta:
        db_table = "matches_match"
        ordering = ["kickoff"]
        verbose_name = "Match"
        verbose_name_plural = "Matches"

    def __str__(self) -> str:
        if (
            self.status == "finished"
            and self.goals_home is not None
            and self.goals_away is not None
        ):
            return (
                f"{self.team_home.name} {self.goals_home}-{self.goals_away} {self.team_away.name}"
            )
        return f"{self.team_home.name} vs {self.team_away.name} ({self.round.label})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save the match and trigger scoring if results are set.

        Sends the match_result_entered signal when both goals are set and any
        scoring-relevant field (SCORING_RELEVANT_FIELDS) changed, or when the row was
        newly created with both goals already set. Saves that only touch unrelated
        fields (kickoff, round, teams, external_id) send nothing.

        Signal receivers handle:
        1. Scoring all predictions for this match
        2. Updating champion bonuses if this is the final match
        """
        previous: dict[str, Any] | None = None

        if self.pk:
            previous = (
                Match.objects.filter(pk=self.pk).values(*self.SCORING_RELEVANT_FIELDS).first()
            )

        super().save(*args, **kwargs)

        if self.goals_home is None or self.goals_away is None:
            return

        changed = previous is None or any(
            previous[field] != getattr(self, field) for field in self.SCORING_RELEVANT_FIELDS
        )

        if changed:
            match_result_entered.send(sender=self.__class__, match=self)
