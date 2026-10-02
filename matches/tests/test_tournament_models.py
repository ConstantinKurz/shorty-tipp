"""Tests for the Tournament and Round configuration models."""

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from conftest import make_match, make_team
from matches.models import Match, Round, Tournament
from matches.tournament import NoActiveTournamentError, get_active_tournament

WM2026_ROUND_CODES = ["group", "r32", "r16", "qf", "sf", "3rd", "final"]

EXPECTED_WM2026_ROUNDS = [
    ("group", "Gruppenphase", 1, 1, 0, 2, "", 36, False, "GROUP_STAGE"),
    ("r32", "Sechzehntelfinale", 2, 2, 3, 2, "", None, False, "ROUND_OF_32"),
    ("r16", "Achtelfinale", 3, 2, 3, 2, "", None, False, "ROUND_OF_16"),
    ("qf", "Viertelfinale", 4, 3, 2, 2, "", None, False, "QUARTER_FINALS"),
    ("sf", "Halbfinale", 5, 3, 2, 2, "ko_final", None, False, "SEMI_FINALS"),
    ("3rd", "Spiel um Platz 3", 6, 3, 2, 2, "ko_final", None, False, "THIRD_PLACE"),
    ("final", "Finale", 7, 3, 2, 2, "ko_final", None, True, "FINAL"),
]


def make_tournament(slug="em-2028", **kwargs):
    """Create an inactive tournament for configuration tests."""
    values = {
        "name": "EM 2028",
        "slug": slug,
        "api_competition_code": "EC",
        **kwargs,
    }
    return Tournament.objects.create(**values)


def make_round(tournament, code="group", order=1, api_stage="GROUP_STAGE", **kwargs):
    """Create a round with the given identity fields."""
    values = {
        "label": code,
        "multiplier": 1,
        **kwargs,
    }
    return Round.objects.create(
        tournament=tournament, code=code, order=order, api_stage=api_stage, **values
    )


@pytest.mark.django_db
class TestTournamentConstraints:
    """Tests for tournament-level invariants."""

    def test_only_one_active_tournament_allowed(self):
        """The seeded tournament is active, so a second active tournament is rejected."""
        assert Tournament.objects.filter(is_active=True).count() == 1

        with pytest.raises(IntegrityError), transaction.atomic():
            make_tournament(is_active=True)

    def test_get_active_tournament_returns_active_tournament(self):
        """The accessor returns the tournament flagged as active."""
        assert get_active_tournament().slug == "wm-2026"

    def test_get_active_tournament_raises_when_none_configured(self):
        """Without an active tournament the accessor raises instead of returning None."""
        Tournament.objects.update(is_active=False)

        with pytest.raises(NoActiveTournamentError):
            get_active_tournament()


@pytest.mark.django_db
class TestRoundConstraints:
    """Tests for round-level invariants."""

    def test_only_one_final_round_per_tournament(self):
        """A tournament may declare at most one final."""
        tournament = make_tournament()
        make_round(tournament, code="final", order=1, api_stage="FINAL", is_final=True)

        with pytest.raises(IntegrityError), transaction.atomic():
            make_round(tournament, code="3rd", order=2, api_stage="THIRD_PLACE", is_final=True)

    def test_round_code_order_and_api_stage_unique_per_tournament(self):
        """Code, order and API stage identify a round within its tournament."""
        tournament = make_tournament()
        make_round(tournament)

        with pytest.raises(IntegrityError), transaction.atomic():
            make_round(tournament, code="group", order=2, api_stage="ROUND_OF_16")

        with pytest.raises(IntegrityError), transaction.atomic():
            make_round(tournament, code="r16", order=1, api_stage="ROUND_OF_16")

        with pytest.raises(IntegrityError), transaction.atomic():
            make_round(tournament, code="r16", order=2, api_stage="GROUP_STAGE")

    def test_two_tournaments_may_share_round_codes(self):
        """Round codes are scoped to a tournament, not global."""
        first = make_tournament(slug="em-2028")
        second = make_tournament(slug="em-2032", name="EM 2032")

        make_round(first)
        make_round(second)

        assert Round.objects.filter(code="group").count() == 3  # two new plus the seeded one

    def test_rounds_are_ordered_by_order(self):
        """Rounds come back in tournament order."""
        tournament = make_tournament()
        make_round(tournament, code="final", order=2, api_stage="FINAL")
        make_round(tournament, code="group", order=1, api_stage="GROUP_STAGE")

        assert [round.code for round in tournament.rounds.all()] == ["group", "final"]

    def test_effective_joker_pool_falls_back_to_code(self):
        """A round without an explicit pool forms its own pool."""
        tournament = make_tournament()
        pooled = make_round(tournament, code="sf", order=1, api_stage="SEMI_FINALS")
        pooled.joker_pool = "ko_final"

        unpooled = make_round(tournament, code="r16", order=2, api_stage="ROUND_OF_16")

        assert pooled.effective_joker_pool == "ko_final"
        assert unpooled.effective_joker_pool == "r16"


@pytest.mark.django_db
class TestSeedMigration:
    """Tests for the seeded 2026 World Cup configuration."""

    def test_seed_migration_creates_wm2026_with_expected_rounds(self):
        """The data migration reproduces the previously hardcoded configuration."""
        tournament = Tournament.objects.get(slug="wm-2026")

        assert tournament.name == "WM 2026"
        assert tournament.api_competition_code == "WC"
        assert tournament.api_season == 2026
        assert tournament.lock_buffer_minutes == 3
        assert tournament.is_active is True

        seeded = [
            (
                round.code,
                round.label,
                round.order,
                round.multiplier,
                round.joker_count,
                round.joker_multiplier,
                round.joker_pool,
                round.prediction_limit,
                round.is_final,
                round.api_stage,
            )
            for round in tournament.rounds.all()
        ]

        assert seeded == EXPECTED_WM2026_ROUNDS

    def test_round_backfill_migration_maps_all_existing_codes(self):
        """Every round code the application used before the migration resolves to a row."""
        tournament = Tournament.objects.get(slug="wm-2026")
        seeded_codes = set(tournament.rounds.values_list("code", flat=True))

        assert set(WM2026_ROUND_CODES) <= seeded_codes
        assert not Match.objects.filter(round__isnull=True).exists()


@pytest.mark.django_db
class TestMatchRoundRelation:
    """Tests for the Match to Round relation."""

    def test_match_round_is_protected_from_deletion(self):
        """A round that has matches cannot be deleted."""
        match = make_match(
            team_home=make_team("Germany", "GER"),
            team_away=make_team("Brazil", "BRA"),
            kickoff=timezone.now(),
            round="group",
        )

        with pytest.raises(ProtectedError):
            match.round.delete()

    def test_match_round_relation_resolves_label_and_multiplier(self):
        """A match exposes its round's configuration through the relation."""
        match = make_match(
            team_home=make_team("Germany", "GER"),
            team_away=make_team("Brazil", "BRA"),
            kickoff=timezone.now(),
            round="r32",
        )

        assert match.round.label == "Sechzehntelfinale"
        assert match.round.multiplier == 2
