"""End-to-end integration tests for API sync and scoring."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from matches.models import Match, Team
from matches.services import sync_matches_from_api
from predictions.models import MatchPrediction
from scoring.match_scoring import ScoringService
from users.models import User


@pytest.mark.django_db
class TestAPIIntegration:
    """End-to-end integration tests for API sync and scoring."""

    @pytest.fixture
    def users(self) -> tuple[User, User, User]:
        """Create test users."""
        user1 = User.objects.create_user(username="alice", email="alice@test.com")
        user2 = User.objects.create_user(username="bob", email="bob@test.com")
        user3 = User.objects.create_user(username="charlie", email="charlie@test.com")
        return user1, user2, user3

    @pytest.fixture
    def teams(self) -> tuple[Team, Team]:
        """Create test teams."""
        germany = Team.objects.create(name="Germany", fifa_code="GER")
        brazil = Team.objects.create(name="Brazil", fifa_code="BRA")
        return germany, brazil

    @pytest.fixture
    def match(self, teams: tuple[Team, Team]) -> Match:
        """Create test match."""
        germany, brazil = teams
        return Match.objects.create(
            external_id=1001,
            team_home=germany,
            team_away=brazil,
            kickoff=datetime(2026, 6, 20, 18, 0, tzinfo=UTC),
            round="group",
            status="scheduled",
            goals_home=None,
            goals_away=None,
        )

    def test_full_sync_and_scoring_flow(
        self, users: tuple[User, User, User], teams: tuple[Team, Team], match: Match
    ) -> None:
        """Verify full flow: API sync → goal detection → scoring → user points update."""
        user1, user2, user3 = users
        germany, brazil = teams

        # Create predictions for the match
        pred1 = MatchPrediction.objects.create(
            user=user1,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        pred2 = MatchPrediction.objects.create(
            user=user2,
            match=match,
            predicted_goals_home=1,
            predicted_goals_away=1,
        )
        pred3 = MatchPrediction.objects.create(
            user=user3,
            match=match,
            predicted_goals_home=0,
            predicted_goals_away=2,
        )

        # Mock API response with match result
        mock_matches_data = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "FINISHED",
                "stage": "GROUP_STAGE",
                "score": {"fullTime": {"home": 2, "away": 1}},
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_matches_data

            # Sync matches from API
            results = sync_matches_from_api()

            # Verify sync detected goal change
            assert len(results) == 1
            assert results[0].goals_changed is True

            # Trigger scoring for the match
            scored_count = ScoringService.score_all_predictions_for_match(results[0].match)

            # Verify predictions were scored
            assert scored_count == 3

            # Verify prediction points
            pred1.refresh_from_db()
            pred2.refresh_from_db()
            pred3.refresh_from_db()

            assert pred1.points_earned == 6  # Exact score
            assert pred2.points_earned == 1  # One goal match (away=1)
            assert pred3.points_earned == 0  # Wrong

            # Verify user total points
            user1.refresh_from_db()
            user2.refresh_from_db()
            user3.refresh_from_db()

            assert user1.total_points == 6
            assert user2.total_points == 1
            assert user3.total_points == 0

    def test_multiple_users_scored_for_same_match(
        self, teams: tuple[Team, Team], match: Match
    ) -> None:
        """Verify all user predictions are scored when match is updated."""
        germany, brazil = teams

        # Create 5 users with predictions
        users_and_predictions = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@test.com",
            )
            pred = MatchPrediction.objects.create(
                user=user,
                match=match,
                predicted_goals_home=2,
                predicted_goals_away=1,
            )
            users_and_predictions.append((user, pred))

        # Mock API response
        mock_matches_data = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "FINISHED",
                "stage": "GROUP_STAGE",
                "score": {"fullTime": {"home": 2, "away": 1}},
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_matches_data

            results = sync_matches_from_api()
            ScoringService.score_all_predictions_for_match(results[0].match)

            # Verify all 5 users got points
            for user, pred in users_and_predictions:
                pred.refresh_from_db()
                user.refresh_from_db()
                assert pred.points_earned == 6
                assert user.total_points == 6

    def test_incremental_goal_updates(
        self, users: tuple[User, User, User], teams: tuple[Team, Team], match: Match
    ) -> None:
        """Verify scoring updates correctly as goals change: 0:0 → 1:0 → 1:1."""
        user1, user2, user3 = users
        germany, brazil = teams

        # Create predictions
        pred1 = MatchPrediction.objects.create(
            user=user1, match=match, predicted_goals_home=1, predicted_goals_away=1
        )
        pred2 = MatchPrediction.objects.create(
            user=user2, match=match, predicted_goals_home=2, predicted_goals_away=0
        )

        # Simulate 0:0 (no goals yet)
        mock_data_0_0 = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "IN_PLAY",
                "stage": "GROUP_STAGE",
                "score": {"fullTime": {"home": 0, "away": 0}},
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_data_0_0

            results = sync_matches_from_api()
            # First sync changes from None to 0, so marked as changed
            assert results[0].goals_changed is True

        # Simulate 1:0 update
        mock_data_1_0 = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "IN_PLAY",
                "stage": "GROUP_STAGE",
                "score": {"fullTime": {"home": 1, "away": 0}},
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_data_1_0

            results = sync_matches_from_api()
            assert results[0].goals_changed is True  # Goals changed!

            ScoringService.score_all_predictions_for_match(results[0].match)

            pred1.refresh_from_db()
            pred2.refresh_from_db()

            # At 1:0, user2 has correct tendency + one goal, user1 has one goal
            assert pred2.points_earned == 4  # Correct tendency + one goal (away=0)
            assert pred1.points_earned == 1  # One goal match (home=1)

        # Simulate 1:1 final score
        mock_data_1_1 = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "FINISHED",
                "stage": "GROUP_STAGE",
                "score": {"fullTime": {"home": 1, "away": 1}},
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_data_1_1

            results = sync_matches_from_api()
            assert results[0].goals_changed is True  # Goals changed again!

            ScoringService.score_all_predictions_for_match(results[0].match)

            pred1.refresh_from_db()
            pred2.refresh_from_db()
            user1.refresh_from_db()
            user2.refresh_from_db()

            # At 1:1, user1 has exact score, user2 has wrong
            assert pred1.points_earned == 6  # Exact score
            assert pred2.points_earned == 0  # Wrong

            assert user1.total_points == 6
            assert user2.total_points == 0
