"""Tests for champion prediction scoring."""

import pytest
from django.utils import timezone

from matches.models import Match, Team
from scoring.services import ScoringService
from users.models import User


@pytest.fixture
def champion_team(db) -> Team:
    """Create champion team (category A)."""
    return Team.objects.create(
        name="Germany",
        fifa_code="GER",
        odds_category="A",
        is_champion=True,
    )


@pytest.fixture
def runner_up_team(db) -> Team:
    """Create runner-up team."""
    return Team.objects.create(
        name="Brazil",
        fifa_code="BRA",
        odds_category="B",
        is_champion=False,
    )


@pytest.fixture
def finished_final(db, champion_team: Team, runner_up_team: Team) -> Match:
    """Create finished final match."""
    return Match.objects.create(
        team_home=champion_team,
        team_away=runner_up_team,
        kickoff=timezone.now(),
        round="final",
        status="finished",
        goals_home=1,
        goals_away=0,
    )


class TestChampionPointsAwarded:
    """Test champion points are awarded correctly."""

    def test_points_awarded_when_prediction_matches_champion(
        self, db, champion_team: Team, finished_final: Match
    ) -> None:
        """Test user receives points when their prediction matches champion."""
        user = User.objects.create_user(
            username="winner",
            password="test",
            predicted_champion=champion_team,
        )

        count = ScoringService.score_champion_predictions()

        user.refresh_from_db()
        assert count == 1
        assert user.total_points == 20  # Category A

    def test_no_points_when_prediction_wrong(
        self, db, champion_team: Team, runner_up_team: Team, finished_final: Match
    ) -> None:
        """Test user receives no points when prediction doesn't match."""
        user = User.objects.create_user(
            username="loser",
            password="test",
            predicted_champion=runner_up_team,
        )

        count = ScoringService.score_champion_predictions()

        user.refresh_from_db()
        assert count == 0  # No users awarded
        assert user.total_points == 0


class TestChampionCategories:
    """Test champion scoring by odds category."""

    def test_category_a_champion_20_points(
        self, db, champion_team: Team, runner_up_team: Team, finished_final: Match
    ) -> None:
        """Test category A champion awards 20 points."""
        champion_team.odds_category = "A"
        champion_team.save()

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=champion_team,
        )

        ScoringService.score_champion_predictions()

        user.refresh_from_db()
        assert user.total_points == 20

    def test_category_b_champion_30_points(
        self, db, runner_up_team: Team
    ) -> None:
        """Test category B champion awards 30 points."""
        # Make runner_up the champion
        runner_up_team.is_champion = True
        runner_up_team.odds_category = "B"
        runner_up_team.save()

        # Create a team for home (doesn't matter who)
        home_team = Team.objects.create(name="France", fifa_code="FRA")

        # Create final match
        Match.objects.create(
            team_home=home_team,
            team_away=runner_up_team,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=0,
            goals_away=1,
        )

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=runner_up_team,
        )

        ScoringService.score_champion_predictions()

        user.refresh_from_db()
        assert user.total_points == 30


class TestChampionScoringTriggers:
    """Test when champion scoring triggers."""

    def test_no_scoring_without_champion_set(self, db) -> None:
        """Test no scoring when no team has is_champion=True."""
        team = Team.objects.create(
            name="Germany",
            fifa_code="GER",
            is_champion=False,
        )

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=team,
        )

        count = ScoringService.score_champion_predictions()

        assert count == 0
        user.refresh_from_db()
        assert user.total_points == 0

    def test_no_scoring_without_finished_final(
        self, db, champion_team: Team, runner_up_team: Team
    ) -> None:
        """Test no scoring when final match not finished."""
        # Create unfinished final
        Match.objects.create(
            team_home=champion_team,
            team_away=runner_up_team,
            kickoff=timezone.now(),
            round="final",
            status="scheduled",  # Not finished
        )

        User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=champion_team,
        )

        count = ScoringService.score_champion_predictions()

        assert count == 0


class TestMultipleUsers:
    """Test champion scoring with multiple users."""

    def test_multiple_users_predicting_champion_all_receive_points(
        self, db, champion_team: Team, finished_final: Match
    ) -> None:
        """Test all users who predicted champion receive points."""
        users = [
            User.objects.create_user(
                username=f"user{i}",
                password="test",
                predicted_champion=champion_team,
            )
            for i in range(3)
        ]

        count = ScoringService.score_champion_predictions()

        assert count == 3
        for user in users:
            user.refresh_from_db()
            assert user.total_points == 20


class TestChampionMatchPredictionSeparation:
    """Test champion scoring is separate from match prediction scoring."""

    def test_champion_scoring_separate_from_match_prediction(
        self, db, champion_team: Team, runner_up_team: Team, finished_final: Match
    ) -> None:
        """Test champion points don't affect match prediction points."""
        from predictions.models import MatchPrediction

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=champion_team,
            total_points=50,  # Existing points from match predictions
        )

        # Create a match prediction for the final
        MatchPrediction.objects.create(
            user=user,
            match=finished_final,
            predicted_goals_home=1,
            predicted_goals_away=0,
            points_earned=18,  # Already scored
        )

        # Score champion predictions
        ScoringService.score_champion_predictions()

        user.refresh_from_db()
        # Should add champion points (20) to existing points (50)
        assert user.total_points == 70
