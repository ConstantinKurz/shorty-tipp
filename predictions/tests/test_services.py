"""Tests for PredictionLimitService."""

from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from conftest import make_match
from matches.models import Team
from predictions import services
from predictions.models import MatchPrediction
from predictions.services import PredictionLimitService


@pytest.fixture
def teams(db):
    """Create test teams."""
    team_a = Team.objects.create(name="Germany", fifa_code="GER")
    team_b = Team.objects.create(name="Brazil", fifa_code="BRA")
    team_c = Team.objects.create(name="France", fifa_code="FRA")
    team_d = Team.objects.create(name="Spain", fifa_code="ESP")
    return team_a, team_b, team_c, team_d


@pytest.fixture
def future_kickoff():
    """Return a kickoff time in the future."""
    return timezone.now() + timedelta(days=7)


@pytest.fixture
def group_matches(teams, future_kickoff, db):
    """Create group stage matches."""
    team_a, team_b, team_c, team_d = teams
    matches = []
    for i in range(40):  # More than 36 to test limit
        match = make_match(
            team_home=team_a if i % 2 == 0 else team_c,
            team_away=team_b if i % 2 == 0 else team_d,
            kickoff=future_kickoff + timedelta(hours=i),
            round="group",
        )
        matches.append(match)
    return matches


@pytest.fixture
def knockout_matches(teams, future_kickoff, db):
    """Create knockout stage matches for each round."""
    team_a, team_b, team_c, team_d = teams
    kickoff_base = future_kickoff + timedelta(days=30)

    matches = {}
    rounds = ["r32", "r16", "qf", "sf", "final", "3rd"]

    for idx, round_code in enumerate(rounds):
        round_matches = []
        count = 4 if round_code in ("r32", "r16") else 2
        for i in range(count):
            match = make_match(
                team_home=team_a if i % 2 == 0 else team_c,
                team_away=team_b if i % 2 == 0 else team_d,
                kickoff=kickoff_base + timedelta(days=idx * 3, hours=i),
                round=round_code,
            )
            round_matches.append(match)
        matches[round_code] = round_matches

    return matches


class TestGetJokerLimitForRound:
    """Tests for get_joker_limit_for_round method."""

    def test_limits_come_from_configuration(self, rounds):
        """The joker limit of a round is its configured joker_count."""
        limits = {
            code: PredictionLimitService.get_joker_limit_for_round(match_round)
            for code, match_round in rounds.items()
        }

        assert limits == {
            "group": 0,
            "r32": 3,
            "r16": 3,
            "qf": 2,
            "sf": 2,
            "3rd": 2,
            "final": 2,
        }

    def test_changed_joker_count_is_read_back(self, rounds):
        """Editing joker_count changes the limit immediately."""
        rounds["qf"].joker_count = 7

        assert PredictionLimitService.get_joker_limit_for_round(rounds["qf"]) == 7


class TestGetJokerCountForRound:
    """Tests for get_joker_count_for_round method."""

    def test_counts_jokers_correctly(self, regular_user, knockout_matches, rounds):
        """Should count active jokers in a round."""
        r32_matches = knockout_matches["r32"]

        # Create predictions with jokers for 2 matches
        MatchPrediction.objects.create(
            user=regular_user,
            match=r32_matches[0],
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=True,
        )
        MatchPrediction.objects.create(
            user=regular_user,
            match=r32_matches[1],
            predicted_goals_home=1,
            predicted_goals_away=0,
            joker_active=True,
        )
        # One without joker
        MatchPrediction.objects.create(
            user=regular_user,
            match=r32_matches[2],
            predicted_goals_home=0,
            predicted_goals_away=0,
            joker_active=False,
        )

        count = PredictionLimitService.get_joker_count_for_round(regular_user, rounds["r32"])
        assert count == 2

    def test_combined_rounds_share_pool(self, regular_user, knockout_matches, rounds):
        """sf/final/3rd should share joker pool."""
        # Add joker to semi-final
        MatchPrediction.objects.create(
            user=regular_user,
            match=knockout_matches["sf"][0],
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=True,
        )
        # Add joker to final
        MatchPrediction.objects.create(
            user=regular_user,
            match=knockout_matches["final"][0],
            predicted_goals_home=1,
            predicted_goals_away=0,
            joker_active=True,
        )

        # All combined rounds should show count of 2
        for code in ("sf", "final", "3rd"):
            assert PredictionLimitService.get_joker_count_for_round(regular_user, rounds[code]) == 2

    def test_joker_pool_limit_with_third_place_round_absent(
        self, regular_user, knockout_matches, rounds
    ):
        """A joker pool of two rounds still enforces the shared limit."""
        rounds["3rd"].joker_pool = ""
        rounds["3rd"].save(update_fields=["joker_pool"])

        MatchPrediction.objects.create(
            user=regular_user,
            match=knockout_matches["sf"][0],
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=True,
        )
        MatchPrediction.objects.create(
            user=regular_user,
            match=knockout_matches["final"][0],
            predicted_goals_home=1,
            predicted_goals_away=0,
            joker_active=True,
        )

        assert PredictionLimitService.get_joker_count_for_round(regular_user, rounds["sf"]) == 2
        assert PredictionLimitService.can_add_joker(regular_user, rounds["final"]) is False
        # The third-place round now has its own pool and is still empty
        assert PredictionLimitService.can_add_joker(regular_user, rounds["3rd"]) is True

    def test_no_jokers_returns_zero(self, regular_user, knockout_matches, rounds):
        """Should return 0 when user has no jokers in round."""
        count = PredictionLimitService.get_joker_count_for_round(regular_user, rounds["r32"])
        assert count == 0


