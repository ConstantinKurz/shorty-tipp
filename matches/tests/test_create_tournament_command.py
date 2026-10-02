"""Tests for the create_tournament command and the tournament presets."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone

from conftest import make_match, make_team
from matches.models import Round, Tournament
from matches.presets import TOURNAMENT_PRESETS
from matches.tournament import UnknownPresetError, create_tournament
from predictions.models import MatchPrediction
from predictions.services import PredictionLimitService
from scoring.match_scoring import recalculate_all_scores
from users.models import User


@pytest.mark.django_db
class TestCreateTournamentFunction:
    """Tests for the create_tournament factory."""

    def test_create_tournament_from_wm48_preset_creates_seven_rounds(self) -> None:
        """The wm48 preset reproduces the seeded 2026 configuration."""
        tournament = create_tournament(
            name="WM 2030", slug="wm-2030", api_competition_code="WC", preset="wm48"
        )

        codes = list(tournament.rounds.values_list("code", flat=True))
        assert codes == ["group", "r32", "r16", "qf", "sf", "3rd", "final"]
        assert tournament.rounds.get(code="r32").label == "Sechzehntelfinale"
        assert tournament.rounds.filter(is_final=True).count() == 1

    def test_create_tournament_from_em24_preset_omits_r32_and_third_place(self) -> None:
        """The em24 preset has neither a round of 32 nor a third-place match."""
        tournament = create_tournament(
            name="EM 2028", slug="em-2028", api_competition_code="EC", preset="em24"
        )

        codes = list(tournament.rounds.values_list("code", flat=True))
        assert codes == ["group", "r16", "qf", "sf", "final"]

    def test_create_tournament_without_preset_creates_no_rounds(self) -> None:
        """A tournament without a preset starts empty."""
        tournament = create_tournament(name="Leer", slug="leer", api_competition_code="WC")

        assert tournament.rounds.count() == 0

    def test_activate_deactivates_previous_tournament(self) -> None:
        """Activating a tournament leaves exactly one active tournament."""
        tournament = create_tournament(
            name="EM 2028",
            slug="em-2028",
            api_competition_code="EC",
            preset="em24",
            activate=True,
        )

        assert Tournament.objects.filter(is_active=True).count() == 1
        assert Tournament.objects.get(is_active=True).pk == tournament.pk

    def test_create_tournament_is_atomic(self, monkeypatch) -> None:
        """A failing round specification leaves no tournament behind."""
        before = Tournament.objects.count()
        duplicated = [*TOURNAMENT_PRESETS["em24"], TOURNAMENT_PRESETS["em24"][0]]
        monkeypatch.setitem(TOURNAMENT_PRESETS, "broken", duplicated)

        with pytest.raises(IntegrityError), transaction.atomic():
            create_tournament(
                name="Kaputt",
                slug="kaputt",
                api_competition_code="EC",
                preset="broken",
            )

        assert Tournament.objects.count() == before

    def test_unknown_preset_raises(self) -> None:
        """An unknown preset name fails before anything is written."""
        with pytest.raises(UnknownPresetError, match="wm99"):
            create_tournament(name="X", slug="x", api_competition_code="WC", preset="wm99")

        assert not Tournament.objects.filter(slug="x").exists()

    def test_em24_joker_pool_spans_semi_final_and_final(self) -> None:
        """The em24 joker pool covers sf and final and shares one limit."""
        tournament = create_tournament(
            name="EM 2028", slug="em-2028", api_competition_code="EC", preset="em24"
        )

        pooled = tournament.rounds.filter(joker_pool="ko_final")
        assert set(pooled.values_list("code", flat=True)) == {"sf", "final"}
        assert set(pooled.values_list("joker_count", flat=True)) == {2}


@pytest.mark.django_db
class TestCreateTournamentCommand:
    """Tests for the create_tournament management command."""

    def test_command_creates_preset_rounds(self) -> None:
        """The command produces the same rounds as the factory."""
        out = StringIO()
        call_command(
            "create_tournament",
            "--preset=em24",
            "--name=EM 2028",
            "--slug=em-2028",
            "--competition=EC",
            "--activate",
            stdout=out,
        )

        tournament = Tournament.objects.get(slug="em-2028")
        assert tournament.is_active is True
        assert list(tournament.rounds.values_list("code", flat=True)) == [
            "group",
            "r16",
            "qf",
            "sf",
            "final",
        ]
        assert "5 round(s)" in out.getvalue()

    def test_command_without_preset_creates_no_rounds(self) -> None:
        """Omitting the preset creates an empty tournament."""
        call_command(
            "create_tournament",
            "--name=Leer",
            "--slug=leer",
            "--competition=WC",
            stdout=StringIO(),
        )

        assert Tournament.objects.get(slug="leer").rounds.count() == 0

    def test_command_rejects_duplicate_slug(self) -> None:
        """A slug collision fails the command."""
        with pytest.raises(CommandError):
            call_command(
                "create_tournament",
                "--name=WM 2026",
                "--slug=wm-2026",
                "--competition=WC",
                stdout=StringIO(),
            )


@pytest.mark.django_db
class TestScoringOnEm24Configuration:
    """End-to-end check that scoring works without r32 and without a third-place match."""

    def test_scoring_works_on_em24_configuration(self) -> None:
        """A final on an em24 tournament scores points, champion bonus and joker pool."""
        Tournament.objects.filter(is_active=True).update(is_active=False)
        tournament = create_tournament(
            name="EM 2028",
            slug="em-2028",
            api_competition_code="EC",
            preset="em24",
            activate=True,
        )

        germany = make_team("Germany", "GER", champion_points=25)
        spain = make_team("Spain", "ESP", champion_points=35)

        user = User.objects.create_user(
            username="tipper", password="test", predicted_champion=germany
        )

        semi_final = make_match(
            team_home=germany,
            team_away=spain,
            kickoff=timezone.now(),
            round="sf",
            status="finished",
            goals_home=1,
            goals_away=0,
        )
        MatchPrediction.objects.create(
            user=user,
            match=semi_final,
            predicted_goals_home=1,
            predicted_goals_away=0,
            joker_active=True,
        )

        final = make_match(
            team_home=germany,
            team_away=spain,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=2,
            goals_away=1,
        )
        MatchPrediction.objects.create(
            user=user,
            match=final,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        recalculate_all_scores()
        user.refresh_from_db()

        # sf: 6 * 3 * 2 (joker) = 36, final: 6 * 3 = 18, champion bonus 25
        assert user.total_points == 36 + 18 + 25
        assert user.champion_bonus_points == 25

        # The joker pool now spans sf and final only, and one joker is already used
        sf_round = Round.objects.get(tournament=tournament, code="sf")
        assert PredictionLimitService.get_joker_count_for_round(user, sf_round) == 1
        assert PredictionLimitService.can_add_joker(user, sf_round) is True
