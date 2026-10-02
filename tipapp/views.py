"""
Core views for the tipapp project.

Contains cross-cutting views that aggregate data from multiple apps,
such as the home page.
"""

from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from matches.models import Match, Round
from predictions.forms import PredictionForm
from predictions.models import MatchPrediction
from predictions.services import PredictionLimitService, get_polling_interval
from scoring.ranking_service import RankingService
from users.models import User


def _get_available_rounds() -> list[dict[str, Any]]:
    """Return the rounds of the active tournament as code/label dicts for the filter."""
    return [
        {"code": row["code"], "label": row["label"]}
        for row in Round.objects.filter(tournament__is_active=True).values("code", "label")
    ]


def _get_validated_round(request: HttpRequest) -> str | None:
    """
    Get and validate round filter from query params.

    Args:
        request: The HTTP request containing potential 'round' query param

    Returns:
        Valid round code or None if not specified or invalid
    """
    selected_round = request.GET.get("round")
    if selected_round and selected_round not in [r["code"] for r in _get_available_rounds()]:
        return None
    return selected_round


def _get_ranking_context(user: User, selected_round: str | None) -> dict[str, Any]:
    """
    Shared ranking logic for HomeView and RankingUpdatesView.

    Args:
        user: The current user
        selected_round: Round code to filter by (None for all rounds)

    Returns:
        Dict containing compact_leaderboard, full_leaderboard, and user_rank_entry
    """
    full_leaderboard = RankingService.get_leaderboard_up_to_round(round_code=selected_round)

    # Enrich with champion data
    if full_leaderboard:
        user_ids = [entry["user_id"] for entry in full_leaderboard]
        users_dict = {
            u.pk: u
            for u in User.objects.filter(pk__in=user_ids).select_related("predicted_champion")
        }
        for entry in full_leaderboard:
            u = users_dict.get(entry["user_id"])
            if u:
                entry["predicted_champion"] = u.predicted_champion
            else:
                entry["predicted_champion"] = None

    # Find user position
    user_rank_entry = None
    user_index = None
    for idx, entry in enumerate(full_leaderboard):
        if entry["user_id"] == user.id:
            user_rank_entry = entry
            user_index = idx
            break

    # Compact leaderboard
    compact_leaderboard = []
    if user_index is not None:
        start = max(0, user_index - 2)
        end = min(len(full_leaderboard), start + 5)
        if end - start < 5:
            start = max(0, end - 5)
        compact_leaderboard = full_leaderboard[start:end]
    elif full_leaderboard:
        compact_leaderboard = full_leaderboard[:5]

    return {
        "compact_leaderboard": compact_leaderboard,
        "full_leaderboard": full_leaderboard,
        "user_rank_entry": user_rank_entry,
    }


class HomeView(LoginRequiredMixin, TemplateView):
    """
    Home page view showing user rank, compact ranking, and next matches.

    This view consolidates the most important information for users:
    - Their current rank and points
    - A compact view of nearby competitors in the ranking
    - The next 3 upcoming matches for quick tipping

    The full ranking can be expanded inline with round filtering via HTMX.
    """

    template_name = "home.html"

    def get_template_names(self) -> list[str]:
        """Return partial for HTMX requests, full page otherwise."""
        if self.request.headers.get("HX-Request"):
            return ["partials/ranking_content.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Build context for home page.

        Returns:
            Context dict containing:
            - selected_round: Current round filter (None for Live, or round code)
            - available_rounds: List of round options for filter
            - user_rank_entry: Current user's ranking data (or None)
            - compact_leaderboard: List of 5 entries near user
            - full_leaderboard: Complete ranking (filtered by round if applicable)
            - matches_data: Up to 3 upcoming matches with prediction forms
        """
        context = super().get_context_data(**kwargs)
        # LoginRequiredMixin guarantees an authenticated user here.
        user = cast("User", self.request.user)

        # Get round filter and ranking data
        selected_round = _get_validated_round(self.request)
        ranking_context = _get_ranking_context(user, selected_round)

        # Get next 3 upcoming matches
        now = timezone.now()
        upcoming_matches = list(
            Match.objects.filter(kickoff__gt=now)
            .order_by("kickoff")
            .select_related("team_home", "team_away", "round", "round__tournament")[:3]
        )

        # Get user's predictions for those matches
        predictions_dict = {}
        if upcoming_matches:
            match_ids = [m.id for m in upcoming_matches]
            predictions = MatchPrediction.objects.filter(user=user, match_id__in=match_ids)
            predictions_dict = {p.match_id: p for p in predictions}

        # Build match data (similar to predictions view)
        matches_data = []
        for match in upcoming_matches:
            prediction = predictions_dict.get(match.id)
            is_locked = match.kickoff <= now

            joker_limit = PredictionLimitService.get_joker_limit_for_round(match.round)
            joker_count = (
                PredictionLimitService.get_joker_count_for_round(user, match.round)
                if joker_limit
                else 0
            )

            # Create form for this match
            form = PredictionForm(
                initial={
                    "predicted_goals_home": prediction.predicted_goals_home if prediction else None,
                    "predicted_goals_away": prediction.predicted_goals_away if prediction else None,
                }
            )

            matches_data.append(
                {
                    "match": match,
                    "prediction": prediction,
                    "form": form,
                    "is_locked": is_locked,
                    "joker_limit": joker_limit,
                    "joker_count": joker_count,
                }
            )

        context.update(
            {
                "selected_round": selected_round,
                "available_rounds": _get_available_rounds(),
                "matches_data": matches_data,
                "ranking_interval": get_polling_interval(),
                "leaderboard": ranking_context[
                    "full_leaderboard"
                ],  # For ranking_content.html compatibility
                **ranking_context,
            }
        )

        return context


class RankingUpdatesView(LoginRequiredMixin, View):
    """
    HTMX endpoint for polling ranking updates.

    Returns updated ranking partials (both compact and full) using out-of-band swaps.
    Triggered by client-side polling on the home page.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handle GET request for ranking updates."""
        # LoginRequiredMixin guarantees an authenticated user here.
        user = cast("User", request.user)

        # Get round filter and ranking data
        selected_round = _get_validated_round(request)
        ranking_context = _get_ranking_context(user, selected_round)

        context = {
            "selected_round": selected_round,
            "available_rounds": _get_available_rounds(),
            "leaderboard": ranking_context["full_leaderboard"],
            **ranking_context,
        }

        return render(request, "partials/ranking_updates.html", context)