class TestCanAddJoker:
    """Tests for can_add_joker method."""

    def test_returns_true_when_under_limit(self, regular_user, knockout_matches, rounds):
        """Should return True when user hasn't reached limit."""
        # Add 2 jokers to r32 (limit is 3)
        for match in knockout_matches["r32"][:2]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=2,
                predicted_goals_away=1,
                joker_active=True,
            )

        assert PredictionLimitService.can_add_joker(regular_user, rounds["r32"]) is True

    def test_returns_false_when_at_limit(self, regular_user, knockout_matches, rounds):
        """Should return False when user has reached limit."""
        # Add 3 jokers to r32 (limit is 3)
        for match in knockout_matches["r32"][:3]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=2,
                predicted_goals_away=1,
                joker_active=True,
            )

        assert PredictionLimitService.can_add_joker(regular_user, rounds["r32"]) is False

    def test_returns_false_for_group_stage(self, regular_user, group_matches, rounds):
        """Should return False for group stage (limit is 0)."""
        assert PredictionLimitService.can_add_joker(regular_user, rounds["group"]) is False

    def test_combined_rounds_respect_shared_limit(self, regular_user, knockout_matches, rounds):
        """sf/final/3rd should enforce shared limit of 2."""
        # Add 2 jokers across sf/final
        MatchPrediction.objects.create(
            user=regular_user,
            match=knockout_matches["sf"][0],
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=True,
        )
        MatchPrediction.objects.create(
            user=regular_user,
            match=knockout_matches["final"][0],
            predicted_goals_home=1,
            predicted_goals_away=0,
            joker_active=True,
        )

        # Should not be able to add to any combined round
        for code in ("sf", "final", "3rd"):
            assert PredictionLimitService.can_add_joker(regular_user, rounds[code]) is False


class TestGetPredictionCountForRound:
    """Tests for get_prediction_count_for_round method."""

    def test_counts_correctly(self, regular_user, group_matches, rounds):
        """Should count predictions of the round correctly."""
        # Create 5 predictions
        for match in group_matches[:5]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=1,
                predicted_goals_away=1,
            )

        count = PredictionLimitService.get_prediction_count_for_round(regular_user, rounds["group"])
        assert count == 5

    def test_ignores_other_rounds(self, regular_user, group_matches, knockout_matches, rounds):
        """Should not count predictions of other rounds."""
        # Create group prediction
        MatchPrediction.objects.create(
            user=regular_user,
            match=group_matches[0],
            predicted_goals_home=1,
            predicted_goals_away=1,
        )
        # Create knockout prediction
        MatchPrediction.objects.create(
            user=regular_user,
            match=knockout_matches["r32"][0],
            predicted_goals_home=2,
            predicted_goals_away=0,
        )

        count = PredictionLimitService.get_prediction_count_for_round(regular_user, rounds["group"])
        assert count == 1

    def test_zero_when_no_predictions(self, regular_user, rounds):
        """Should return 0 when user has no predictions."""
        count = PredictionLimitService.get_prediction_count_for_round(regular_user, rounds["group"])
        assert count == 0


