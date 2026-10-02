"""
Prediction views for the tipapp application.

Provides views for listing, saving, deleting predictions and toggling jokers.
All views use HTMX for seamless inline updates without full page reloads.
"""

import json
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from matches.models import Match
from matches.tournament import get_active_tournament
from predictions.forms import PredictionForm
from predictions.models import MatchPrediction
from predictions.services import (
    MATCH_ACTIVE_WINDOW_MINUTES,
    PredictionLimitService,
    build_match_predictions_list,
    get_phase_stats,
    get_polling_interval,
)

if TYPE_CHECKING:
    from users.models import User


class PredictionListView(LoginRequiredMixin, TemplateView):
    """
    Display all matches with inline prediction forms.

    Shows matches ordered by kickoff time, grouped by date.
    Displays match results, user predictions, points earned,
    and provides inline forms for editing predictions.
    """

    template_name = "predictions/prediction_list.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Build context with matches and prediction data.

        Returns:
            Context dict with matches data, prediction map, and limit info.
        """
        context = super().get_context_data(**kwargs)
        user: User = self.request.user  # type: ignore[assignment]
        now = timezone.now()

        # Get all matches ordered by kickoff
        matches = (
            Match.objects.all()
            .select_related("team_home", "team_away", "round", "round__tournament")
            .order_by("kickoff")
        )

        # Get user's predictions
        predictions = MatchPrediction.objects.filter(user=user).select_related("match")

        # Build prediction lookup
        prediction_map = {p.match.pk: p for p in predictions}

        # Build enriched matches data
        matches_data: list[dict[str, Any]] = []
        for match in matches:
            prediction = prediction_map.get(match.pk)
            is_locked = PredictionLimitService.is_match_locked(match, now)
            match_round = match.round

            # Joker info for this round
            can_add_joker = PredictionLimitService.can_add_joker(user, match_round)
            joker_count = PredictionLimitService.get_joker_count_for_round(user, match_round)
            joker_limit = PredictionLimitService.get_joker_limit_for_round(match_round)

            # Create form for this match
            form = PredictionForm(instance=prediction)

            matches_data.append(
                {
                    "match": match,
                    "prediction": prediction,
                    "form": form,
                    "is_locked": is_locked,
                    "can_add_joker": can_add_joker,
                    "joker_count": joker_count,
                    "joker_limit": joker_limit,
                    "has_prediction_limit": match_round.prediction_limit is not None,
                }
            )

        # Group by date
        matches_by_date: dict[str, list[dict[str, Any]]] = {}
        for item in matches_data:
            date_key = item["match"].kickoff.strftime("%Y-%m-%d")
            if date_key not in matches_by_date:
                matches_by_date[date_key] = []
            matches_by_date[date_key].append(item)

        context["matches_data"] = matches_data
        context["matches_by_date"] = matches_by_date

        # Phase navigation stats
        context["phase_stats"] = get_phase_stats(user)
        context["phase_stats_json"] = json.dumps(context["phase_stats"])
        context["tournament_phases"] = list(get_active_tournament().rounds.all())

        # Polling interval (dynamic based on active matches)
        context["polling_interval"] = get_polling_interval()

        return context


def _get_match_row_context(
    user: "User", match: Match, prediction: MatchPrediction | None, just_saved: bool = False
) -> dict[str, Any]:
    """
    Build context for rendering a single match row partial.

    Args:
        user: The authenticated user.
        match: The match object.
        prediction: The user's prediction for this match (or None).
        just_saved: Whether the prediction was just saved (shows success indicator).

    Returns:
        Context dict for the prediction_row.html template.
    """
    now = timezone.now()
    is_locked = PredictionLimitService.is_match_locked(match, now)
    match_round = match.round

    form = PredictionForm(instance=prediction)

    return {
        "match": match,
        "prediction": prediction,
        "form": form,
        "is_locked": is_locked,
        "can_add_joker": PredictionLimitService.can_add_joker(user, match_round),
        "joker_count": PredictionLimitService.get_joker_count_for_round(user, match_round),
        "joker_limit": PredictionLimitService.get_joker_limit_for_round(match_round),
        "has_prediction_limit": match_round.prediction_limit is not None,
        "round_prediction_count": PredictionLimitService.get_prediction_count_for_round(
            user, match_round
        ),
        "round_prediction_limit": match_round.prediction_limit,
        "just_saved": just_saved,
    }


def _get_match_predictions_form_context(
    user: "User", match: Match, prediction: MatchPrediction | None, just_saved: bool = False
) -> dict[str, Any]:
    """
    Build context for match predictions page form partial.

    Args:
        user: The authenticated user.
        match: The match object.
        prediction: The user's prediction for this match (or None).
        just_saved: Whether the prediction was just saved (shows success indicator).

    Returns:
        Context dict for current_user_prediction_form.html template.
    """
    now = timezone.now()
    is_locked = PredictionLimitService.is_match_locked(match, now)
    match_round = match.round

    return {
        "match": match,
        "current_user_prediction": prediction,
        "current_user_form": PredictionForm(instance=prediction),
        "is_locked": is_locked,
        "can_add_joker": PredictionLimitService.can_add_joker(user, match_round),
        "joker_count": PredictionLimitService.get_joker_count_for_round(user, match_round),
        "joker_limit": PredictionLimitService.get_joker_limit_for_round(match_round),
        "has_prediction_limit": match_round.prediction_limit is not None,
        "current_user": user,
        "just_saved": just_saved,
    }


class PredictionSaveView(LoginRequiredMixin, View):
    """
    Save or update a prediction via HTMX POST.

    Creates a new prediction or updates an existing one.
    Validates locktime and group stage limits.
    Returns the updated match row partial.
    """

    def post(self, request: HttpRequest, match_id: int) -> HttpResponse:
        """
        Handle POST request to save prediction.

        Args:
            request: The HTTP request.
            match_id: The ID of the match to predict.

        Returns:
            HTML partial of the updated match row, or error partial.
        """
        user: User = request.user  # type: ignore[assignment]
        match = get_object_or_404(
            Match.objects.select_related("team_home", "team_away", "round", "round__tournament"),
            pk=match_id,
        )
        now = timezone.now()

        # Check locktime
        if PredictionLimitService.is_match_locked(match, now):
            return render(
                request,
                "predictions/prediction_error.html",
                {"error": "Spiel bereits gestartet. Tipp nicht mehr möglich."},
                status=400,
            )

        # Check the round's prediction limit before creating a row, so the count never
        # includes the prediction currently being saved.
        with transaction.atomic():
            prediction = MatchPrediction.objects.filter(user=user, match=match).first()
            created = prediction is None

            if created and not PredictionLimitService.can_add_prediction(user, match.round):
                return render(
                    request,
                    "predictions/prediction_error.html",
                    {
                        "error": (
                            f"Limit erreicht: Max. {match.round.prediction_limit} Tipps "
                            f"in {match.round.label} erlaubt."
                        )
                    },
                    status=400,
                )

            if prediction is None:
                prediction = MatchPrediction.objects.create(
                    user=user,
                    match=match,
                    predicted_goals_home=0,
                    predicted_goals_away=0,
                )

        # Validate form
        form = PredictionForm(request.POST, instance=prediction)
        if not form.is_valid():
            # Restore original values if update failed
            if not created:
                prediction.refresh_from_db()
            else:
                prediction.delete()
            return render(
                request,
                "predictions/prediction_error.html",
                {"error": "Ungültige Eingabe. Tore müssen zwischen 0 und 99 liegen."},
                status=400,
            )

        form.save()

        # Check if request from match predictions page
        context_type = request.GET.get("context", "")
        if context_type == "match-predictions":
            context = _get_match_predictions_form_context(user, match, prediction)
            context["just_saved"] = True
            return render(
                request, "predictions/partials/current_user_prediction_form.html", context
            )

        context = _get_match_row_context(user, match, prediction, just_saved=True)
        return render(request, "predictions/prediction_row.html", context)


class PredictionDeleteView(LoginRequiredMixin, View):
    """
    Delete a prediction via HTMX POST.

    Removes the user's prediction for a match.
    Validates locktime before deletion.
    Returns a cleared match row partial.
    """

    def post(self, request: HttpRequest, match_id: int) -> HttpResponse:
        """
        Handle POST request to delete prediction.

        Args:
            request: The HTTP request.
            match_id: The ID of the match.

        Returns:
            HTML partial of the cleared match row, or error partial.
        """
        user: User = request.user  # type: ignore[assignment]
        match = get_object_or_404(
            Match.objects.select_related("team_home", "team_away", "round", "round__tournament"),
            pk=match_id,
        )
        now = timezone.now()

        # Check locktime
        if PredictionLimitService.is_match_locked(match, now):
            return render(
                request,
                "predictions/prediction_error.html",
                {"error": "Spiel bereits gestartet. Tipp kann nicht gelöscht werden."},
                status=400,
            )

        # Get and delete prediction
        prediction = get_object_or_404(
            MatchPrediction,
            user=user,
            match=match,
        )
        prediction.delete()

        # Check if request from match predictions page
        context_type = request.GET.get("context", "")
        if context_type == "match-predictions":
            context = _get_match_predictions_form_context(user, match, None)
            return render(
                request, "predictions/partials/current_user_prediction_form.html", context
            )

        context = _get_match_row_context(user, match, None)
        return render(request, "predictions/prediction_row.html", context)


class PredictionJokerView(LoginRequiredMixin, View):
    """
    Toggle joker on a prediction via HTMX POST.

    Enables or disables joker on an existing prediction.
    Validates locktime, round eligibility, and joker limits.
    Returns the updated match row partial.
    """

    def post(self, request: HttpRequest, match_id: int) -> HttpResponse:
        """
        Handle POST request to toggle joker.

        Args:
            request: The HTTP request.
            match_id: The ID of the match.

        Returns:
            HTML partial of the updated match row, or error partial.
        """
        user: User = request.user  # type: ignore[assignment]
        match = get_object_or_404(
            Match.objects.select_related("team_home", "team_away", "round", "round__tournament"),
            pk=match_id,
        )
        now = timezone.now()

        # Check locktime
        if PredictionLimitService.is_match_locked(match, now):
            return render(
                request,
                "predictions/prediction_error.html",
                {"error": "Spiel bereits gestartet. Joker kann nicht geändert werden."},
                status=400,
            )

        # Check round - a round with no jokers configured allows none
        if PredictionLimitService.get_joker_limit_for_round(match.round) == 0:
            return render(
                request,
                "predictions/prediction_error.html",
                {"error": f"Keine Joker in {match.round.label} erlaubt."},
                status=400,
            )

        # Get prediction - must exist to toggle joker
        prediction = MatchPrediction.objects.filter(
            user=user,
            match=match,
        ).first()

        if not prediction:
            return render(
                request,
                "predictions/prediction_error.html",
                {"error": "Erst einen Tipp abgeben, dann Joker setzen."},
                status=400,
            )

        # If enabling joker, check limit
        if not prediction.joker_active:
            if not PredictionLimitService.can_add_joker(user, match.round):
                return render(
                    request,
                    "predictions/prediction_error.html",
                    {"error": "Joker-Limit für diese Runde erreicht."},
                    status=400,
                )

        # Toggle joker
        prediction.joker_active = not prediction.joker_active
        prediction.save(update_fields=["joker_active", "updated_at"])

        # Check if request from match predictions page
        context_type = request.GET.get("context", "")
        if context_type == "match-predictions":
            context = _get_match_predictions_form_context(user, match, prediction, just_saved=True)
            return render(
                request, "predictions/partials/current_user_prediction_form.html", context
            )

        context = _get_match_row_context(user, match, prediction, just_saved=True)
        return render(request, "predictions/prediction_row.html", context)


class PredictionUpdatesView(LoginRequiredMixin, View):
    """
    Return match updates for HTMX polling.

    Returns finished matches that may have updated results.
    Uses HTMX OOB swap to update only changed match rows.
    Also returns updated polling interval via HX-Trigger header.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Handle GET request for match updates.

        Args:
            request: The HTTP request.

        Returns:
            HTML fragments with hx-swap-oob for live matches, or empty response. OOB to change multiple matches at once
            HX-Trigger header with updated polling interval.
        """
        # Calculate current polling interval
        polling_interval = get_polling_interval()
        now = timezone.now()

        # Find live/active matches (within active window, not finished yet)
        # These may have goals updating in real-time
        matches_to_update = (
            Match.objects.filter(
                kickoff__lte=now,
                kickoff__gt=now - timedelta(minutes=MATCH_ACTIVE_WINDOW_MINUTES),
            )
            .exclude(status="finished")
            .select_related("team_home", "team_away", "round", "round__tournament")
        )

        if not matches_to_update.exists():
            # No live matches, return empty response with polling interval
            response = HttpResponse("", content_type="text/html")
            response["HX-Trigger"] = json.dumps({"pollingInterval": polling_interval})
            return response

        # Get user's predictions for these matches
        user: User = request.user  # type: ignore[assignment]
        predictions = MatchPrediction.objects.filter(
            user=user,
            match__in=matches_to_update,
        ).select_related("match")
        prediction_map = {p.match.pk: p for p in predictions}

        # Build HTML fragments for matches with OOB swap
        html_parts = []
        for match in matches_to_update:
            prediction = prediction_map.get(match.pk)
            context = _get_match_row_context(user, match, prediction)

            row_html = render(
                request,
                "predictions/prediction_row.html",
                context,
            ).content.decode("utf-8")

            # Add hx-swap-oob attribute to the row
            row_html = row_html.replace(
                f'id="match-{match.pk}"',
                f'id="match-{match.pk}" hx-swap-oob="true"',
                1,
            )
            html_parts.append(row_html)

        response = HttpResponse("".join(html_parts), content_type="text/html")
        response["HX-Trigger"] = json.dumps({"pollingInterval": polling_interval})
        return response


class PhaseStatsView(LoginRequiredMixin, View):
    """
    Return phase statistics as JSON for HTMX/JavaScript updates.

    Called after prediction saves/deletes/joker toggles to refresh stats.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Handle GET request for phase statistics.

        Args:
            request: The HTTP request.

        Returns:
            JSON response with phase statistics.
        """
        user: User = request.user  # type: ignore[assignment]
        stats = get_phase_stats(user)
        return HttpResponse(json.dumps(stats), content_type="application/json")


class MatchPredictionsView(LoginRequiredMixin, TemplateView):
    """
    Display all predictions for a match on a dedicated page.

    Shows predictions from all users for the given match with aggregated
    user statistics: champion prediction, exact count, jokers used, and
    total points.

    Query Parameters:
        from: Origin page for back navigation ('home' or 'predictions').
              Defaults to 'predictions' if not provided or invalid.
        sort: Ranking sort mode ('match' for match points, 'total' for
              total points). Defaults to 'match' if not provided or invalid.
    """

    template_name = "predictions/match_predictions_page.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Build context with match and all user predictions.

        Returns:
            Context dict with match, user_predictions, sort_mode, origin,
            and current_user.
        """
        context = super().get_context_data(**kwargs)
        match_id = self.kwargs["match_id"]
        match = get_object_or_404(
            Match.objects.select_related("team_home", "team_away", "round", "round__tournament"),
            pk=match_id,
        )

        # Get origin for back navigation (defaults to predictions)
        origin = self.request.GET.get("from", "predictions")
        if origin not in ("home", "predictions"):
            origin = "predictions"

        # Get sort mode from query parameter (default: match)
        sort_mode = self.request.GET.get("sort", "match")
        if sort_mode not in ("match", "total"):
            sort_mode = "match"

        # Build predictions list using shared helper
        user_predictions = build_match_predictions_list(
            match=match,
            sort_mode=sort_mode,
            current_user=self.request.user,  # type: ignore[arg-type]
        )

        # Calculate polling interval based on match activity
        polling_interval = get_polling_interval()

        # Calculate is_locked for header partial
        now = timezone.now()
        is_locked = PredictionLimitService.is_match_locked(match, now)

        # Build version from match score for polling optimization
        current_version = f"{match.goals_home}:{match.goals_away}"

        # Get current user's prediction for inline editing
        current_user_prediction = MatchPrediction.objects.filter(
            user=self.request.user,  # type: ignore[misc]
            match=match,
        ).first()

        # Build form for current user
        current_user_form = PredictionForm(instance=current_user_prediction)

        # Joker info for current user
        match_round = match.round
        can_add_joker = PredictionLimitService.can_add_joker(
            self.request.user,  # type: ignore[arg-type]
            match_round,
        )
        joker_count = PredictionLimitService.get_joker_count_for_round(
            self.request.user,  # type: ignore[arg-type]
            match_round,
        )
        joker_limit = PredictionLimitService.get_joker_limit_for_round(match_round)

        context.update(
            {
                "match": match,
                "user_predictions": user_predictions,
                "sort_mode": sort_mode,
                "origin": origin,
                "current_user": self.request.user,
                "polling_interval": polling_interval,
                "is_locked": is_locked,
                "current_version": current_version,
                "current_user_prediction": current_user_prediction,
                "current_user_form": current_user_form,
                "can_add_joker": can_add_joker,
                "joker_count": joker_count,
                "joker_limit": joker_limit,
                "has_prediction_limit": match_round.prediction_limit is not None,
            }
        )

        return context


