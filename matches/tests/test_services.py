"""Tests for match sync services."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from matches import services
from matches.models import Match, Team
from matches.services import sync_matches_from_api, sync_teams_from_api


@pytest.mark.django_db
class TestSyncTeamsFromAPI:
    """Test suite for sync_teams_from_api service."""

    def test_sync_teams_creates_new_teams(self) -> None:
        """Verify sync_teams_from_api creates new teams from API data."""
        mock_teams_data = [
            {"id": 1, "name": "Germany", "tla": "GER"},
            {"id": 2, "name": "Brazil", "tla": "BRA"},
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_teams.return_value = mock_teams_data

            created, updated, _ = sync_teams_from_api()

            assert created == 2
            assert updated == 0
            assert Team.objects.count() == 2
            assert Team.objects.filter(fifa_code="GER").exists()
            assert Team.objects.filter(fifa_code="BRA").exists()

    def test_sync_teams_updates_existing_teams(self) -> None:
        """Verify sync_teams_from_api updates existing teams by fifa_code."""
        # Create existing team with old name
        Team.objects.create(name="Old Germany Name", fifa_code="GER")

        mock_teams_data = [
            {"id": 1, "name": "Germany", "tla": "GER"},
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_teams.return_value = mock_teams_data

            created, updated, _ = sync_teams_from_api()

            assert created == 0
            assert updated == 1
            assert Team.objects.count() == 1

            team = Team.objects.get(fifa_code="GER")
            assert team.name == "Germany"  # Name updated

    def test_sync_teams_skips_incomplete_data(self) -> None:
        """Verify sync skips teams with missing tla or name."""
        mock_teams_data = [
            {"id": 1, "name": "Germany", "tla": "GER"},
            {"id": 2, "name": "Brazil"},  # Missing tla
            {"id": 3, "tla": "FRA"},  # Missing name
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_teams.return_value = mock_teams_data

            created, updated, _ = sync_teams_from_api()

            assert created == 1
            assert updated == 0
            assert Team.objects.count() == 1
            assert Team.objects.filter(fifa_code="GER").exists()


@pytest.mark.django_db
class TestSyncMatchesFromAPI:
    """Test suite for sync_matches_from_api service."""

    @pytest.fixture
    def teams(self) -> tuple[Team, Team]:
        """Create test teams."""
        team_home = Team.objects.create(name="Germany", fifa_code="GER")
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA")
        return team_home, team_away

    def test_sync_matches_creates_new_matches(self, teams: tuple[Team, Team]) -> None:
        """Verify sync_matches_from_api creates new matches from API data."""
        mock_matches_data = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "SCHEDULED",
                "stage": "GROUP_STAGE",
                "score": {"fullTime": {"home": None, "away": None}},
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_matches_data

            results = sync_matches_from_api()

            assert len(results) == 1
            assert results[0].goals_changed is False  # New match
            assert Match.objects.count() == 1

            match = Match.objects.get(external_id=1001)
            assert match.team_home.fifa_code == "GER"
            assert match.team_away.fifa_code == "BRA"
            assert match.status == "scheduled"
            assert match.round == "group"

    def test_sync_matches_updates_existing_matches(self, teams: tuple[Team, Team]) -> None:
        """Verify sync_matches_from_api updates existing matches by external_id."""
        # Create existing match
        team_home, team_away = teams
        Match.objects.create(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=datetime(2026, 6, 20, 18, 0, tzinfo=UTC),
            round="group",
            status="scheduled",
            goals_home=None,
            goals_away=None,
        )

        # API returns updated status
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

            assert len(results) == 1
            assert Match.objects.count() == 1

            match = Match.objects.get(external_id=1001)
            assert match.status == "finished"
            assert match.goals_home == 2
            assert match.goals_away == 1

    def test_sync_matches_detects_goal_changes(self, teams: tuple[Team, Team]) -> None:
        """Verify sync detects when goals change."""
        team_home, team_away = teams

        # Create match with 0-0 score
        Match.objects.create(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=datetime(2026, 6, 20, 18, 0, tzinfo=UTC),
            round="group",
            status="live",
            goals_home=0,
            goals_away=0,
        )

        # API returns updated score 1-0
        mock_matches_data = [
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
            mock_client.get_matches.return_value = mock_matches_data

            results = sync_matches_from_api()

            assert len(results) == 1
            assert results[0].goals_changed is True  # Goals changed!

    def test_sync_matches_status_mapping(self, teams: tuple[Team, Team]) -> None:
        """Verify API status values map correctly to Django status."""
        team_home, team_away = teams

        test_cases = [
            ("SCHEDULED", "scheduled"),
            ("TIMED", "scheduled"),
            ("IN_PLAY", "live"),
            ("PAUSED", "live"),
            ("FINISHED", "finished"),
        ]

        for api_status, expected_status in test_cases:
            mock_matches_data = [
                {
                    "id": 2000 + test_cases.index((api_status, expected_status)),
                    "homeTeam": {"name": "Germany", "tla": "GER"},
                    "awayTeam": {"name": "Brazil", "tla": "BRA"},
                    "utcDate": "2026-06-20T18:00:00Z",
                    "status": api_status,
                    "stage": "GROUP_STAGE",
                    "score": {"fullTime": {"home": None, "away": None}},
                }
            ]

            with patch("matches.services.FootballDataClient") as MockClient:
                mock_client = MockClient.return_value
                mock_client.get_matches.return_value = mock_matches_data

                results = sync_matches_from_api()
                assert results[0].match.status == expected_status

    def test_sync_matches_round_mapping(self, teams: tuple[Team, Team]) -> None:
        """Verify API stage values map correctly to Django round."""
        team_home, team_away = teams

        test_cases = [
            ("GROUP_STAGE", "group"),
            ("ROUND_OF_32", "r32"),
            ("ROUND_OF_16", "r16"),
            ("QUARTER_FINALS", "qf"),
            ("SEMI_FINALS", "sf"),
            ("THIRD_PLACE", "3rd"),
            ("FINAL", "final"),
        ]

        for api_stage, expected_round in test_cases:
            mock_matches_data = [
                {
                    "id": 3000 + test_cases.index((api_stage, expected_round)),
                    "homeTeam": {"name": "Germany", "tla": "GER"},
                    "awayTeam": {"name": "Brazil", "tla": "BRA"},
                    "utcDate": "2026-06-20T18:00:00Z",
                    "status": "SCHEDULED",
                    "stage": api_stage,
                    "score": {"fullTime": {"home": None, "away": None}},
                }
            ]

            with patch("matches.services.FootballDataClient") as MockClient:
                mock_client = MockClient.return_value
                mock_client.get_matches.return_value = mock_matches_data

                results = sync_matches_from_api()
                assert results[0].match.round == expected_round

    def test_sync_matches_skips_missing_teams(self) -> None:
        """Verify sync skips matches when teams are not in database."""
        # Don't create any teams

        mock_matches_data = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "SCHEDULED",
                "stage": "GROUP_STAGE",
                "score": {"fullTime": {"home": None, "away": None}},
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_matches_data

            results = sync_matches_from_api()

            assert len(results) == 0  # Match skipped
            assert Match.objects.count() == 0

    def test_sync_match_stores_winner_home_team(self, teams: tuple[Team, Team]) -> None:
        """Verify sync stores winner='home' when API returns HOME_TEAM."""
        mock_matches_data = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "FINISHED",
                "stage": "FINAL",
                "score": {
                    "winner": "HOME_TEAM",
                    "fullTime": {"home": 2, "away": 1},
                },
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_matches_data

            results = sync_matches_from_api()

            assert len(results) == 1
            match = results[0].match
            assert match.winner == "home"

    def test_sync_match_stores_winner_away_team(self, teams: tuple[Team, Team]) -> None:
        """Verify sync stores winner='away' when API returns AWAY_TEAM."""
        mock_matches_data = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "FINISHED",
                "stage": "FINAL",
                "score": {
                    "winner": "AWAY_TEAM",
                    "fullTime": {"home": 0, "away": 1},
                },
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_matches_data

            results = sync_matches_from_api()

            assert len(results) == 1
            match = results[0].match
            assert match.winner == "away"

    def test_sync_match_stores_winner_draw(self, teams: tuple[Team, Team]) -> None:
        """Verify sync stores winner='draw' when API returns DRAW."""
        mock_matches_data = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "FINISHED",
                "stage": "GROUP_STAGE",
                "score": {
                    "winner": "DRAW",
                    "fullTime": {"home": 1, "away": 1},
                },
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_matches_data

            results = sync_matches_from_api()

            assert len(results) == 1
            match = results[0].match
            assert match.winner == "draw"

    def test_sync_match_winner_null_for_scheduled(self, teams: tuple[Team, Team]) -> None:
        """Verify winner is None when match is scheduled (no winner field in API)."""
        mock_matches_data = [
            {
                "id": 1001,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "SCHEDULED",
                "stage": "GROUP_STAGE",
                "score": {"fullTime": {"home": None, "away": None}},
            }
        ]

        with patch("matches.services.FootballDataClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_matches_data

            results = sync_matches_from_api()

            assert len(results) == 1
            match = results[0].match
            assert match.winner is None

    def test_sync_continues_after_single_match_failure(self, teams: tuple[Team, Team]) -> None:
        """Verify one failing match does not abort the sync of the remaining matches."""

        def match_payload(external_id: int) -> dict:
            return {
                "id": external_id,
                "homeTeam": {"name": "Germany", "tla": "GER"},
                "awayTeam": {"name": "Brazil", "tla": "BRA"},
                "utcDate": "2026-06-20T18:00:00Z",
                "status": "FINISHED",
                "stage": "GROUP_STAGE",
                "score": {"winner": "HOME_TEAM", "fullTime": {"home": 2, "away": 1}},
            }

        mock_matches_data = [match_payload(1001), match_payload(1002), match_payload(1003)]

        real_sync_match = services._sync_match

        def flaky_sync(match_data: dict):
            if match_data["id"] == 1002:
                raise RuntimeError("scoring boom")
            return real_sync_match(match_data)

        with (
            patch("matches.services.FootballDataClient") as MockClient,
            patch("matches.services._sync_match", side_effect=flaky_sync),
        ):
            mock_client = MockClient.return_value
            mock_client.get_matches.return_value = mock_matches_data

            results = sync_matches_from_api()

        assert len(results) == 2
        assert {r.match.external_id for r in results} == {1001, 1003}
        assert not Match.objects.filter(external_id=1002).exists()