class TestCanAddPrediction:
    """Tests for can_add_prediction method."""

    def test_returns_true_under_limit(self, regular_user, group_matches, rounds):
        """Should return True when under the configured limit."""
        # Create 35 predictions, limit is 36
        for match in group_matches[:35]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=1,
                predicted_goals_away=1,
            )

        assert PredictionLimitService.can_add_prediction(regular_user, rounds["group"]) is True

    def test_returns_false_at_limit(self, regular_user, group_matches, rounds):
        """Should return False when the configured limit is reached."""
        # Create 36 predictions
        for match in group_matches[:36]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=1,
                predicted_goals_away=1,
            )

        assert PredictionLimitService.can_add_prediction(regular_user, rounds["group"]) is False

    def test_prediction_limit_enforced_per_round(self, regular_user, group_matches, rounds):
        """A limit of 10 rejects the eleventh prediction in that round."""
        rounds["group"].prediction_limit = 10
        rounds["group"].save(update_fields=["prediction_limit"])

        for match in group_matches[:10]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=1,
                predicted_goals_away=1,
            )

        assert PredictionLimitService.can_add_prediction(regular_user, rounds["group"]) is False

    def test_round_without_prediction_limit_allows_all_matches(
        self, regular_user, knockout_matches, rounds
    ):
        """A round with no limit never rejects a prediction."""
        for match in knockout_matches["r32"]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=1,
                predicted_goals_away=1,
            )

        assert rounds["r32"].prediction_limit is None
        assert PredictionLimitService.can_add_prediction(regular_user, rounds["r32"]) is True

    def test_returns_true_with_no_predictions(self, regular_user, rounds):
        """Should return True when user has no predictions."""
        assert PredictionLimitService.can_add_prediction(regular_user, rounds["group"]) is True


class TestIsMatchLocked:
    """Tests for is_match_locked method."""

    def test_returns_true_when_2_minutes_before_kickoff(self, db):
        """Test match is locked 2 minutes before kickoff."""
        from datetime import datetime

        from django.utils import timezone

        from matches.models import Team

        team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)

        kickoff = timezone.make_aware(datetime(2026, 6, 15, 18, 0))
        match = make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            status="scheduled",
        )

        # 2 minutes before kickoff - should be locked
        reference_time = timezone.make_aware(datetime(2026, 6, 15, 17, 58))
        assert PredictionLimitService.is_match_locked(match, reference_time) is True

    def test_returns_false_when_4_minutes_before_kickoff(self, db):
        """Test match is not locked 4 minutes before kickoff."""
        from datetime import datetime

        from django.utils import timezone

        from matches.models import Team

        team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)

        kickoff = timezone.make_aware(datetime(2026, 6, 15, 18, 0))
        match = make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            status="scheduled",
        )

        # 4 minutes before kickoff - should NOT be locked
        reference_time = timezone.make_aware(datetime(2026, 6, 15, 17, 56))
        assert PredictionLimitService.is_match_locked(match, reference_time) is False

    def test_boundary_at_exactly_3_minutes(self, db):
        """Test boundary condition at exactly 3 minutes before kickoff."""
        from datetime import datetime

        from django.utils import timezone

        from matches.models import Team

        team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)

        kickoff = timezone.make_aware(datetime(2026, 6, 15, 18, 0))
        match = make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            status="scheduled",
        )

        # Exactly 3 minutes before kickoff - should be locked (>= lock_time)
        reference_time = timezone.make_aware(datetime(2026, 6, 15, 17, 57))
        assert PredictionLimitService.is_match_locked(match, reference_time) is True

    def test_uses_timezone_now_when_reference_time_not_provided(self, db):
        """Test method uses timezone.now() when reference_time is None."""
        from datetime import datetime

        from django.utils import timezone

        from matches.models import Team

        team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)

        # Kickoff in the past
        kickoff = timezone.make_aware(datetime(2020, 6, 15, 18, 0))
        match = make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            status="scheduled",
        )

        # Should be locked (kickoff was 6 years ago)
        assert PredictionLimitService.is_match_locked(match) is True

    def test_lock_buffer_read_from_tournament(self, db, tournament):
        """The lock buffer comes from the tournament, not from a constant."""
        from datetime import datetime

        from django.utils import timezone

        from matches.models import Team

        team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)

        tournament.lock_buffer_minutes = 30
        tournament.save(update_fields=["lock_buffer_minutes"])

        kickoff = timezone.make_aware(datetime(2026, 6, 15, 18, 0))
        match = make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            status="scheduled",
        )
        match.refresh_from_db()

        # 20 minutes before kickoff is inside the configured 30 minute buffer
        reference_time = timezone.make_aware(datetime(2026, 6, 15, 17, 40))
        assert PredictionLimitService.is_match_locked(match, reference_time) is True

        # 40 minutes before kickoff is outside it
        reference_time = timezone.make_aware(datetime(2026, 6, 15, 17, 20))
        assert PredictionLimitService.is_match_locked(match, reference_time) is False


