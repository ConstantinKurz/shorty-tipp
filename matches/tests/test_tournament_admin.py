"""Tests for the tournament admin and its round inline validation."""

import pytest
from django.forms import BaseInlineFormSet
from django.forms.models import inlineformset_factory
from django.urls import reverse
from django.utils import timezone

from conftest import make_match, make_team
from matches.admin import RoundInlineFormSet
from matches.models import Round, Tournament
from matches.tournament import create_tournament
from predictions.models import MatchPrediction
from users.models import User

RoundFormSet: type[BaseInlineFormSet] = inlineformset_factory(
    Tournament,
    Round,
    formset=RoundInlineFormSet,
    fields="__all__",
    extra=0,
)

BASE_ROUND = {
    "label": "Runde",
    "multiplier": 1,
    "joker_count": 0,
    "joker_multiplier": 2,
    "joker_pool": "",
    "prediction_limit": "",
}


def formset_data(*rounds):
    """Build POST data for the round inline formset."""
    data = {
        "rounds-TOTAL_FORMS": str(len(rounds)),
        "rounds-INITIAL_FORMS": "0",
        "rounds-MIN_NUM_FORMS": "0",
        "rounds-MAX_NUM_FORMS": "1000",
    }

    for index, values in enumerate(rounds):
        for field, value in {**BASE_ROUND, **values}.items():
            if value is True:
                data[f"rounds-{index}-{field}"] = "on"
            elif value is False:
                continue
            else:
                data[f"rounds-{index}-{field}"] = str(value)

    return data


@pytest.fixture
def tournament(db):
    """Create an inactive tournament to attach rounds to."""
    return Tournament.objects.create(name="EM 2028", slug="em-2028", api_competition_code="EC")


def build_formset(tournament, *rounds):
    """Return a bound round formset for the given tournament."""
    return RoundFormSet(data=formset_data(*rounds), instance=tournament, prefix="rounds")


@pytest.mark.django_db
class TestRoundInlineValidation:
    """Tests for RoundInlineFormSet.clean()."""

    def test_round_inline_accepts_valid_configuration(self, tournament):
        """A configuration with exactly one final and consistent pools is accepted."""
        formset = build_formset(
            tournament,
            {
                "code": "sf",
                "order": 1,
                "api_stage": "SEMI_FINALS",
                "joker_pool": "ko",
                "joker_count": 2,
            },
            {
                "code": "final",
                "order": 2,
                "api_stage": "FINAL",
                "joker_pool": "ko",
                "joker_count": 2,
                "is_final": True,
            },
        )

        assert formset.is_valid(), formset.non_form_errors()

    def test_round_inline_rejects_two_finals(self, tournament):
        """Two rounds marked as the final are rejected."""
        formset = build_formset(
            tournament,
            {"code": "3rd", "order": 1, "api_stage": "THIRD_PLACE", "is_final": True},
            {"code": "final", "order": 2, "api_stage": "FINAL", "is_final": True},
        )

        assert not formset.is_valid()
        assert "Only one round may be marked as the final." in formset.non_form_errors()

    def test_round_inline_rejects_no_final(self, tournament):
        """A configuration without a final is rejected."""
        formset = build_formset(
            tournament,
            {"code": "group", "order": 1, "api_stage": "GROUP_STAGE"},
        )

        assert not formset.is_valid()
        assert "Exactly one round must be marked as the final." in formset.non_form_errors()

    def test_round_inline_rejects_duplicate_code(self, tournament):
        """Two rounds with the same code are rejected."""
        formset = build_formset(
            tournament,
            {"code": "group", "order": 1, "api_stage": "GROUP_STAGE"},
            {"code": "group", "order": 2, "api_stage": "FINAL", "is_final": True},
        )

        assert not formset.is_valid()

    def test_round_inline_rejects_duplicate_order(self, tournament):
        """Two rounds with the same order are rejected."""
        formset = build_formset(
            tournament,
            {"code": "group", "order": 1, "api_stage": "GROUP_STAGE"},
            {"code": "final", "order": 1, "api_stage": "FINAL", "is_final": True},
        )

        assert not formset.is_valid()

    def test_round_inline_rejects_duplicate_api_stage(self, tournament):
        """Two rounds mapped to the same API stage are rejected."""
        formset = build_formset(
            tournament,
            {"code": "group", "order": 1, "api_stage": "FINAL"},
            {"code": "final", "order": 2, "api_stage": "FINAL", "is_final": True},
        )

        assert not formset.is_valid()

    def test_round_inline_rejects_mismatched_joker_counts_in_pool(self, tournament):
        """Rounds sharing a joker pool must declare the same joker count."""
        formset = build_formset(
            tournament,
            {
                "code": "sf",
                "order": 1,
                "api_stage": "SEMI_FINALS",
                "joker_pool": "ko",
                "joker_count": 2,
            },
            {
                "code": "final",
                "order": 2,
                "api_stage": "FINAL",
                "joker_pool": "ko",
                "joker_count": 3,
                "is_final": True,
            },
        )

        assert not formset.is_valid()
        assert (
            'All rounds in joker pool "ko" must declare the same joker count.'
            in formset.non_form_errors()
        )


