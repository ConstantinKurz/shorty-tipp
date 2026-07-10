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
    """

    predicted_champion: models.ForeignKey = models.ForeignKey(
        "matches.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="champion_predictions",
        help_text="The team this user predicts will win the tournament",
    )

    class Meta:
        db_table = "users_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.username
