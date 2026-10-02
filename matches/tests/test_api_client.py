"""Tests for Football-Data.org API client."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from matches.api_client import FootballDataAPIError, FootballDataClient


class TestFootballDataClient:
    """Test suite for FootballDataClient."""

    @pytest.fixture
    def client(self) -> FootballDataClient:
        """Create a test client instance."""
        return FootballDataClient(api_key="test-api-key", base_url="https://api.test.com/v4")

    def test_api_client_sends_auth_header(self, client: FootballDataClient) -> None:
        """Verify that API client includes X-Auth-Token header in requests."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"teams": []}
            mock_get.return_value = mock_response

            client.get_teams("WC")

            mock_get.assert_called_once()
            assert client.session.headers["X-Auth-Token"] == "test-api-key"

    def test_api_client_retries_on_429(self, client: FootballDataClient) -> None:
        """Verify that API client retries on 429 rate limit response."""
        with patch.object(client.session, "get") as mock_get:
            # First call returns 429, second succeeds
            mock_429 = Mock()
            mock_429.status_code = 429
            mock_429.headers = {"Retry-After": "1"}

            mock_200 = Mock()
            mock_200.status_code = 200
            mock_200.json.return_value = {"teams": []}

            mock_get.side_effect = [mock_429, mock_200]

            result = client.get_teams("WC")

            assert mock_get.call_count == 2
            assert result == []

    def test_api_client_retries_on_500(self, client: FootballDataClient) -> None:
        """Verify that API client retries on 5xx server errors with exponential backoff."""
        with patch.object(client.session, "get") as mock_get:
            # First call returns 500, second succeeds
            mock_500 = Mock()
            mock_500.status_code = 500

            mock_200 = Mock()
            mock_200.status_code = 200
            mock_200.json.return_value = {"matches": []}

            mock_get.side_effect = [mock_500, mock_200]

            result = client.get_matches("WC")

            assert mock_get.call_count == 2
            assert result == []

    def test_api_client_respects_retry_after_header(self, client: FootballDataClient) -> None:
        """Verify that API client waits for Retry-After duration on 429."""
        with (
            patch.object(client.session, "get") as mock_get,
            patch("matches.api_client.time.sleep") as mock_sleep,
        ):
            mock_429 = Mock()
            mock_429.status_code = 429
            mock_429.headers = {"Retry-After": "42"}

            mock_200 = Mock()
            mock_200.status_code = 200
            mock_200.json.return_value = {"teams": []}

            mock_get.side_effect = [mock_429, mock_200]

            client.get_teams("WC")

            # Verify sleep was called with Retry-After value
            mock_sleep.assert_called_once_with(42)

    def test_api_client_raises_after_max_retries(self, client: FootballDataClient) -> None:
        """Verify that API client raises exception after max retries are exhausted."""
        with patch.object(client.session, "get") as mock_get:
            # All attempts return 500
            mock_500 = Mock()
            mock_500.status_code = 500
            mock_get.return_value = mock_500

            with pytest.raises(FootballDataAPIError, match="failed after 3 attempts"):
                client.get_teams("WC")

            assert mock_get.call_count == 3

    def test_api_client_handles_network_error(self, client: FootballDataClient) -> None:
        """Verify that API client handles network errors with retries."""
        with patch.object(client.session, "get") as mock_get:
            # First call raises network error, second succeeds
            mock_get.side_effect = [
                requests.exceptions.ConnectionError("Network error"),
                Mock(status_code=200, json=lambda: {"teams": []}),
            ]

            result = client.get_teams("WC")

            assert mock_get.call_count == 2
            assert result == []

    def test_get_teams_returns_team_list(self, client: FootballDataClient) -> None:
        """Verify that get_teams returns list of teams from API response."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "teams": [
                    {"id": 1, "name": "Germany", "tla": "GER"},
                    {"id": 2, "name": "Brazil", "tla": "BRA"},
                ]
            }
            mock_get.return_value = mock_response

            teams = client.get_teams("WC")

            assert len(teams) == 2
            assert teams[0]["name"] == "Germany"
            assert teams[1]["name"] == "Brazil"

    def test_get_matches_returns_match_list(self, client: FootballDataClient) -> None:
        """Verify that get_matches returns list of matches from API response."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "matches": [
                    {"id": 1, "homeTeam": {"name": "Germany"}, "awayTeam": {"name": "Brazil"}},
                ]
            }
            mock_get.return_value = mock_response

            matches = client.get_matches("WC")

            assert len(matches) == 1
            assert matches[0]["homeTeam"]["name"] == "Germany"