@pytest.mark.django_db
class TestGetPollingIntervalService:
    """Tests for get_polling_interval() after the move into the service layer."""

    def test_active_interval_inside_match_window(self, teams, monkeypatch):
        """A match that kicked off inside the active window yields the active interval."""
        team_a, team_b, _, _ = teams
        reference = timezone.make_aware(datetime(2026, 6, 20, 20, 0))
        make_match(
            team_home=team_a,
            team_away=team_b,
            kickoff=reference - timedelta(minutes=30),
            round="group",
            status="live",
        )

        monkeypatch.setattr(services.timezone, "now", lambda: reference)

        assert services.get_polling_interval() == services.POLLING_INTERVAL_ACTIVE

    def test_idle_interval_outside_match_window(self, teams, monkeypatch):
        """A match older than the active window yields the idle interval."""
        team_a, team_b, _, _ = teams
        reference = timezone.make_aware(datetime(2026, 6, 20, 20, 0))
        make_match(
            team_home=team_a,
            team_away=team_b,
            kickoff=reference - timedelta(minutes=services.MATCH_ACTIVE_WINDOW_MINUTES + 1),
            round="group",
            status="live",
        )

        monkeypatch.setattr(services.timezone, "now", lambda: reference)

        assert services.get_polling_interval() == services.POLLING_INTERVAL_IDLE


@pytest.mark.django_db
class TestGetPhaseStatsService:
    """Tests for get_phase_stats() after the move into the service layer."""

    def test_counts_predictions_and_jokers_per_phase(self, teams):
        """Predictions and jokers are counted per tournament phase."""
        team_a, team_b, team_c, team_d = teams
        user = get_user_model().objects.create_user(username="tipper", password="test")

        group_match = make_match(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() + timedelta(days=1),
            round="group",
        )
        knockout_match = make_match(
            team_home=team_c,
            team_away=team_d,
            kickoff=timezone.now() + timedelta(days=2),
            round="r32",
        )
        MatchPrediction.objects.create(
            user=user, match=group_match, predicted_goals_home=1, predicted_goals_away=0
        )
        MatchPrediction.objects.create(
            user=user,
            match=knockout_match,
            predicted_goals_home=2,
            predicted_goals_away=2,
            joker_active=True,
        )

        stats = services.get_phase_stats(user)

        assert stats["group"]["predictions"] == 1
        assert stats["group"]["jokers"] == 0
        assert stats["group"]["total_matches"] == 36
        assert stats["group"]["label"] == "Gruppenphase"
        assert stats["r32"]["predictions"] == 1
        assert stats["r32"]["jokers"] == 1
        assert stats["r32"]["joker_limit"] == 3
        assert stats["r32"]["label"] == "Sechzehntelfinale"


@pytest.mark.django_db
class TestBuildMatchPredictionsListService:
    """Tests for build_match_predictions_list() after the move into the service layer."""

    def test_ordering_ranking_and_joker_flags(self, teams):
        """Entries are ordered by match points with Olympic ranking and joker flags."""
        team_a, team_b, _, _ = teams
        User = get_user_model()
        top = User.objects.create_user(username="top", password="test")
        tied = User.objects.create_user(username="atied", password="test")
        User.objects.create_user(username="zzz", password="test")

        match = make_match(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() - timedelta(hours=3),
            round="r32",
            status="finished",
            goals_home=2,
            goals_away=1,
        )
        MatchPrediction.objects.create(
            user=top,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=6,
            is_exact_match=True,
            joker_active=True,
        )
        MatchPrediction.objects.create(
            user=tied,
            match=match,
            predicted_goals_home=3,
            predicted_goals_away=0,
            points_earned=3,
        )

        result = services.build_match_predictions_list(match, "match", top)

        assert [entry["user"].username for entry in result] == ["top", "atied", "zzz"]
        assert [entry["rank"] for entry in result] == [1, 2, 3]
        assert result[0]["joker_active"] is True
        assert result[1]["joker_active"] is False
        assert result[2]["has_predicted"] is False