@pytest.mark.django_db
class TestTournamentAdminPreset:
    """Tests for the preset dropdown on the tournament add form."""

    def test_admin_preset_dropdown_produces_same_rounds_as_command(self, admin_user, client):
        """Adding a tournament with a preset produces the rounds the command produces."""
        client.force_login(admin_user)

        response = client.post(
            reverse("admin:matches_tournament_add"),
            {
                "name": "EM 2028",
                "slug": "em-2028",
                "api_competition_code": "EC",
                "api_season": "",
                "lock_buffer_minutes": "3",
                "preset": "em24",
            },
        )

        assert response.status_code == 302

        from_admin = Tournament.objects.get(slug="em-2028")
        from_command = create_tournament(
            name="EM 2032", slug="em-2032", api_competition_code="EC", preset="em24"
        )

        fields = ["code", "label", "order", "multiplier", "joker_count", "api_stage", "is_final"]
        assert list(from_admin.rounds.values(*fields)) == list(from_command.rounds.values(*fields))

    def test_admin_add_without_preset_creates_no_rounds(self, admin_user, client):
        """Leaving the preset empty creates a tournament with no rounds."""
        client.force_login(admin_user)

        client.post(
            reverse("admin:matches_tournament_add"),
            {
                "name": "Leer",
                "slug": "leer",
                "api_competition_code": "WC",
                "api_season": "",
                "lock_buffer_minutes": "3",
                "preset": "",
            },
        )

        assert Tournament.objects.get(slug="leer").rounds.count() == 0


@pytest.mark.django_db
class TestRecalculateScoresAction:
    """Tests for the recalculate scores admin action."""

    def test_recalculate_applies_changed_multiplier(self, admin_user, client):
        """Changing a multiplier and recalculating updates the stored points."""
        germany = make_team("Germany", "GER")
        brazil = make_team("Brazil", "BRA")
        user = User.objects.create_user(username="tipper", password="test")

        match = make_match(
            team_home=germany,
            team_away=brazil,
            kickoff=timezone.now(),
            round="group",
            status="scheduled",
        )
        MatchPrediction.objects.create(
            user=user, match=match, predicted_goals_home=2, predicted_goals_away=1
        )

        match.status = "finished"
        match.goals_home = 2
        match.goals_away = 1
        match.save()

        user.refresh_from_db()
        assert user.total_points == 6

        Round.objects.filter(tournament__is_active=True, code="group").update(multiplier=4)

        client.force_login(admin_user)
        client.post(
            reverse("admin:matches_tournament_changelist"),
            {
                "action": "recalculate_scores",
                "_selected_action": [str(Tournament.objects.get(slug="wm-2026").pk)],
            },
            follow=True,
        )

        user.refresh_from_db()
        assert user.total_points == 24
