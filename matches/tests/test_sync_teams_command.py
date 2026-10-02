"""Tests for sync_teams management command."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from matches.api_client import FootballDataAPIError
from matches.tournament import create_tournament


@pytest.mark.django_db
class TestSyncTeamsCommand:
    """Test suite for sync_teams management command."""

    def test_sync_teams_command_runs(self) -> None:
        """Verify sync_teams command executes successfully."""
        with patch("matches.management.commands.sync_teams.sync_teams_from_api") as mock_sync:
            mock_sync.return_value = (5, 3, 1)  # 5 created, 3 updated, 1 unchanged

            out = StringIO()
            call_command("sync_teams", stdout=out)

            output = out.getvalue()
            assert "Syncing teams" in output
            assert "5 created" in output
            assert "3 updated" in output
            assert "1 unchanged" in output
            assert mock_sync.call_args.args[0].slug == "wm-2026"

    def test_sync_teams_command_output(self) -> None:
        """Verify sync_teams command outputs created and updated counts."""
        with patch("matches.management.commands.sync_teams.sync_teams_from_api") as mock_sync:
            mock_sync.return_value = (10, 0, 0)

            out = StringIO()
            call_command("sync_teams", stdout=out)

            output = out.getvalue()
            assert "10 created" in output
            assert "0 updated" in output

    def test_sync_teams_command_accepts_tournament_option(self) -> None:
        """Verify sync_teams command syncs the named tournament."""
        create_tournament(name="EM 2028", slug="em-2028", api_competition_code="EC", preset="em24")

        with patch("matches.management.commands.sync_teams.sync_teams_from_api") as mock_sync:
            mock_sync.return_value = (2, 1, 0)

            out = StringIO()
            call_command("sync_teams", "--tournament=em-2028", stdout=out)

            output = out.getvalue()
            assert "EC" in output
            assert mock_sync.call_args.args[0].slug == "em-2028"

    def test_sync_teams_command_unknown_tournament(self) -> None:
        """An unknown slug fails instead of silently syncing something else."""
        with pytest.raises(CommandError, match="No tournament with slug"):
            call_command("sync_teams", "--tournament=does-not-exist")

    def test_sync_teams_command_handles_api_error(self) -> None:
        """Verify sync_teams command handles API errors gracefully."""
        with patch("matches.management.commands.sync_teams.sync_teams_from_api") as mock_sync:
            mock_sync.side_effect = FootballDataAPIError("API unavailable")

            with pytest.raises(CommandError, match="API error"):
                call_command("sync_teams")

    def test_sync_teams_command_defaults_to_active_tournament(self) -> None:
        """Verify sync_teams command uses the active tournament by default."""
        with patch("matches.management.commands.sync_teams.sync_teams_from_api") as mock_sync:
            mock_sync.return_value = (0, 0, 0)

            call_command("sync_teams")

            assert mock_sync.call_args.args[0].slug == "wm-2026"
