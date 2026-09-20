"""Tests for ScoringService."""

import pytest
from django.utils import timezone

from matches.models import Match, Team
from predictions.models import MatchPrediction
from scoring.champion_scoring import calculate_champion_points
from scoring.match_scoring import ScoringService
from users.models import User


@pytest.fixture
def team_home(db) -> Team:
    """Create home team fixture."""
    return Team.objects.create(name="Germany", fifa_code="GER", odds_category="A")


@pytest.fixture
def team_away(db) -> Team:
    """Create away team fixture."""
    return Team.objects.create(name="Brazil", fifa_code="BRA", odds_category="B")


@pytest.fixture
def group_match(db, team_home: Team, team_away: Team) -> Match:
    """Create group stage match fixture."""
    return Match.objects.create(
        team_home=team_home,
        team_away=team_away,
        kickoff=timezone.now(),
        round="group",
        status="finished",
        goals_home=2,
        goals_away=1,
    )


@pytest.fixture
def r16_match(db, team_home: Team, team_away: Team) -> Match:
    """Create round of 16 match fixture."""
    return Match.objects.create(
        team_home=team_home,
        team_away=team_away,
        kickoff=timezone.now(),
        round="r16",
        status="finished",
        goals_home=3,
        goals_away=0,
    )


@pytest.fixture
def final_match(db, team_home: Team, team_away: Team) -> Match:
    """Create final match fixture."""
    return Match.objects.create(
        team_home=team_home,
        team_away=team_away,
        kickoff=timezone.now(),
        round="final",
        status="finished",
        goals_home=1,
        goals_away=0,
    )


@pytest.fixture
def user(db) -> User:
    """Create user fixture."""
    return User.objects.create_user(username="testuser", password="test123")


