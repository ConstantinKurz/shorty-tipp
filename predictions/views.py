"""
Prediction views for the tipapp application.

Provides views for listing, saving, deleting predictions and toggling jokers.
All views use HTMX for seamless inline updates without full page reloads.
"""

import json
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from matches.models import Match
from predictions.forms import PredictionForm
from predictions.models import MatchPrediction
from predictions.services import PredictionLimitService

if TYPE_CHECKING:
    from users.models import User


# Tournament phases in display order
TOURNAMENT_PHASES = ["group", "r32", "r16", "qf", "sf", "3rd", "final"]

# Polling configuration
POLLING_INTERVAL_ACTIVE = 1  # seconds - during active matches
POLLING_INTERVAL_IDLE = 60  # seconds - no active matches
MATCH_ACTIVE_WINDOW_MINUTES = 160  # kickoff + 160 min covers extra time + penalties


def get_polling_interval() -> int:
    """
    Determine polling interval based on active match windows.

    Active window: from kickoff until kickoff + 160 minutes.
    This covers regulation (90 min), extra time (30 min), and breaks (~40 min).

    Returns:
        Polling interval in seconds (10 during matches, 60 otherwise).
    """
    now = timezone.now()
    window_end = now - timedelta(minutes=MATCH_ACTIVE_WINDOW_MINUTES)

    # Match is "active" if kickoff is in the past but within the active window
    active_match_exists = Match.objects.filter(
        kickoff__lte=now,  # Started
        kickoff__gt=window_end,  # Within active window
    ).exclude(status="finished").exists()

    return POLLING_INTERVAL_ACTIVE if active_match_exists else POLLING_INTERVAL_IDLE


def get_phase_stats(user: "User") -> dict[str, dict[str, Any]]:
    """
    Calculate prediction and joker counts per tournament phase.

    Args:
        user: The authenticated user to get stats for.

    Returns:
        Dict mapping phase code to stats dict containing:
        - predictions: Number of predictions user has made
        - jokers: Number of active jokers user has set
        - total_matches: Total matches in this phase
        - joker_limit: Maximum jokers allowed for this phase
    """
    stats: dict[str, dict[str, Any]] = {}

    # Get match counts per phase in one query
    match_counts = dict(
        Match.objects.values("round").annotate(count=Count("id")).values_list("round", "count")
    )

    # Get prediction counts per phase in one query
    prediction_data = (
        MatchPrediction.objects.filter(user=user)
        .values("match__round")
        .annotate(
            count=Count("id"),
            joker_count=Count("id", filter=Q(joker_active=True)),
        )
    )
    # Build lookup: phase -> (count, joker_count)
    prediction_counts: dict[str, tuple[int, int]] = {
        row["match__round"]: (row["count"], row["joker_count"])
        for row in prediction_data
    }

    for phase in TOURNAMENT_PHASES:
        pred_count, joker_count = prediction_counts.get(phase, (0, 0))

        # For group stage, use prediction limit (36) instead of total matches (72)
        if phase == "group":
            display_total = PredictionLimitService.GROUP_STAGE_LIMIT
        else:
            display_total = match_counts.get(phase, 0)

        stats[phase] = {
            "predictions": pred_count,
            "jokers": joker_count,
            "total_matches": display_total,
            "joker_limit": PredictionLimitService.get_joker_limit_for_round(phase),
        }

    return stats


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
        matches = Match.objects.all().select_related("team_home", "team_away").order_by("kickoff")

        # Get user's predictions
        predictions = MatchPrediction.objects.filter(user=user).select_related("match")

        # Build prediction lookup
        prediction_map = {p.match.pk: p for p in predictions}

        # Build enriched matches data
        matches_data = []
        for match in matches:
            prediction = prediction_map.get(match.pk)
            is_locked = match.kickoff <= now
            round_code = match.round

            # Joker info for this round
            can_add_joker = PredictionLimitService.can_add_joker(user, round_code)
            joker_count = PredictionLimitService.get_joker_count_for_round(user, round_code)
            joker_limit = PredictionLimitService.get_joker_limit_for_round(round_code)

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
                    "is_group_stage": round_code == "group",
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
        context["group_stage_count"] = PredictionLimitService.get_group_stage_prediction_count(user)
        context["group_stage_limit"] = PredictionLimitService.GROUP_STAGE_LIMIT

        # Phase navigation stats
        context["phase_stats"] = get_phase_stats(user)
        context["phase_stats_json"] = json.dumps(context["phase_stats"])
        context["tournament_phases"] = TOURNAMENT_PHASES

        # Polling interval (dynamic based on active matches)
        context["polling_interval"] = get_polling_interval()

        return context


