"""
User views for the tipapp application.
"""

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from scoring.services import RankingService
from users.models import User


class RankingView(LoginRequiredMixin, TemplateView):
    """
    Display the current tournament ranking for all users.

    Shows olympic-style ranking with shared ranks for ties.
    Displays username, rank, total points, predicted champion with flag,
    exact match count, and jokers used.
    """

    template_name = "ranking.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Build context with enriched leaderboard data.

        Calls RankingService for base ranking, then enriches with
        predicted_champion data fetched in a single query.

        Returns:
            Context dict with 'leaderboard' containing ranked user data.
        """
        context = super().get_context_data(**kwargs)

        # Get base leaderboard from ranking service
        leaderboard = RankingService.get_current_leaderboard()

        if leaderboard:
            # Extract user IDs for champion data enrichment
            user_ids = [entry["user_id"] for entry in leaderboard]

            # Fetch users with champion in one query (no N+1)
            users_dict = {
                user.pk: user
                for user in User.objects.filter(pk__in=user_ids).select_related(
                    "predicted_champion"
                )
            }

            # Enrich leaderboard with champion data and country_code
            for entry in leaderboard:
                user = users_dict.get(entry["user_id"])
                if user:
                    entry["predicted_champion"] = user.predicted_champion
                    entry["country_code"] = user.country_code
                else:
                    entry["predicted_champion"] = None
                    entry["country_code"] = ""

        context["leaderboard"] = leaderboard
        return context
