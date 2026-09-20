"""
Football-Data.org API Client.

Provides HTTP client for fetching team and match data from football-data.org v4 API.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class FootballDataAPIError(Exception):
    """Base exception for Football-Data API errors."""

    pass


class FootballDataRateLimitError(FootballDataAPIError):
    """Raised when API rate limit is exceeded."""

    pass


class FootballDataClient:
    """
    HTTP client for football-data.org v4 API.

    Handles authentication, rate limiting compliance, and retry logic.
    Free tier allows 10 requests per minute.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        """
        Initialize the Football-Data API client.

        Args:
            api_key: API authentication token. If None, reads from settings.FOOTBALL_DATA_API_KEY
            base_url: API base URL. If None, reads from settings.FOOTBALL_DATA_BASE_URL
        """
        self.api_key = api_key or settings.FOOTBALL_DATA_API_KEY
        self.base_url = base_url or settings.FOOTBALL_DATA_BASE_URL
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Auth-Token": self.api_key,
            }
        )
        # Disable proxies - direct connection required for football-data.org
        self.session.proxies = {}

    def get_teams(self, competition: str = "WC") -> list[dict[str, Any]]:
        """
        Fetch all teams for a competition.

        Args:
            competition: Competition code (default: WC for World Cup)

        Returns:
            List of team data dictionaries from API

        Raises:
            FootballDataAPIError: If API request fails after retries
        """
        url = f"{self.base_url}/competitions/{competition}/teams"
        response_data = self._make_request(url)
        return response_data.get("teams", [])

    def get_matches(self, competition: str = "WC") -> list[dict[str, Any]]:
        """
        Fetch all matches for a competition.

        Args:
            competition: Competition code (default: WC for World Cup)

        Returns:
            List of match data dictionaries from API

        Raises:
            FootballDataAPIError: If API request fails after retries
        """
        url = f"{self.base_url}/competitions/{competition}/matches"
        response_data = self._make_request(url)
        return response_data.get("matches", [])

    def _make_request(self, url: str, max_retries: int = 3) -> dict[str, Any]:
        """
        Make HTTP GET request with retry logic.

        Implements exponential backoff for 5xx errors and respects
        Retry-After header for 429 rate limit responses.

        Args:
            url: Full URL to request
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            Parsed JSON response data

        Raises:
            FootballDataAPIError: If request fails after max retries
            FootballDataRateLimitError: If rate limit exceeded after retries
        """
        attempt = 0
        backoff_seconds = 1

        while attempt < max_retries:
            try:
                response = self.session.get(url, timeout=10)

                # Success
                if response.status_code == 200:
                    return response.json()

                # Rate limit - respect Retry-After header
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        "Rate limit exceeded. Retrying after %d seconds (attempt %d/%d)",
                        retry_after,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(retry_after)
                    attempt += 1
                    continue

                # Server errors - exponential backoff
                if 500 <= response.status_code < 600:
                    logger.warning(
                        "Server error %d. Retrying in %d seconds (attempt %d/%d)",
                        response.status_code,
                        backoff_seconds,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2  # Exponential backoff
                    attempt += 1
                    continue

                # Client errors - don't retry
                response.raise_for_status()

            except requests.exceptions.RequestException as e:
                logger.error("Network error on attempt %d/%d: %s", attempt + 1, max_retries, e)
                if attempt + 1 >= max_retries:
                    raise FootballDataAPIError(
                        f"Request failed after {max_retries} attempts"
                    ) from e
                time.sleep(backoff_seconds)
                backoff_seconds *= 2
                attempt += 1
                continue

        # Max retries exceeded
        raise FootballDataAPIError(f"Request to {url} failed after {max_retries} attempts")
