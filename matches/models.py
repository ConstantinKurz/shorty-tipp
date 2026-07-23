from __future__ import annotations

import logging
from typing import Any

from django.db import models

logger = logging.getLogger(__name__)


class Team(models.Model):
    """Represents a country/team participating in World Cup 2026."""

    ODDS_CATEGORY_CHOICES = [
        ("A", "Category A (odds rank 1-8)"),
        ("B", "Category B (odds rank 9+)"),
    ]

    name: models.CharField = models.CharField(max_length=100, help_text="Team name (e.g., Germany)")
    fifa_code: models.CharField = models.CharField(
        max_length=3,
        unique=True,
        help_text="FIFA country code (e.g., GER)"
    )
    points: models.IntegerField = models.IntegerField(
        default=0,
        help_text="Championship points"
    )
    is_champion: models.BooleanField = models.BooleanField(
        default=False,
        help_text="Whether this team won the tournament"
    )
    odds_category: models.CharField = models.CharField(
        max_length=1,
        choices=ODDS_CATEGORY_CHOICES,
        null=True,
        blank=True,
        help_text="Champion prediction category: A (odds rank 1-8, 20pts) or B (rank 9+, 30pts). Set by admin based on betting odds."
    )

    class Meta:
        db_table = 'matches_team'
        ordering = ['name']
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'

    def __str__(self) -> str:
        return self.name


class Match(models.Model):
    """
    Represents a match between two teams in World Cup 2026.

    When saved with goals_home and goals_away set, automatically triggers
    scoring of all predictions for this match via ScoringService.
    For the final match, also triggers champion prediction scoring.
    """

    ROUND_CHOICES = [
        ('group', 'Group Stage'),
        ('r32', 'Round of 32'),
        ('r16', 'Round of 16'),
        ('qf', 'Quarter-Final'),
        ('sf', 'Semi-Final'),
        ('3rd', 'Third Place'),
        ('final', 'Final'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('finished', 'Finished'),
    ]

    team_home: models.ForeignKey = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name='home_matches',
        help_text="Home team"
    )
    team_away: models.ForeignKey = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name='away_matches',
        help_text="Away team"
    )
    kickoff: models.DateTimeField = models.DateTimeField(help_text="Match start time")
    round: models.CharField = models.CharField(
        max_length=10,
        choices=ROUND_CHOICES,
        help_text="Tournament round"
    )
    goals_home: models.IntegerField = models.IntegerField(
        null=True,
        blank=True,
        help_text="Goals scored by home team"
    )
    goals_away: models.IntegerField = models.IntegerField(
        null=True,
        blank=True,
        help_text="Goals scored by away team"
    )
    status: models.CharField = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='scheduled',
        help_text="Match status"
    )

    class Meta:
        db_table = 'matches_match'
        ordering = ['kickoff']
        verbose_name = 'Match'
        verbose_name_plural = 'Matches'

    def __str__(self) -> str:
        if self.status == 'finished' and self.goals_home is not None and self.goals_away is not None:
            return f"{self.team_home.name} {self.goals_home}-{self.goals_away} {self.team_away.name}"
        return f"{self.team_home.name} vs {self.team_away.name} ({self.get_round_display()})"  # type: ignore[attr-defined]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save the match and trigger scoring if results are set.

        When goals_home and goals_away are both set:
        1. Scores all predictions for this match
        2. If this is the final match, also scores champion predictions

        Scoring errors are logged but don't prevent the save.
        """
        super().save(*args, **kwargs)

        # Trigger scoring if match has results
        if self.goals_home is not None and self.goals_away is not None:
            try:
                from scoring.services import ScoringService

                scored_count = ScoringService.score_all_predictions_for_match(self)
                logger.info(
                    "Scored %d predictions for match %s",
                    scored_count,
                    self,
                )

                # For final match, also score champion predictions
                if self.round == "final" and self.status == "finished":
                    champion_count = ScoringService.score_champion_predictions()
                    if champion_count > 0:
                        logger.info(
                            "Awarded champion points to %d users",
                            champion_count,
                        )

            except Exception:
                logger.exception(
                    "Error scoring predictions for match %s",
                    self,
                )
