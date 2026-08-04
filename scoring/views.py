"""
Views for the scoring app.

Provides views for displaying rankings, leaderboards, and the home page.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from matches.constants import get_available_rounds
from matches.models import Match
from predictions.forms import PredictionForm
from predictions.models import MatchPrediction
from predictions.services import PredictionLimitService
from scoring.services import RankingService
from users.models import User


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

    def get_template_names(self):
        """Return partial for HTMX requests, full page otherwise."""
        if self.request.headers.get("HX-Request"):
            return ["partials/ranking_content.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
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
        user = self.request.user

        # Get round filter from query params
        selected_round = self.request.GET.get("round")
        if selected_round and selected_round not in [r["code"] for r in get_available_rounds()]:
            selected_round = None

        # Get full leaderboard (filtered by round if applicable)
        full_leaderboard = RankingService.get_leaderboard_up_to_round(round_code=selected_round)

        # Enrich leaderboard with champion data (avoid N+1)
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
                    entry["country_code"] = u.country_code
                else:
                    entry["predicted_champion"] = None
                    entry["country_code"] = ""

        # Find user's entry and position in leaderboard
        user_rank_entry = None
        user_index = None
        for idx, entry in enumerate(full_leaderboard):
            if entry["user_id"] == user.id:
                user_rank_entry = entry
                user_index = idx
                break

        # Build compact leaderboard (up to 5 entries centered around user)
        # Edge cases handled:
        # - User at rank 1: shows user + 4 below (or all available)
        # - User at last rank: shows user + 4 above (or all available)
        # - Fewer than 5 users: shows all available users
        # - User not in ranking: shows top 5 users
        compact_leaderboard = []
        if user_index is not None:
            # Center window of 5 around user (2 above + user + 2 below)
            start = max(0, user_index - 2)
            end = min(len(full_leaderboard), start + 5)
            # If hit end boundary, slide window back to get 5 entries
            if end - start < 5:
                start = max(0, end - 5)
            compact_leaderboard = full_leaderboard[start:end]
        elif full_leaderboard:
            # User not in ranking, show top 5
            compact_leaderboard = full_leaderboard[:5]
        # If no leaderboard at all, compact_leaderboard remains empty list

        # Get next 3 upcoming matches
        now = timezone.now()
        upcoming_matches = list(
            Match.objects.filter(kickoff__gt=now).order_by("kickoff").select_related(
                "team_home", "team_away"
            )[:3]
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
            is_group_stage = match.round == "group"

            # Get joker info for this match's round
            if is_group_stage:
                joker_limit = 0  # No jokers in group stage
                joker_count = 0
            else:
                joker_limit = PredictionLimitService.get_joker_limit_for_round(match.round)
                joker_count = PredictionLimitService.get_joker_count_for_round(user, match.round)

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
                    "is_group_stage": is_group_stage,
                    "joker_limit": joker_limit,
                    "joker_count": joker_count,
                }
            )

        context.update(
            {
                "selected_round": selected_round,
                "available_rounds": get_available_rounds(),
                "user_rank_entry": user_rank_entry,
                "compact_leaderboard": compact_leaderboard,
                "full_leaderboard": full_leaderboard,
                "leaderboard": full_leaderboard,  # For ranking_content.html compatibility
                "matches_data": matches_data,
            }
        )

        return context