def _get_match_row_context(
    user: "User", match: Match, prediction: MatchPrediction | None
) -> dict[str, Any]:
    """
    Build context for rendering a single match row partial.

    Args:
        user: The authenticated user.
        match: The match object.
        prediction: The user's prediction for this match (or None).

    Returns:
        Context dict for the prediction_row.html template.
    """
    now = timezone.now()
    is_locked = match.kickoff <= now
    round_code = match.round

    form = PredictionForm(instance=prediction)

    return {
        "match": match,
        "prediction": prediction,
        "form": form,
        "is_locked": is_locked,
        "can_add_joker": PredictionLimitService.can_add_joker(user, round_code),
        "joker_count": PredictionLimitService.get_joker_count_for_round(user, round_code),
        "joker_limit": PredictionLimitService.get_joker_limit_for_round(round_code),
        "is_group_stage": round_code == "group",
        "group_stage_count": PredictionLimitService.get_group_stage_prediction_count(user),
        "group_stage_limit": PredictionLimitService.GROUP_STAGE_LIMIT,
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
            Match.objects.select_related("team_home", "team_away"), pk=match_id
        )
        now = timezone.now()

        # Check locktime
        if match.kickoff <= now:
            return render(
                request,
                "predictions/prediction_error.html",
                {"error": "Spiel bereits gestartet. Tipp nicht mehr möglich."},
                status=400,
            )

        # Get or create prediction
        prediction, created = MatchPrediction.objects.get_or_create(
            user=user,
            match=match,
            defaults={
                "predicted_goals_home": 0,
                "predicted_goals_away": 0,
            },
        )

        # Check group stage limit for new predictions
        if created and match.round == "group":
            if not PredictionLimitService.can_add_group_stage_prediction(user):
                # Delete the just-created prediction
                prediction.delete()
                return render(
                    request,
                    "predictions/prediction_error.html",
                    {"error": "Limit erreicht: Max. 36 Gruppenphasen-Tipps erlaubt."},
                    status=400,
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

        context = _get_match_row_context(user, match, prediction)
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
            Match.objects.select_related("team_home", "team_away"), pk=match_id
        )
        now = timezone.now()

        # Check locktime
        if match.kickoff <= now:
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
            Match.objects.select_related("team_home", "team_away"), pk=match_id
        )
        now = timezone.now()

        # Check locktime
        if match.kickoff <= now:
            return render(
                request,
                "predictions/prediction_error.html",
                {"error": "Spiel bereits gestartet. Joker kann nicht geändert werden."},
                status=400,
            )

        # Check round - no jokers in group stage
        if match.round == "group":
            return render(
                request,
                "predictions/prediction_error.html",
                {"error": "Keine Joker in der Gruppenphase erlaubt."},
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

        context = _get_match_row_context(user, match, prediction)
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
            HTML fragments with hx-swap-oob for finished matches, or empty response.
            HX-Trigger header with updated polling interval.
        """
        # Calculate current polling interval
        polling_interval = get_polling_interval()

        # Find finished matches - these may have recently updated results
        finished_matches = Match.objects.filter(
            status="finished",
        ).select_related("team_home", "team_away")

        if not finished_matches.exists():
            # No finished matches, return empty response with polling interval
            response = HttpResponse("", content_type="text/html")
            response["HX-Trigger"] = json.dumps({"pollingInterval": polling_interval})
            return response

        # Get user's predictions for finished matches
        user: User = request.user  # type: ignore[assignment]
        predictions = MatchPrediction.objects.filter(
            user=user,
            match__in=finished_matches,
        ).select_related("match")
        prediction_map = {p.match.pk: p for p in predictions}

        # Build HTML fragments for finished matches with OOB swap
        html_parts = []
        for match in finished_matches:
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


class MatchPredictionsView(LoginRequiredMixin, View):
    """
    Return all predictions for a match (HTMX partial).

    Displays predictions from all users for the given match.
    Used in the bottom sheet overlay.
    """

    def get(self, request: HttpRequest, match_id: int) -> HttpResponse:
        """
        Handle GET request to retrieve all predictions for a match.

        Args:
            request: The HTTP request.
            match_id: The ID of the match.

        Returns:
            HTML partial with all predictions for the match.
        """
        match = get_object_or_404(
            Match.objects.select_related("team_home", "team_away"),
            pk=match_id,
        )

        # Get all users (excluding inactive/is_active=False if desired, but User.objects.filter(is_active=True))
        # and fetch their predictions for this match if they exist.
        User = get_user_model()
        users = User.objects.filter(is_active=True)

        # Prefetch prediction for this specific match
        predictions_by_user = {
            p.user_id: p
            for p in MatchPrediction.objects.filter(match=match).select_related("user")
        }

        # Build list of user prediction items
        user_predictions = []
        for user in users:
            pred = predictions_by_user.get(user.id)
            user_predictions.append({
                "user": user,
                "prediction": pred,
                "predicted_goals_home": pred.predicted_goals_home if pred else None,
                "predicted_goals_away": pred.predicted_goals_away if pred else None,
                "joker_active": pred.joker_active if pred else False,
                "points_earned": pred.points_earned if pred else None,
                "has_predicted": pred is not None,
            })

        # Sort: users with predictions first, ordered by points (desc, treating None as -1), then username
        def sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
            pred = item["prediction"]
            has_points = pred is not None and pred.points_earned is not None
            pts = pred.points_earned if has_points else -1
            # Sort order: highest points first (-pts), then has_predicted (False comes after True), then lower username
            has_pred_rank = 0 if item["has_predicted"] else 1
            return (-pts, has_pred_rank, item["user"].username.lower())

        user_predictions.sort(key=sort_key)

        # Calculate Olympic-style ranks (shared ranks for same points)
        current_rank = 1
        for i, item in enumerate(user_predictions):
            if i > 0:
                prev = user_predictions[i - 1]
                # Check if this user has same points/status as previous
                same_rank = (
                    item["points_earned"] == prev["points_earned"]
                    and item["has_predicted"] == prev["has_predicted"]
                )
                if not same_rank:
                    current_rank = i + 1  # Skip to actual position (Olympic ranking)
            item["rank"] = current_rank

        return render(
            request,
            "predictions/partials/match_predictions.html",
            {
                "match": match,
                "user_predictions": user_predictions,
                "current_user": request.user,
            },
        )
