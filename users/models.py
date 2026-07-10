"""User models for the tipapp application."""

from django.contrib.auth.models import AbstractUser


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

    Can be extended with additional fields in future changes.
    """

    class Meta:
        db_table = "users_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.username
