"""Admin configuration for predictions app."""

from django.contrib import admin

from .models import MatchPrediction


@admin.register(MatchPrediction)
class MatchPredictionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin interface for MatchPrediction model."""

    list_display = [
        "user",
        "match",
        "predicted_score",
        "joker_active",
        "created_at",
        "points_earned",
    ]
    list_filter = ["joker_active", "user"]
    search_fields = [
        "user__username",
        "user__email",
        "match__team_home__name",
        "match__team_away__name",
    ]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Predicted Score")
    def predicted_score(self, obj: MatchPrediction) -> str:
        """Display predicted score in list view."""
        return f"{obj.predicted_goals_home}-{obj.predicted_goals_away}"
