"""Admin configuration for users app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""

    list_display = [
        "username",
        "email",
        "total_points",
        "exact_match_count",
        "jokers_used",
        "champion_bonus_points",
        "is_staff",
        "is_active",
    ]
    list_filter = [
        "is_staff",
        "is_active",
        "is_superuser",
        "date_joined",
    ]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-total_points", "-exact_match_count", "jokers_used", "username"]
    readonly_fields = ["total_points", "exact_match_count", "jokers_used", "champion_bonus_points"]

    # Extend BaseUserAdmin fieldsets to include predictions and statistics
    fieldsets = (
        *(BaseUserAdmin.fieldsets or ()),
        (
            "Predictions",
            {
                "fields": ("predicted_champion",),
            },
        ),
        (
            "Statistics (read-only, calculated by scoring service)",
            {
                "fields": (
                    "total_points",
                    "exact_match_count",
                    "jokers_used",
                    "champion_bonus_points",
                ),
            },
        ),
    )
