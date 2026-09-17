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

from matches.constants import ROUND_ORDER, get_available_rounds
from matches.models import Match, Team
from scoring.ranking_service import RankingService
from users.forms import UserSettingsForm
from users.models import User


class RulesView(TemplateView):
    """Display game rules and how-to guide."""

    template_name = "users/rules.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add page title to context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Rules & How to Play"
        return context


class RankingView(LoginRequiredMixin, TemplateView):
    """
    Display the current tournament ranking for all users.

    Shows olympic-style ranking with shared ranks for ties.
    Displays username, rank, total points, predicted champion with flag,
    exact match count, and jokers used.
    """

    template_name = "ranking.html"

    def get_template_names(self) -> list[str]:
        """
        Return partial template for HTMX requests, full page otherwise.
        HTMX requests renders filtered ranking by group stage.
        """
        if self.request.headers.get("HX-Request"):
            return ["partials/ranking_content.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Build context with enriched leaderboard data.

        Calls RankingService for base ranking, then enriches with
        predicted_champion data fetched in a single query.
        Supports round filtering via ?round=<code> query parameter.

        Returns:
            Context dict with 'leaderboard', 'selected_round', and 'available_rounds'.
        """
        context = super().get_context_data(**kwargs)

        # Get round filter from query params
        round_filter = self.request.GET.get("round", None)

        # Validate round parameter
        if round_filter and round_filter not in ROUND_ORDER:
            round_filter = None

        # Get filtered leaderboard
        leaderboard = RankingService.get_leaderboard_up_to_round(round_filter)

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

            # Enrich leaderboard with champion data
            for entry in leaderboard:
                user = users_dict.get(entry["user_id"])
                if user:
                    entry["predicted_champion"] = user.predicted_champion
                else:
                    entry["predicted_champion"] = None

        context["leaderboard"] = leaderboard
        context["selected_round"] = round_filter
        context["available_rounds"] = get_available_rounds()
        return context


class UserSettingsView(LoginRequiredMixin, UpdateView):
    """
    View for users to manage their profile settings.

    Allows users to update:
    - Username (max 20 characters)
    - Email address
    - Predicted World Cup champion (before first match only, enforced server-side
      by removing the field from the form once the lock applies)
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

    def get_form_kwargs(self) -> dict[str, Any]:
        """Pass the champion lock state into the form."""
        kwargs = super().get_form_kwargs()
        kwargs["champion_locked"] = not self.can_change_champion()
        return kwargs

    def form_valid(self, form: UserSettingsForm) -> Any:
        """Save form and show success message."""
        messages.success(self.request, "Einstellungen gespeichert!")
        return super().form_valid(form)
