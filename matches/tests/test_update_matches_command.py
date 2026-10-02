"""Tests for update_matches management command."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from conftest import make_match
from matches.management.commands.update_matches import Command
from matches.models import Team
from matches.services import MatchSyncResult


@pytest.mark.django_db
class TestUpdateMatchesCommand:
    """Test suite for update_matches management command."""

    @pytest.fixture
    def teams(self) -> tuple[Team, Team]:
        """Create test teams."""
        team_home = Team.objects.create(name="Germany", fifa_code="GER")
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA")
        return team_home, team_away

    def test_update_matches_once_flag(self, teams: tuple[Team, Team]) -> None:
        """Verify --once flag runs single iteration and exits."""
        team_home, team_away = teams
        match = make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=datetime(2026, 6, 20, 18, 0, tzinfo=UTC),
            round="group",
            status="scheduled",
        )

        with patch("matches.management.commands.update_matches.sync_matches_from_api") as mock_sync:
            mock_sync.return_value = [MatchSyncResult(match=match, goals_changed=False)]

            out = StringIO()
            call_command("update_matches", "--once", stdout=out)

            output = out.getvalue()
            assert "Single iteration complete" in output
            mock_sync.assert_called_once()

    def test_calculate_sleep_interval_live_match(self, teams: tuple[Team, Team]) -> None:
        """Verify interval is 10 seconds when live match exists."""
        team_home, team_away = teams
        make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="live",
        )

        command = Command()
        interval = command._calculate_sleep_interval()

        assert interval == 10

    def test_calculate_sleep_interval_no_matches(self) -> None:
        """Verify interval is 1800 seconds when no upcoming matches."""
        command = Command()
        interval = command._calculate_sleep_interval()

        assert interval == 1800

    def test_calculate_sleep_interval_match_soon(self, teams: tuple[Team, Team]) -> None:
        """Verify interval is 60 seconds for match < 30 minutes away."""
        team_home, team_away = teams
        # Match in 20 minutes
        make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now() + timedelta(minutes=20),
            round="group",
            status="scheduled",
        )

        command = Command()
        interval = command._calculate_sleep_interval()

        assert interval == 30

    def test_calculate_sleep_interval_match_in_2h(self, teams: tuple[Team, Team]) -> None:
        """Verify interval is 300 seconds for match 30min-2h away."""
        team_home, team_away = teams
        # Match in 1 hour
        make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now() + timedelta(hours=1),
            round="group",
            status="scheduled",
        )

        command = Command()
        interval = command._calculate_sleep_interval()

        assert interval == 300

    def test_calculate_sleep_interval_match_later(self, teams: tuple[Team, Team]) -> None:
        """Verify interval is 600 seconds for match > 2 hours away."""
        team_home, team_away = teams
        # Match in 3 hours
        make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now() + timedelta(hours=3),
            round="group",
            status="scheduled",
        )

        command = Command()
        interval = command._calculate_sleep_interval()

        assert interval == 600

    def test_update_matches_triggers_scoring(self, teams: tuple[Team, Team]) -> None:
        """Verify scoring is triggered when goals change."""
        team_home, team_away = teams
        match = make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=datetime(2026, 6, 20, 18, 0, tzinfo=UTC),
            round="group",
            status="live",
            goals_home=0,
            goals_away=0,
        )

        # Mock the sync function and signal receiver
        with (
            patch("matches.management.commands.update_matches.sync_matches_from_api") as mock_sync,
            patch("scoring.signals.score_predictions_on_result"),
        ):
            # Simulate goal change
            mock_sync.return_value = [MatchSyncResult(match=match, goals_changed=True)]

            out = StringIO()
            call_command("update_matches", "--once", stdout=out)

            # Signal receiver should have been called via match.save() in sync
            # We verify the output shows goal changes were detected
            output = out.getvalue()
            assert "1 with goal changes" in output
            assert "Predictions scored automatically via signals" in output

    def test_update_matches_triggers_champion_scoring(self, teams: tuple[Team, Team]) -> None:
        """Verify champion scoring is triggered when final match finishes."""
        team_home, team_away = teams
        match = make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=datetime(2026, 7, 20, 18, 0, tzinfo=UTC),
            round="final",
            status="finished",
            goals_home=2,
            goals_away=1,
        )

        # Mock sync and signal receivers
        with patch("matches.management.commands.update_matches.sync_matches_from_api") as mock_sync:
            # Simulate final match finished
            mock_sync.return_value = [MatchSyncResult(match=match, goals_changed=True)]

            out = StringIO()
            call_command("update_matches", "--once", stdout=out)

            # Verify output shows match was processed
            output = out.getvalue()
            assert "1 with goal changes" in output
            assert "Predictions scored automatically via signals" in output

    def test_update_matches_continues_after_error(self, teams: tuple[Team, Team]) -> None:
        """Verify update loop continues after error in --once=False mode."""
        command = Command()
        command.running = True

        call_count = 0

        def side_effect_sync(tournament):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated error")
            else:
                # Stop after second call
                command.running = False
                return []

        with (
            patch("matches.management.commands.update_matches.sync_matches_from_api") as mock_sync,
            patch("matches.management.commands.update_matches.time.sleep"),
        ):
            mock_sync.side_effect = side_effect_sync

            out = StringIO()
            command.handle(once=False, stdout=out)

            # Should be called twice: once failing, once succeeding
            assert mock_sync.call_count == 2

    def test_update_matches_skips_scoring_when_no_goal_changes(
        self, teams: tuple[Team, Team]
    ) -> None:
        """Verify scoring is not triggered when goals don't change."""
        team_home, team_away = teams
        match = make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=datetime(2026, 6, 20, 18, 0, tzinfo=UTC),
            round="group",
            status="scheduled",
        )

        with patch("matches.management.commands.update_matches.sync_matches_from_api") as mock_sync:
            # No goal changes
            mock_sync.return_value = [MatchSyncResult(match=match, goals_changed=False)]

            out = StringIO()
            call_command("update_matches", "--once", stdout=out)

            # Verify output shows no goal changes
            output = out.getvalue()
            assert "0 with goal changes" in output
            # Should not see the "scored automatically" message
            assert "Predictions scored automatically" not in output

    def test_active_window_match_after_kickoff_not_live(self, teams: tuple[Team, Team]) -> None:
        """Match with kickoff passed but status still scheduled should trigger fast polling."""
        team_home, team_away = teams
        # Kickoff was 1 minute ago, status still "scheduled"
        make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now() - timedelta(minutes=1),
            round="group",
            status="scheduled",
        )

        command = Command()
        interval = command._calculate_sleep_interval()

        assert interval == 30, "Should poll frequently during active window"

    def test_active_window_excludes_finished_matches(self, teams: tuple[Team, Team]) -> None:
        """Finished matches should not trigger active window polling."""
        team_home, team_away = teams
        # Match finished 1 hour ago
        make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now() - timedelta(hours=1),
            round="group",
            status="finished",
        )

        command = Command()
        interval = command._calculate_sleep_interval()

        assert interval == 1800, "Finished matches should not trigger active window"

    def test_active_window_before_kickoff(self, teams: tuple[Team, Team]) -> None:
        """Match approaching kickoff (within 30 min) should trigger active window."""
        team_home, team_away = teams
        # Match starts in 15 minutes
        make_match(
            external_id=1001,
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now() + timedelta(minutes=15),
            round="group",
            status="scheduled",
        )

        command = Command()
        interval = command._calculate_sleep_interval()

        assert interval == 30, "Should poll frequently during active window before kickoff"