class TestScoringCategories:
    """Test the 6 scoring categories per Shortytipp rules."""

    def test_exact_score_6_points(self, db, group_match: Match, user: User) -> None:
        """Test exact score prediction awards 6 base points."""
        prediction = MatchPrediction.objects.create(
            user=user,
            match=group_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        result = ScoringService.calculate_match_points(prediction, group_match)

        assert result["base_points"] == 6
        assert result["is_exact"] is True
        assert result["points"] == 6  # 6 * 1 (group multiplier) * 1 (no joker)

    def test_tendency_and_diff_5_points(self, db, group_match: Match, user: User) -> None:
        """Test correct tendency + goal difference awards 5 base points.

        Match result: 2-1 (home win, diff +1)
        Prediction: 3-2 (home win, diff +1) → 5 points
        """
        prediction = MatchPrediction.objects.create(
            user=user,
            match=group_match,
            predicted_goals_home=3,
            predicted_goals_away=2,
        )
        result = ScoringService.calculate_match_points(prediction, group_match)

        assert result["base_points"] == 5
        assert result["is_exact"] is False

    def test_tendency_and_one_goal_4_points(self, db, group_match: Match, user: User) -> None:
        """Test correct tendency + one team's goals awards 4 base points.

        Match result: 2-1 (home win)
        Prediction: 2-0 (home win, home goals correct, diff wrong) → 4 points
        """
        prediction = MatchPrediction.objects.create(
            user=user,
            match=group_match,
            predicted_goals_home=2,
            predicted_goals_away=0,
        )
        result = ScoringService.calculate_match_points(prediction, group_match)

        assert result["base_points"] == 4
        assert result["is_exact"] is False

    def test_tendency_only_3_points(self, db, group_match: Match, user: User) -> None:
        """Test correct tendency only awards 3 base points.

        Match result: 2-1 (home win)
        Prediction: 5-0 (home win, nothing else matches) → 3 points
        """
        prediction = MatchPrediction.objects.create(
            user=user,
            match=group_match,
            predicted_goals_home=5,
            predicted_goals_away=0,
        )
        result = ScoringService.calculate_match_points(prediction, group_match)

        assert result["base_points"] == 3
        assert result["is_exact"] is False

    def test_one_goal_only_1_point(self, db, group_match: Match, user: User) -> None:
        """Test one goal correct (wrong tendency) awards 1 point.

        Match result: 2-1 (home win)
        Prediction: 0-1 (away win, away goals correct) → 1 point
        """
        prediction = MatchPrediction.objects.create(
            user=user,
            match=group_match,
            predicted_goals_home=0,
            predicted_goals_away=1,
        )
        result = ScoringService.calculate_match_points(prediction, group_match)

        assert result["base_points"] == 1
        assert result["is_exact"] is False

    def test_no_match_0_points(self, db, group_match: Match, user: User) -> None:
        """Test no match awards 0 points.

        Match result: 2-1 (home win)
        Prediction: 0-3 (away win, no goals match) → 0 points
        """
        prediction = MatchPrediction.objects.create(
            user=user,
            match=group_match,
            predicted_goals_home=0,
            predicted_goals_away=3,
        )
        result = ScoringService.calculate_match_points(prediction, group_match)

        assert result["base_points"] == 0
        assert result["is_exact"] is False
        assert result["points"] == 0

    def test_scoring_precedence_higher_category_wins(
        self, db, group_match: Match, user: User
    ) -> None:
        """Test that higher scoring category takes precedence.

        Match result: 2-1
        Prediction: 2-1 → could match multiple categories but exact (6) wins.
        """
        prediction = MatchPrediction.objects.create(
            user=user,
            match=group_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        result = ScoringService.calculate_match_points(prediction, group_match)

        # Exact score (6) takes precedence over tendency+diff (5), etc.
        assert result["base_points"] == 6


class TestRoundMultipliers:
    """Test round multipliers per Shortytipp rules section 4."""

    def test_group_stage_x1(self, db, team_home: Team, team_away: Team, user: User) -> None:
        """Test group stage has x1 multiplier."""
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="finished",
            goals_home=2,
            goals_away=1,
        )
        # Exact prediction: 6 base * 1 = 6
        prediction = MatchPrediction.objects.create(
            user=user, match=match, predicted_goals_home=2, predicted_goals_away=1
        )
        result = ScoringService.calculate_match_points(prediction, match)
        assert result["points"] == 6

    def test_r32_x2(self, db, team_home: Team, team_away: Team, user: User) -> None:
        """Test round of 32 has x2 multiplier."""
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="r32",
            status="finished",
            goals_home=2,
            goals_away=1,
        )
        # Exact prediction: 6 base * 2 = 12
        prediction = MatchPrediction.objects.create(
            user=user, match=match, predicted_goals_home=2, predicted_goals_away=1
        )
        result = ScoringService.calculate_match_points(prediction, match)
        assert result["points"] == 12

    def test_r16_x2(self, db, team_home: Team, team_away: Team, user: User) -> None:
        """Test round of 16 has x2 multiplier."""
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="r16",
            status="finished",
            goals_home=2,
            goals_away=1,
        )
        # Exact prediction: 6 base * 2 = 12
        prediction = MatchPrediction.objects.create(
            user=user, match=match, predicted_goals_home=2, predicted_goals_away=1
        )
        result = ScoringService.calculate_match_points(prediction, match)
        assert result["points"] == 12

    def test_knockout_x3(self, db, team_home: Team, team_away: Team, user: User) -> None:
        """Test quarter-final and beyond has x3 multiplier."""
        for round_name in ["qf", "sf", "3rd", "final"]:
            match = Match.objects.create(
                team_home=team_home,
                team_away=team_away,
                kickoff=timezone.now(),
                round=round_name,
                status="finished",
                goals_home=2,
                goals_away=1,
            )
            # Exact prediction: 6 base * 3 = 18
            prediction = MatchPrediction.objects.create(
                user=user, match=match, predicted_goals_home=2, predicted_goals_away=1
            )
            result = ScoringService.calculate_match_points(prediction, match)
            assert result["points"] == 18, f"Failed for round {round_name}"


