"""Tests for scoring aggregate edge cases.

Tests verify that User model aggregates (total_points, exact_match_count,
jokers_used, champion_bonus_points) are correctly maintained across various
scoring scenarios including first scoring, rescoring, and result changes.
"""

import pytest
from django.utils import timezone

from matches.models import Match, Team
from predictions.models import MatchPrediction
from scoring.match_scoring import ScoringService
from users.models import User


@pytest.fixture
def team_home(db) -> Team:
    """Create home team fixture."""
    return Team.objects.create(name="Germany", fifa_code="GER")


@pytest.fixture
def team_away(db) -> Team:
    """Create away team fixture."""
    return Team.objects.create(name="Brazil", fifa_code="BRA")


@pytest.fixture
def user(db) -> User:
    """Create user fixture."""
    return User.objects.create_user(username="testuser", password="test123")


@pytest.fixture
def finished_match(db, team_home: Team, team_away: Team) -> Match:
    """Create a finished match with result 2-1."""
    return Match.objects.create(
        team_home=team_home,
        team_away=team_away,
        kickoff=timezone.now(),
        round="group",
        status="finished",
        goals_home=2,
        goals_away=1,
    )


class TestFirstScoring:
    """Test first-time scoring of predictions."""

    def test_first_scoring_increments_total_points(
        self, db, finished_match: Match, user: User
    ) -> None:
        """First scoring should increment user total_points from 0 to 6."""
        prediction = MatchPrediction.objects.create(
            user=user,
            match=finished_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # Verify initial state
        assert user.total_points == 0
        assert user.exact_match_count == 0

        # Score the prediction
        ScoringService.score_prediction(prediction)

        # Verify user aggregates updated
        user.refresh_from_db()
        assert user.total_points == 6
        assert user.exact_match_count == 1


class TestUnchangedRescoring:
    """Test rescoring when result hasn't changed."""

    def test_unchanged_rescoring_no_delta(self, db, finished_match: Match, user: User) -> None:
        """Rescoring unchanged result should have zero delta."""
        prediction = MatchPrediction.objects.create(
            user=user,
            match=finished_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # First scoring
        ScoringService.score_prediction(prediction)
        user.refresh_from_db()
        assert user.total_points == 6

        # Rescore with same result (simulating re-run)
        ScoringService.score_prediction(prediction)
        user.refresh_from_db()

        # Points should remain unchanged
        assert user.total_points == 6
        assert user.exact_match_count == 1


class TestChangedResult:
    """Test rescoring when match result changes."""

    def test_changed_result_decrements_points(
        self, db, team_home: Team, team_away: Team, user: User
    ) -> None:
        """Changing result from exact (6 pts) to tendency (3 pts) should decrement total."""
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="finished",
            goals_home=2,
            goals_away=1,
        )

        prediction = MatchPrediction.objects.create(
            user=user,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # First scoring: exact match (6 points)
        ScoringService.score_prediction(prediction)
        user.refresh_from_db()
        assert user.total_points == 6
        assert user.exact_match_count == 1

        # Match result changes to 3-1
        match.goals_home = 3
        match.save()
        match.refresh_from_db()
        prediction.refresh_from_db()

        # Rescore
        ScoringService.score_prediction(prediction)
        user.refresh_from_db()

        # Prediction 2-1 vs actual 3-1 = tendency + away goal correct = 4 points
        assert user.total_points == 4
        assert user.exact_match_count == 0


class TestExactMatchTransitions:
    """Test transitions between exact and non-exact matches."""

    def test_non_exact_to_exact_increments_count(
        self, db, team_home: Team, team_away: Team, user: User
    ) -> None:
        """Changing from non-exact to exact should increment exact_match_count."""
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="finished",
            goals_home=3,
            goals_away=1,
        )

        prediction = MatchPrediction.objects.create(
            user=user,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # First scoring: tendency only (3 points, not exact)
        ScoringService.score_prediction(prediction)
        user.refresh_from_db()
        # Prediction 2-1 vs actual 3-1 = tendency + away goal correct = 4 points
        assert user.total_points == 4
        assert user.exact_match_count == 0

        # Match result changes to 2-1 (now exact match)
        match.goals_home = 2
        match.save()
        match.refresh_from_db()
        prediction.refresh_from_db()

        # Rescore
        ScoringService.score_prediction(prediction)
        user.refresh_from_db()

        # Points increase to 6, exact count to 1
        assert user.total_points == 6
        assert user.exact_match_count == 1

    def test_exact_to_non_exact_decrements_count(
        self, db, finished_match: Match, user: User
    ) -> None:
        """Changing from exact to non-exact should decrement exact_match_count."""
        prediction = MatchPrediction.objects.create(
            user=user,
            match=finished_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # First scoring: exact match (6 points)
        ScoringService.score_prediction(prediction)
        user.refresh_from_db()
        assert user.total_points == 6
        assert user.exact_match_count == 1

        # Match result changes to 3-1 (no longer exact)
        finished_match.goals_home = 3
        finished_match.save()
        finished_match.refresh_from_db()
        prediction.refresh_from_db()

        # Rescore
        ScoringService.score_prediction(prediction)
        user.refresh_from_db()

        # Prediction 2-1 vs actual 3-1 = tendency + away goal correct = 4 points
        assert user.total_points == 4
        assert user.exact_match_count == 0


class TestJokerEdgeCases:
    """Test joker-related aggregate edge cases."""

    def test_joker_first_scored_increments_jokers_used(
        self, db, finished_match: Match, user: User
    ) -> None:
        """First time scoring a joker should increment jokers_used."""
        prediction = MatchPrediction.objects.create(
            user=user,
            match=finished_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=True,
        )

        # Verify initial state
        assert user.jokers_used == 0

        # Score the joker prediction
        ScoringService.score_prediction(prediction)

        # Verify jokers_used incremented
        user.refresh_from_db()
        assert user.jokers_used == 1
        assert user.total_points == 12  # 6 * 2 (joker)

    def test_joker_rescored_unchanged(self, db, finished_match: Match, user: User) -> None:
        """Rescoring a joker should not double-count jokers_used."""
        prediction = MatchPrediction.objects.create(
            user=user,
            match=finished_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=True,
        )

        # First scoring
        ScoringService.score_prediction(prediction)
        user.refresh_from_db()
        assert user.jokers_used == 1

        # Rescore (simulating match update)
        ScoringService.score_prediction(prediction)
        user.refresh_from_db()

        # jokers_used should still be 1, not 2
        assert user.jokers_used == 1
        assert user.total_points == 12


class TestChampionBonusInvariant:
    """Test that champion bonus is preserved in total_points."""

    def test_champion_bonus_invariant(self, db, finished_match: Match, user: User) -> None:
        """Verify total_points = match_points + champion_bonus_points."""
        # Set up user with champion bonus
        user.champion_bonus_points = 20
        user.total_points = 20  # Just the bonus
        user.save()

        prediction = MatchPrediction.objects.create(
            user=user,
            match=finished_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # Score the prediction
        ScoringService.score_prediction(prediction)

        # Verify total_points includes both match points and champion bonus
        user.refresh_from_db()
        assert user.champion_bonus_points == 20
        assert user.total_points == 26  # 6 (match) + 20 (champion)

    def test_multiple_predictions_with_champion_bonus(
        self, db, team_home: Team, team_away: Team, user: User
    ) -> None:
        """Verify champion bonus preserved across multiple match scorings."""
        # Set up user with champion bonus
        user.champion_bonus_points = 30
        user.total_points = 30
        user.save()

        # Create two matches
        match1 = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="finished",
            goals_home=2,
            goals_away=1,
        )
        match2 = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="finished",
            goals_home=1,
            goals_away=0,
        )

        # Create predictions
        pred1 = MatchPrediction.objects.create(
            user=user,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        pred2 = MatchPrediction.objects.create(
            user=user,
            match=match2,
            predicted_goals_home=1,
            predicted_goals_away=0,
        )

        # Score both predictions
        ScoringService.score_prediction(pred1)
        ScoringService.score_prediction(pred2)

        # Verify total_points = match_points + champion_bonus
        user.refresh_from_db()
        assert user.champion_bonus_points == 30
        assert user.total_points == 42  # 6 + 6 + 30
