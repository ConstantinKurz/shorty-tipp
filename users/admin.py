"""Admin configuration for users app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):  # type: ignore[type-arg]
    """Admin interface for User model."""

    list_display = ["username", "email", "first_name", "last_name", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_active", "is_superuser", "date_joined"]
    search_fields = ["username", "email", "first_name", "last_name"]

    # Extend BaseUserAdmin fieldsets to include predictions
    fieldsets = BaseUserAdmin.fieldsets + (  # type: ignore[operator]
        (
            "Predictions",
            {
                "fields": ("predicted_champion",),
            },
        ),
    )
