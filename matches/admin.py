from collections import defaultdict
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.forms import BaseInlineFormSet
from django.http import HttpRequest, HttpResponse

from matches.models import Match, Round, Team, Tournament
from matches.presets import TOURNAMENT_PRESETS
from matches.tournament import create_rounds_from_preset
from predictions.models import MatchPrediction
from scoring.match_scoring import recalculate_all_scores


class RoundInlineFormSet(BaseInlineFormSet):
    """Validate the round configuration of a tournament as a whole."""

    def clean(self) -> None:
        """
        Reject round configurations that cannot produce a playable tournament.

        Raises:
            ValidationError: If no or several finals are declared, if a code, order or
                API stage is used twice, or if rounds sharing a joker pool declare
                different joker counts.
        """
        super().clean()

        rounds = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]

        if not rounds:
            return

        finals = [values for values in rounds if values.get("is_final")]
        if len(finals) > 1:
            raise ValidationError("Only one round may be marked as the final.")
        if not finals:
            raise ValidationError("Exactly one round must be marked as the final.")

        for field, label in (("code", "code"), ("order", "order"), ("api_stage", "API stage")):
            values = [values[field] for values in rounds if values.get(field) is not None]
            if len(values) != len(set(values)):
                raise ValidationError(f"Each round needs its own {label}.")

        counts_per_pool: dict[str, set[int]] = defaultdict(set)
        for values in rounds:
            pool = values.get("joker_pool")
            if pool:
                counts_per_pool[pool].add(values.get("joker_count"))

        for pool, counts in counts_per_pool.items():
            if len(counts) > 1:
                raise ValidationError(
                    f'All rounds in joker pool "{pool}" must declare the same joker count.'
                )


class RoundInline(admin.TabularInline):
    """Inline editor for the rounds of a tournament."""

    model = Round
    formset = RoundInlineFormSet
    extra = 0
    ordering = ["order"]


class TournamentAddForm(forms.ModelForm):
    """Tournament add form offering a round preset."""

    preset = forms.ChoiceField(
        required=False,
        choices=[("", "-- no rounds --")] + [(key, key) for key in sorted(TOURNAMENT_PRESETS)],
        help_text="Create the rounds of a known tournament format",
    )

    class Meta:
        model = Tournament
        fields = [
            "name",
            "slug",
            "api_competition_code",
            "api_season",
            "lock_buffer_minutes",
            "is_active",
        ]


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """Admin interface for Tournament model."""

    list_display = ["name", "slug", "api_competition_code", "api_season", "is_active"]
    list_display_links = ["name"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [RoundInline]
    actions = ["recalculate_scores"]

    def get_form(
        self,
        request: HttpRequest,
        obj: Any | None = None,
        change: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Offer the preset dropdown while adding, not while editing."""
        if obj is None:
            kwargs["form"] = TournamentAddForm
        return super().get_form(request, obj, change, **kwargs)

    def get_inline_instances(
        self, request: HttpRequest, obj: Tournament | None = None
    ) -> list[Any]:
        """Hide the round inline on the add form; the preset fills it instead."""
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def save_model(self, request: HttpRequest, obj: Tournament, form: Any, change: bool) -> None:
        """Save the tournament and create preset rounds when one was chosen."""
        super().save_model(request, obj, form, change)

        preset = form.cleaned_data.get("preset") if not change else None
        if preset:
            create_rounds_from_preset(obj, preset)

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """Warn about stale scores and unset champion points before rounds are edited."""
        scored_predictions = MatchPrediction.objects.filter(
            match__round__tournament_id=object_id,
            points_earned__isnull=False,
        ).count()

        if scored_predictions:
            messages.warning(
                request,
                f"{scored_predictions} prediction(s) are already scored. Changing a round's "
                "multiplier, joker multiplier or final flag requires running the "
                '"Recalculate scores" action afterwards.',
            )

        teams_without_points = Team.objects.filter(champion_points=0).count()
        if teams_without_points:
            messages.warning(
                request,
                f"{teams_without_points} team(s) still have champion_points = 0 and award no "
                "champion bonus.",
            )

        return super().change_view(request, object_id, form_url, extra_context)

    @admin.action(description="Recalculate scores for all finished matches")
    def recalculate_scores(self, request: HttpRequest, queryset: QuerySet[Tournament]) -> None:
        """Re-score every finished match so changed round configuration takes effect."""
        scored = recalculate_all_scores()
        self.message_user(
            request,
            f"Recalculated {scored} prediction(s).",
            messages.SUCCESS,
        )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Admin interface for Team model."""

    list_display = ["name", "fifa_code", "champion_points"]
    list_display_links = ["name"]
    search_fields = ["name", "fifa_code"]
    ordering = ["name"]
    list_editable = ["champion_points"]


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """Admin interface for Match model."""

    list_display = ["match_teams", "kickoff", "round", "score", "status"]
    list_filter = ["round__code", "status"]
    list_select_related = ["team_home", "team_away", "round"]
    search_fields = ["team_home__name", "team_away__name"]
    date_hierarchy = "kickoff"
    ordering = ["kickoff"]

    @admin.display(description="Match")
    def match_teams(self, obj: Match) -> str:
        """Display teams in list view."""
        return f"{obj.team_home.name} vs {obj.team_away.name}"

    @admin.display(description="Score")
    def score(self, obj: Match) -> str:
        """Display score if available."""
        if obj.goals_home is not None and obj.goals_away is not None:
            return f"{obj.goals_home}-{obj.goals_away}"
        return "-"