class MatchPredictionsUpdateView(LoginRequiredMixin, View):
    """
    Return updated predictions list for HTMX polling.

    Returns only the predictions content partial, not the full page.
    Used for live updates on the match predictions page.

    Query Parameters:
        sort: Ranking sort mode ('match' for match points, 'total' for
              total points). Defaults to 'match' if not provided or invalid.
        from: Origin page tracking ('home' or 'predictions').
              Preserved in context for sort toggle links.
    """

    def get(self, request: HttpRequest, match_id: int) -> HttpResponse:
        """
        Handle GET request for partial predictions update.

        Args:
            request: The HTTP request.
            match_id: The ID of the match.

        Returns:
            HTML partial with updated predictions content.
            Includes HX-Trigger header with version for client-side tracking.
        """
        match = get_object_or_404(
            Match.objects.select_related("team_home", "team_away", "round", "round__tournament"),
            pk=match_id,
        )

        # Build version from match score
        current_version = f"{match.goals_home}:{match.goals_away}"
        # Read client's version from query params
        client_version = request.GET.get("version", "")

        # Calculate is_locked for optimization and context
        now = timezone.now()
        is_locked = PredictionLimitService.is_match_locked(match, now)

        # Optimization: skip rendering if post-kickoff and version unchanged
        # Post-kickoff predictions are locked, so only score changes matter.
        # If score (version) is unchanged, predictions and points are identical.
        if is_locked and client_version == current_version:
            response = HttpResponse("")
            response["HX-Trigger"] = json.dumps({"version": current_version})
            return response

        # Get sort mode from query params (default: match)
        sort_mode = request.GET.get("sort", "match")
        if sort_mode not in ("match", "total"):
            sort_mode = "match"

        # Get origin for preserving in sort toggle links
        origin = request.GET.get("from", "predictions")
        if origin not in ("home", "predictions"):
            origin = "predictions"

        # Get current user's prediction for inline editing
        current_user_prediction = MatchPrediction.objects.filter(
            user=request.user,  # type: ignore[misc]
            match=match,
        ).first()

        # Build form for current user
        current_user_form = PredictionForm(instance=current_user_prediction)

        # Joker info for current user
        match_round = match.round
        can_add_joker = PredictionLimitService.can_add_joker(
            request.user,  # type: ignore[arg-type]
            match_round,
        )
        joker_count = PredictionLimitService.get_joker_count_for_round(
            request.user,  # type: ignore[arg-type]
            match_round,
        )
        joker_limit = PredictionLimitService.get_joker_limit_for_round(match_round)

        # Build user predictions list using shared helper
        user_predictions = build_match_predictions_list(
            match=match,
            sort_mode=sort_mode,
            current_user=request.user,  # type: ignore[arg-type]
        )

        context = {
            "match": match,
            "user_predictions": user_predictions,
            "sort_mode": sort_mode,
            "current_user": request.user,
            "origin": origin,
            "is_locked": is_locked,
            "current_user_prediction": current_user_prediction,
            "current_user_form": current_user_form,
            "can_add_joker": can_add_joker,
            "joker_count": joker_count,
            "joker_limit": joker_limit,
            "has_prediction_limit": match_round.prediction_limit is not None,
        }

        response = render(
            request,
            "predictions/partials/match_predictions_updates.html",
            context,
        )
        response["HX-Trigger"] = json.dumps({"version": current_version})
        return response
