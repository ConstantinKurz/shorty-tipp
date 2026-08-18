"""Tests for champion change signal handler."""

from unittest.mock import patch

import pytest

from matches.models import Team
from scoring.ranking_service import RankingService
from users.models import User


@pytest.fixture
def teams(db) -> dict[str, Team]:
    """Create test teams."""
    return {
        "germany": Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        ),
        "brazil": Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B", is_champion=True
        ),
    }


@pytest.fixture
def user_without_champion(db) -> User:
    """Create a test user without a champion prediction."""
    return User.objects.create_user(
        username="testuser",
        password="test",
        total_points=50,
        exact_match_count=3,
        jokers_used=1,
    )


class TestChampionChangeSignal:
    """Test signal handler for champion prediction changes."""

    def test_champion_change_triggers_recalculation(
        self, db, teams: dict[str, Team], user_without_champion: User
    ) -> None:
        """Test that changing predicted_champion triggers recalculation."""
        user = user_without_champion

        with patch.object(RankingService, "recalculate_user_score") as mock_recalc:
            user.predicted_champion = teams["germany"]
            user.save()

            mock_recalc.assert_called_once_with(user)

    def test_champion_change_on_creation_does_not_trigger_signal(
        self, db, teams: dict[str, Team]
    ) -> None:
        """Test signal doesn't fire when creating new user with champion."""
        with patch.object(RankingService, "recalculate_user_score") as mock_recalc:
            User.objects.create_user(
                username="newuser",
                password="test",
                predicted_champion=teams["germany"],
            )

            mock_recalc.assert_not_called()

    def test_no_change_does_not_trigger_signal(
        self, db, teams: dict[str, Team], user_without_champion: User
    ) -> None:
        """Test signal doesn't fire when champion remains unchanged."""
        user = user_without_champion
        user.predicted_champion = teams["germany"]
        user.save()

        with patch.object(RankingService, "recalculate_user_score") as mock_recalc:
            # Save without changing champion
            user.total_points = 100
            user.save()

            mock_recalc.assert_not_called()

    def test_champion_clear_triggers_recalculation(
        self, db, teams: dict[str, Team], user_without_champion: User
    ) -> None:
        """Test clearing predicted_champion triggers recalculation."""
        user = user_without_champion
        user.predicted_champion = teams["germany"]
        user.save()

        with patch.object(RankingService, "recalculate_user_score") as mock_recalc:
            user.predicted_champion = None
            user.save()

            mock_recalc.assert_called_once_with(user)

    def test_champion_switch_triggers_recalculation(
        self, db, teams: dict[str, Team], user_without_champion: User
    ) -> None:
        """Test switching champion from one team to another triggers recalculation."""
        user = user_without_champion
        user.predicted_champion = teams["germany"]
        user.save()

        with patch.object(RankingService, "recalculate_user_score") as mock_recalc:
            user.predicted_champion = teams["brazil"]
            user.save()

            mock_recalc.assert_called_once_with(user)


class TestChampionRecalculationIntegration:
    """Integration tests for champion prediction recalculation."""

    def test_recalculation_resets_to_prediction_points_only(
        self, db, teams: dict[str, Team], user_without_champion: User
    ) -> None:
        """Test that recalculation resets to match prediction points only.
        
        Champion bonus is handled separately by update_live_champion_bonuses,
        so recalculate_user_score should not include it.
        """
        user = user_without_champion

        # Set champion to the actual champion team (brazil is_champion=True)
        user.predicted_champion = teams["brazil"]
        user.save()

        user.refresh_from_db()
        # Points should be recalculated from predictions only (0 predictions = 0 points)
        # Champion bonus is NOT included - it's added separately via update_live_champion_bonuses
        assert user.total_points == 0

    def test_recalculation_no_bonus_for_wrong_champion(
        self, db, teams: dict[str, Team], user_without_champion: User
    ) -> None:
        """Test that recalculation doesn't add bonus for incorrect prediction."""
        user = user_without_champion

        # Set champion to a non-champion team (germany is not the champion)
        user.predicted_champion = teams["germany"]
        user.save()

        user.refresh_from_db()
        # Points should be recalculated but no champion bonus (germany is not champion)
        assert user.total_points == 0  # No predictions, no champion bonus
