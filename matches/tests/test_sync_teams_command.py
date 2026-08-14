"""Tests for sync_teams management command."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from matches.api_client import FootballDataAPIError


@pytest.mark.django_db
class TestSyncTeamsCommand:
    """Test suite for sync_teams management command."""

    def test_sync_teams_command_runs(self) -> None:
        """Verify sync_teams command executes successfully."""
        with patch("matches.management.commands.sync_teams.sync_teams_from_api") as mock_sync:
            mock_sync.return_value = (5, 3)  # 5 created, 3 updated

            out = StringIO()
            call_command("sync_teams", stdout=out)

            output = out.getvalue()
            assert "Syncing teams" in output
            assert "5 created" in output
            assert "3 updated" in output
            mock_sync.assert_called_once_with("WC")

    def test_sync_teams_command_output(self) -> None:
        """Verify sync_teams command outputs created and updated counts."""
        with patch("matches.management.commands.sync_teams.sync_teams_from_api") as mock_sync:
            mock_sync.return_value = (10, 0)

            out = StringIO()
            call_command("sync_teams", stdout=out)

            output = out.getvalue()
            assert "10 created" in output
            assert "0 updated" in output

    def test_sync_teams_command_competition_option(self) -> None:
        """Verify sync_teams command accepts --competition option."""
        with patch("matches.management.commands.sync_teams.sync_teams_from_api") as mock_sync:
            mock_sync.return_value = (2, 1)

            out = StringIO()
            call_command("sync_teams", "--competition=EURO", stdout=out)

            output = out.getvalue()
            assert "EURO" in output
            mock_sync.assert_called_once_with("EURO")

    def test_sync_teams_command_handles_api_error(self) -> None:
        """Verify sync_teams command handles API errors gracefully."""
        with patch("matches.management.commands.sync_teams.sync_teams_from_api") as mock_sync:
            mock_sync.side_effect = FootballDataAPIError("API unavailable")

            with pytest.raises(CommandError, match="API error"):
                call_command("sync_teams")

    def test_sync_teams_command_default_competition(self) -> None:
        """Verify sync_teams command uses WC as default competition."""
        with patch("matches.management.commands.sync_teams.sync_teams_from_api") as mock_sync:
            mock_sync.return_value = (0, 0)

            call_command("sync_teams")

            mock_sync.assert_called_once_with("WC")