class TestJokerMultiplier:
    """Test joker doubling per Shortytipp rules section 6."""

    def test_joker_doubles_points(self, db, r16_match: Match, user: User) -> None:
        """Test joker doubles the final points.

        r16 match (x2), exact score (6 base), joker (x2)
        6 * 2 * 2 = 24
        """
        prediction = MatchPrediction.objects.create(
            user=user,
            match=r16_match,
            predicted_goals_home=3,
            predicted_goals_away=0,
            joker_active=True,
        )
        result = ScoringService.calculate_match_points(prediction, r16_match)

        assert result["base_points"] == 6
        assert result["points"] == 24  # 6 * 2 * 2

    def test_combined_base_round_joker(self, db, final_match: Match, user: User) -> None:
        """Test formula: base * round * joker.

        Final match (x3), exact score (6 base), joker (x2)
        6 * 3 * 2 = 36
        """
        prediction = MatchPrediction.objects.create(
            user=user,
            match=final_match,
            predicted_goals_home=1,
            predicted_goals_away=0,
            joker_active=True,
        )
        result = ScoringService.calculate_match_points(prediction, final_match)

        assert result["points"] == 36  # 6 * 3 * 2


class TestChampionPrediction:
    """Test champion prediction scoring per Shortytipp rules section 8."""

    def test_champion_category_a_20_points(self, db, team_home: Team) -> None:
        """Test category A champion prediction awards 20 points."""
        team_home.odds_category = "A"
        team_home.save()

        points = calculate_champion_points(team_home)
        assert points == 20

    def test_champion_category_b_30_points(self, db, team_away: Team) -> None:
        """Test category B champion prediction awards 30 points."""
        team_away.odds_category = "B"
        team_away.save()

        points = calculate_champion_points(team_away)
        assert points == 30

    def test_champion_no_category_0_points(self, db) -> None:
        """Test champion with no category awards 0 points."""
        team = Team.objects.create(name="Unknown", fifa_code="UNK", odds_category=None)
        points = calculate_champion_points(team)
        assert points == 0


class TestScorePrediction:
    """Test score_prediction method updates database."""

    def test_score_prediction_updates_prediction(self, db, group_match: Match, user: User) -> None:
        """Test score_prediction updates prediction fields."""
        prediction = MatchPrediction.objects.create(
            user=user,
            match=group_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        ScoringService.score_prediction(prediction)

        prediction.refresh_from_db()
        assert prediction.points_earned == 6
        assert prediction.is_exact_match is True

    def test_score_prediction_updates_user_stats(self, db, group_match: Match, user: User) -> None:
        """Test score_prediction updates user statistics."""
        prediction = MatchPrediction.objects.create(
            user=user,
            match=group_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        ScoringService.score_prediction(prediction)

        user.refresh_from_db()
        assert user.total_points == 6
        assert user.exact_match_count == 1
        assert user.jokers_used == 0

    def test_score_prediction_with_joker_updates_jokers_used(
        self, db, group_match: Match, user: User
    ) -> None:
        """Test scoring with joker increments jokers_used."""
        prediction = MatchPrediction.objects.create(
            user=user,
            match=group_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=True,
        )

        ScoringService.score_prediction(prediction)

        user.refresh_from_db()
        assert user.jokers_used == 1


class TestRoundValidation:
    """Test round code validation."""

    def test_invalid_round_code_raises_error(self) -> None:
        """Unknown round codes must raise ValueError, not silently default to 1."""
        with pytest.raises(ValueError, match="Unknown round 'playoffs'"):
            ScoringService._get_round_multiplier("playoffs")

    def test_all_valid_round_codes_return_correct_multipliers(self) -> None:
        """All valid round codes return correct multipliers."""
        assert ScoringService._get_round_multiplier("group") == 1
        assert ScoringService._get_round_multiplier("r32") == 2
        assert ScoringService._get_round_multiplier("r16") == 2
        assert ScoringService._get_round_multiplier("qf") == 3
        assert ScoringService._get_round_multiplier("sf") == 3
        assert ScoringService._get_round_multiplier("3rd") == 3
        assert ScoringService._get_round_multiplier("final") == 3

    def test_invalid_round_error_message_lists_valid_rounds(self) -> None:
        """Error message for invalid round should list all valid rounds."""
        with pytest.raises(ValueError) as exc_info:
            ScoringService._get_round_multiplier("invalid")

        error_message = str(exc_info.value)
        assert "Unknown round 'invalid'" in error_message
        assert "Valid rounds:" in error_message
        # Check that at least some valid rounds are mentioned
        assert "group" in error_message
        assert "final" in error_message
