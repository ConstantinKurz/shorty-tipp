"""Tests for automatic scoring trigger on match save."""

import pytest
from django.utils import timezone

from matches.models import Match, Team
from predictions.models import MatchPrediction
from users.models import User


@pytest.fixture
def team_home(db) -> Team:
    """Create home team."""
    return Team.objects.create(name="Germany", fifa_code="GER")


@pytest.fixture
def team_away(db) -> Team:
    """Create away team."""
    return Team.objects.create(name="Brazil", fifa_code="BRA")


@pytest.fixture
def user(db) -> User:
    """Create test user."""
    return User.objects.create_user(username="testuser", password="test123")


class TestMatchScoringTrigger:
    """Test automatic scoring when match results are saved."""

    def test_scoring_triggered_on_match_save_with_results(
        self, db, team_home: Team, team_away: Team, user: User
    ) -> None:
        """Test predictions are scored when match result is saved."""
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="scheduled",
        )

        prediction = MatchPrediction.objects.create(
            user=user,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # Save match with results
        match.goals_home = 2
        match.goals_away = 1
        match.status = "finished"
        match.save()

        # Prediction should be scored
        prediction.refresh_from_db()
        assert prediction.points_earned == 6
        assert prediction.is_exact_match is True

    def test_user_stats_updated_after_match_save(
        self, db, team_home: Team, team_away: Team, user: User
    ) -> None:
        """Test user statistics are updated when match is scored."""
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="scheduled",
        )

        MatchPrediction.objects.create(
            user=user,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # Save match with results
        match.goals_home = 2
        match.goals_away = 1
        match.save()

        # User stats should be updated
        user.refresh_from_db()
        assert user.total_points == 6
        assert user.exact_match_count == 1

    def test_re_scoring_when_result_changes(
        self, db, team_home: Team, team_away: Team, user: User
    ) -> None:
        """Test predictions are re-scored when match result changes."""
        # Create match without results first
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="scheduled",
        )

        prediction = MatchPrediction.objects.create(
            user=user,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # Add initial result (this triggers scoring)
        match.goals_home = 2
        match.goals_away = 1
        match.status = "finished"
        match.save()

        # Check initial scoring
        prediction.refresh_from_db()
        user.refresh_from_db()
        initial_points = user.total_points
        assert initial_points == 6  # Exact match
        assert prediction.is_exact_match is True

        # Change result (VAR decision!)
        match.goals_home = 2
        match.goals_away = 2  # Changed to draw
        match.save()

        # Re-check prediction
        prediction.refresh_from_db()
        user.refresh_from_db()

        # Points should be recalculated (exact match no longer)
        assert prediction.is_exact_match is False
        # User should have fewer points now (5 for tendency+diff instead of 6)
        assert user.total_points < initial_points

    def test_no_scoring_when_goals_not_set(
        self, db, team_home: Team, team_away: Team, user: User
    ) -> None:
        """Test no scoring when match doesn't have goals set."""
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="scheduled",
            goals_home=None,
            goals_away=None,
        )

        prediction = MatchPrediction.objects.create(
            user=user,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # Save match without results
        match.save()

        # Prediction should not be scored
        prediction.refresh_from_db()
        assert prediction.points_earned is None

    def test_multiple_predictions_scored(
        self, db, team_home: Team, team_away: Team
    ) -> None:
        """Test all predictions for a match are scored."""
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="scheduled",
        )

        users = [
            User.objects.create_user(username=f"user{i}", password="test")
            for i in range(3)
        ]

        predictions = [
            MatchPrediction.objects.create(
                user=user,
                match=match,
                predicted_goals_home=2,
                predicted_goals_away=1,
            )
            for user in users
        ]

        # Save match with results
        match.goals_home = 2
        match.goals_away = 1
        match.save()

        # All predictions should be scored
        for pred in predictions:
            pred.refresh_from_db()
            assert pred.points_earned == 6


class TestFinalMatchChampionScoring:
    """Test champion scoring is triggered for final match."""

    def test_champion_scoring_triggered_for_final(
        self, db, team_home: Team, team_away: Team, user: User
    ) -> None:
        """Test champion predictions are scored when final match saved."""
        # Set odds category for champion points calculation
        team_home.odds_category = "A"
        team_home.save()

        # User predicted champion correctly
        user.predicted_champion = team_home
        user.save()

        # Create final match
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=1,
            goals_away=0,
        )

        # User should have champion points
        user.refresh_from_db()
        assert user.total_points == 20  # Category A champion points
