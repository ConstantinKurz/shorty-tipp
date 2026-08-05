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
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from matches.constants import ROUND_ORDER as TOURNAMENT_PHASES
from matches.models import Match
from predictions.forms import PredictionForm
from predictions.models import MatchPrediction
from predictions.services import PredictionLimitService

if TYPE_CHECKING:
    from users.models import User

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
    is_locked = match.kickoff - timedelta(minutes=3) <= now
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
            HTML fragments with hx-swap-oob for live matches, or empty response. OOB to change multiple matches at once
            HX-Trigger header with updated polling interval.
        """
        # Calculate current polling interval
        polling_interval = get_polling_interval()
        now = timezone.now()

        # Find live/active matches (within active window, not finished yet)
        # These may have goals updating in real-time
        matches_to_update = Match.objects.filter(
            kickoff__lte=now,
            kickoff__gt=now - timedelta(minutes=MATCH_ACTIVE_WINDOW_MINUTES),
        ).exclude(status="finished").select_related("team_home", "team_away")

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


class MatchPredictionsView(LoginRequiredMixin, View):
    """
    Return all predictions for a match (HTMX partial).

    Displays predictions from all users for the given match.
    Used in the bottom sheet overlay.
    Includes aggregated user statistics: champion prediction, exact count,
    jokers used, and total points.
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

        # Get sort mode from query parameter (default: match)
        sort_mode = request.GET.get("sort", "match")
        if sort_mode not in ("match", "total"):
            sort_mode = "match"

        # Get all active users with aggregated statistics
        User = get_user_model()
        users = User.objects.filter(is_active=True).annotate(
            stats_total_points=Coalesce(Sum("match_predictions__points_earned"), 0),
            stats_exact_count=Count(
                "match_predictions",
                filter=Q(match_predictions__is_exact_match=True)
            ),
            stats_jokers_count=Count(
                "match_predictions",
                filter=Q(match_predictions__joker_active=True)
            ),
        ).select_related("predicted_champion")

        # Prefetch predictions for this specific match
        predictions_by_user = {
            p.user_id: p  # type: ignore[attr-defined]
            for p in MatchPrediction.objects.filter(match=match).select_related("user")
        }

        # Build list of user prediction items with all statistics
        user_predictions = []
        for user in users:
            pred = predictions_by_user.get(user.id)  # type: ignore[attr-defined]
            match_points = pred.points_earned if pred and pred.points_earned is not None else 0

            user_predictions.append({
                "user": user,
                "prediction": pred,
                "predicted_goals_home": pred.predicted_goals_home if pred else None,
                "predicted_goals_away": pred.predicted_goals_away if pred else None,
                "joker_active": pred.joker_active if pred else False,
                "points_earned": pred.points_earned if pred else None,
                "has_predicted": pred is not None,
                # Aggregated statistics
                "match_points": match_points,
                "champion": user.predicted_champion,  # type: ignore[attr-defined]
                "exact_count": user.stats_exact_count,  # type: ignore[attr-defined]
                "jokers_count": user.stats_jokers_count,  # type: ignore[attr-defined]
                "total_points": user.stats_total_points,  # type: ignore[attr-defined]
            })

        # Sort based on mode
        if sort_mode == "total":
            # Sort by official tiebreaker criteria:
            # 1. Total points (desc)
            # 2. Exact match count (desc)
            # 3. Jokers used (asc - fewer = better)
            # 4. Username (asc - final tiebreaker)
            user_predictions.sort(
                key=lambda x: (
                    -x["total_points"],
                    -x["exact_count"],
                    x["jokers_count"],  # Ascending: fewer jokers used = better
                    x["user"].username.lower(),
                )
            )
        else:
            # Sort by match points, then same tiebreakers:
            # 1. Match points (desc)
            # 2. Exact match count (desc)
            # 3. Jokers used (asc - fewer = better)
            # 4. Username (asc - final tiebreaker)
            user_predictions.sort(
                key=lambda x: (
                    -x["match_points"],
                    -x["exact_count"],
                    x["jokers_count"],  # Ascending: fewer jokers used = better
                    x["user"].username.lower(),
                )
            )

        # Apply Olympic-style ranking based on sort criterion
        current_rank = 1
        prev_entry = None
        users_at_rank = 0

        for entry in user_predictions:
            if prev_entry is not None:
                # Compare tiebreaker fields (same logic both modes, different primary key)
                if sort_mode == "total":
                    same_rank = (
                        entry["total_points"] == prev_entry["total_points"]
                        and entry["exact_count"] == prev_entry["exact_count"]
                        and entry["jokers_count"] == prev_entry["jokers_count"]
                    )
                else:
                    same_rank = (
                        entry["match_points"] == prev_entry["match_points"]
                        and entry["exact_count"] == prev_entry["exact_count"]
                        and entry["jokers_count"] == prev_entry["jokers_count"]
                    )
                if not same_rank:
                    current_rank += users_at_rank
                    users_at_rank = 1
                else:
                    users_at_rank += 1
            else:
                users_at_rank = 1

            entry["rank"] = current_rank
            prev_entry = entry

        return render(
            request,
            "predictions/partials/match_predictions.html",
            {
                "match": match,
                "user_predictions": user_predictions,
                "current_user": request.user,
                "sort_mode": sort_mode,
            },
        )
