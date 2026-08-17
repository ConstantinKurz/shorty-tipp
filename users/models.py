"""User models for the tipapp application."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.

    Currently inherits all fields from AbstractUser:
    - username
    - first_name
    - last_name
    - email
    - password
    - is_staff
    - is_active
    - is_superuser
    - last_login
    - date_joined

    Additional fields:
    - predicted_champion: The team this user predicts will win the tournament
    - total_points: Cached total points for leaderboard ranking
    - exact_match_count: Number of exact score predictions for tiebreaker
    - jokers_used: Number of jokers used on scored predictions for tiebreaker
    - theme_preference: User's preferred color theme (light, dark, system)
    """

    THEME_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
        ("system", "System"),
    ]

    predicted_champion: models.ForeignKey = models.ForeignKey(
        "matches.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="champion_predictions",
        help_text="The team this user predicts will win the tournament",
    )

    total_points: models.IntegerField = models.IntegerField(
        default=0,
        help_text="Cached total points from all scored predictions (including champion bonus)"
    )

    exact_match_count: models.IntegerField = models.IntegerField(
        default=0,
        help_text="Number of predictions with exact score match (first tiebreaker)"
    )

    jokers_used: models.IntegerField = models.IntegerField(
        default=0,
        help_text="Number of jokers used on scored predictions (second tiebreaker)"
    )

    champion_bonus_points: models.IntegerField = models.IntegerField(
        default=0,
        help_text="Champion prediction bonus points (20 for category A, 30 for category B). Updated live during final."
    )

    theme_preference: models.CharField = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default="system",
        help_text="User's preferred color theme"
    )

    class Meta:
        db_table = "users_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.username
