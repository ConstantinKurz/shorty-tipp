"""Tests for PredictionLimitService."""

from datetime import timedelta

import pytest
from django.utils import timezone

from matches.models import Match, Team
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
        match = Match.objects.create(
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
            match = Match.objects.create(
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

    def test_group_stage_returns_zero(self):
        """Group stage should not allow jokers."""
        assert PredictionLimitService.get_joker_limit_for_round("group") == 0

    def test_r32_returns_three(self):
        """Round of 32 should allow 3 jokers."""
        assert PredictionLimitService.get_joker_limit_for_round("r32") == 3

    def test_r16_returns_three(self):
        """Round of 16 should allow 3 jokers."""
        assert PredictionLimitService.get_joker_limit_for_round("r16") == 3

    def test_qf_returns_two(self):
        """Quarter-final should allow 2 jokers."""
        assert PredictionLimitService.get_joker_limit_for_round("qf") == 2

    def test_sf_returns_two(self):
        """Semi-final should allow 2 jokers (shared pool)."""
        assert PredictionLimitService.get_joker_limit_for_round("sf") == 2

    def test_final_returns_two(self):
        """Final should allow 2 jokers (shared pool with sf/3rd)."""
        assert PredictionLimitService.get_joker_limit_for_round("final") == 2

    def test_third_returns_two(self):
        """Third-place match should allow 2 jokers (shared pool)."""
        assert PredictionLimitService.get_joker_limit_for_round("3rd") == 2

    def test_unknown_round_returns_zero(self):
        """Unknown round codes should return 0."""
        assert PredictionLimitService.get_joker_limit_for_round("unknown") == 0


class TestGetJokerCountForRound:
    """Tests for get_joker_count_for_round method."""

    def test_counts_jokers_correctly(self, regular_user, knockout_matches):
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

        count = PredictionLimitService.get_joker_count_for_round(regular_user, "r32")
        assert count == 2

    def test_combined_rounds_share_pool(self, regular_user, knockout_matches):
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
        assert PredictionLimitService.get_joker_count_for_round(regular_user, "sf") == 2
        assert PredictionLimitService.get_joker_count_for_round(regular_user, "final") == 2
        assert PredictionLimitService.get_joker_count_for_round(regular_user, "3rd") == 2

    def test_no_jokers_returns_zero(self, regular_user, knockout_matches):
        """Should return 0 when user has no jokers in round."""
        count = PredictionLimitService.get_joker_count_for_round(regular_user, "r32")
        assert count == 0


class TestCanAddJoker:
    """Tests for can_add_joker method."""

    def test_returns_true_when_under_limit(self, regular_user, knockout_matches):
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

        assert PredictionLimitService.can_add_joker(regular_user, "r32") is True

    def test_returns_false_when_at_limit(self, regular_user, knockout_matches):
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

        assert PredictionLimitService.can_add_joker(regular_user, "r32") is False

    def test_returns_false_for_group_stage(self, regular_user, group_matches):
        """Should return False for group stage (limit is 0)."""
        assert PredictionLimitService.can_add_joker(regular_user, "group") is False

    def test_combined_rounds_respect_shared_limit(self, regular_user, knockout_matches):
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
        assert PredictionLimitService.can_add_joker(regular_user, "sf") is False
        assert PredictionLimitService.can_add_joker(regular_user, "final") is False
        assert PredictionLimitService.can_add_joker(regular_user, "3rd") is False


class TestGetGroupStagePredictionCount:
    """Tests for get_group_stage_prediction_count method."""

    def test_counts_correctly(self, regular_user, group_matches):
        """Should count group stage predictions correctly."""
        # Create 5 predictions
        for match in group_matches[:5]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=1,
                predicted_goals_away=1,
            )

        count = PredictionLimitService.get_group_stage_prediction_count(regular_user)
        assert count == 5

    def test_ignores_knockout_predictions(self, regular_user, group_matches, knockout_matches):
        """Should not count knockout stage predictions."""
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

        count = PredictionLimitService.get_group_stage_prediction_count(regular_user)
        assert count == 1

    def test_zero_when_no_predictions(self, regular_user):
        """Should return 0 when user has no predictions."""
        count = PredictionLimitService.get_group_stage_prediction_count(regular_user)
        assert count == 0


class TestCanAddGroupStagePrediction:
    """Tests for can_add_group_stage_prediction method."""

    def test_returns_true_under_limit(self, regular_user, group_matches):
        """Should return True when under 36 predictions."""
        # Create 35 predictions
        for match in group_matches[:35]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=1,
                predicted_goals_away=1,
            )

        assert PredictionLimitService.can_add_group_stage_prediction(regular_user) is True

    def test_returns_false_at_limit(self, regular_user, group_matches):
        """Should return False when at 36 predictions."""
        # Create 36 predictions
        for match in group_matches[:36]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=1,
                predicted_goals_away=1,
            )

        assert PredictionLimitService.can_add_group_stage_prediction(regular_user) is False

    def test_returns_true_with_no_predictions(self, regular_user):
        """Should return True when user has no predictions."""
        assert PredictionLimitService.can_add_group_stage_prediction(regular_user) is True


class TestIsMatchLocked:
    """Tests for is_match_locked method."""

    def test_returns_true_when_2_minutes_before_kickoff(self, db):
        """Test match is locked 2 minutes before kickoff."""
        from datetime import datetime

        from django.utils import timezone

        from matches.models import Match, Team

        team_home = Team.objects.create(name="Germany", fifa_code="GER", odds_category="A")
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", odds_category="B")

        kickoff = timezone.make_aware(datetime(2026, 6, 15, 18, 0))
        match = Match.objects.create(
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

        from matches.models import Match, Team

        team_home = Team.objects.create(name="Germany", fifa_code="GER", odds_category="A")
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", odds_category="B")

        kickoff = timezone.make_aware(datetime(2026, 6, 15, 18, 0))
        match = Match.objects.create(
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

        from matches.models import Match, Team

        team_home = Team.objects.create(name="Germany", fifa_code="GER", odds_category="A")
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", odds_category="B")

        kickoff = timezone.make_aware(datetime(2026, 6, 15, 18, 0))
        match = Match.objects.create(
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

        from matches.models import Match, Team

        team_home = Team.objects.create(name="Germany", fifa_code="GER", odds_category="A")
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", odds_category="B")

        # Kickoff in the past
        kickoff = timezone.make_aware(datetime(2020, 6, 15, 18, 0))
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            status="scheduled",
        )

        # Should be locked (kickoff was 6 years ago)
        assert PredictionLimitService.is_match_locked(match) is True
