"""
User views for the tipapp application.
"""

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic.edit import UpdateView

from matches.models import Match, Team
from scoring.services import RankingService
from users.forms import UserSettingsForm
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


class UserSettingsView(LoginRequiredMixin, UpdateView):
    """
    View for users to manage their profile settings.

    Allows users to update:
    - Username (max 20 characters)
    - Email address
    - Predicted World Cup champion (before first match only)
    - Theme preference (light/dark/system)
    """

    model = User
    form_class = UserSettingsForm
    template_name = "users/settings.html"
    success_url = reverse_lazy("users:settings")

    def get_object(self, queryset: Any = None) -> User:
        """Return the current logged-in user."""
        return self.request.user  # type: ignore[return-value]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add teams and champion lock status to context."""
        context = super().get_context_data(**kwargs)
        context["teams"] = Team.objects.all().order_by("name")
        context["can_change_champion"] = self.can_change_champion()
        return context

    def can_change_champion(self) -> bool:
        """
        Check if champion prediction can still be changed.

        Returns True if no matches exist or if the first match
        hasn't started yet.
        """
        first_match = Match.objects.order_by("kickoff").first()
        if not first_match:
            return True
        return timezone.now() < first_match.kickoff

    def form_valid(self, form: UserSettingsForm) -> Any:
        """Save form and show success message."""
        messages.success(self.request, "Einstellungen gespeichert!")
        return super().form_valid(form)
