"""Tests for RankingService."""

import pytest

from scoring.services import RankingService
from users.models import User


@pytest.fixture
def users_with_stats(db) -> list[User]:
    """Create users with various statistics for ranking tests."""
    users = [
        User.objects.create_user(
            username="alice",
            password="test",
            total_points=100,
            exact_match_count=8,
            jokers_used=5,
        ),
        User.objects.create_user(
            username="bob",
            password="test",
            total_points=95,
            exact_match_count=7,
            jokers_used=5,
        ),
        User.objects.create_user(
            username="carol",
            password="test",
            total_points=95,
            exact_match_count=7,
            jokers_used=5,
        ),
        User.objects.create_user(
            username="dave",
            password="test",
            total_points=90,
            exact_match_count=6,
            jokers_used=4,
        ),
        User.objects.create_user(
            username="eve",
            password="test",
            total_points=90,
            exact_match_count=6,
            jokers_used=5,
        ),
    ]
    return users


class TestRankingByPoints:
    """Test basic ranking by total points."""

    def test_ranking_orders_by_points_descending(
        self, db, users_with_stats: list[User]
    ) -> None:
        """Test users are ranked by total points (highest first)."""
        leaderboard = RankingService.get_current_leaderboard()

        assert leaderboard[0]["username"] == "alice"
        assert leaderboard[0]["total_points"] == 100
        assert leaderboard[0]["rank"] == 1


class TestTiebreakers:
    """Test Olympic tiebreaker rules per WM 2026 rules section 10."""

    def test_tiebreaker_exact_matches(self, db) -> None:
        """Test first tiebreaker: exact match count (higher is better)."""
        User.objects.create_user(
            username="more_exact",
            password="test",
            total_points=50,
            exact_match_count=5,
            jokers_used=3,
        )
        User.objects.create_user(
            username="less_exact",
            password="test",
            total_points=50,
            exact_match_count=3,
            jokers_used=3,
        )

        leaderboard = RankingService.get_current_leaderboard()

        # Same points, more exact matches wins
        assert leaderboard[0]["username"] == "more_exact"
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[1]["username"] == "less_exact"
        assert leaderboard[1]["rank"] == 2

    def test_tiebreaker_jokers_used(self, db) -> None:
        """Test second tiebreaker: jokers used (fewer is better)."""
        User.objects.create_user(
            username="fewer_jokers",
            password="test",
            total_points=50,
            exact_match_count=5,
            jokers_used=2,
        )
        User.objects.create_user(
            username="more_jokers",
            password="test",
            total_points=50,
            exact_match_count=5,
            jokers_used=5,
        )

        leaderboard = RankingService.get_current_leaderboard()

        # Same points and exact, fewer jokers wins
        assert leaderboard[0]["username"] == "fewer_jokers"
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[1]["username"] == "more_jokers"
        assert leaderboard[1]["rank"] == 2


class TestSharedRanks:
    """Test shared rank handling."""

    def test_identical_stats_share_rank(
        self, db, users_with_stats: list[User]
    ) -> None:
        """Test users with identical stats share the same rank."""
        leaderboard = RankingService.get_current_leaderboard()

        # bob and carol have identical stats (95 pts, 7 exact, 5 jokers)
        bob = next(e for e in leaderboard if e["username"] == "bob")
        carol = next(e for e in leaderboard if e["username"] == "carol")

        assert bob["rank"] == carol["rank"] == 2

    def test_rank_numbering_with_ties(
        self, db, users_with_stats: list[User]
    ) -> None:
        """Test rank numbering skips after ties (1, 2, 2, 4 not 1, 2, 2, 3)."""
        leaderboard = RankingService.get_current_leaderboard()

        # alice: rank 1 (100 pts)
        # bob, carol: rank 2 (tied at 95 pts)
        # dave: rank 4 (90 pts, 4 jokers - fewer than eve)
        # eve: rank 5 (90 pts, 5 jokers)
        alice = next(e for e in leaderboard if e["username"] == "alice")
        bob = next(e for e in leaderboard if e["username"] == "bob")
        carol = next(e for e in leaderboard if e["username"] == "carol")
        dave = next(e for e in leaderboard if e["username"] == "dave")
        eve = next(e for e in leaderboard if e["username"] == "eve")

        assert alice["rank"] == 1
        assert bob["rank"] == 2
        assert carol["rank"] == 2
        assert dave["rank"] == 4  # Skipped 3 because of tie
        assert eve["rank"] == 5


class TestEdgeCases:
    """Test edge cases in ranking."""

    def test_empty_leaderboard(self, db) -> None:
        """Test empty leaderboard returns empty list."""
        leaderboard = RankingService.get_current_leaderboard()
        assert leaderboard == []

    def test_single_user_leaderboard(self, db) -> None:
        """Test leaderboard with single user."""
        User.objects.create_user(
            username="lonely",
            password="test",
            total_points=50,
            exact_match_count=3,
            jokers_used=2,
        )

        leaderboard = RankingService.get_current_leaderboard()

        assert len(leaderboard) == 1
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[0]["username"] == "lonely"

    def test_inactive_users_excluded(self, db) -> None:
        """Test inactive users are not included in leaderboard."""
        User.objects.create_user(
            username="active",
            password="test",
            total_points=50,
            is_active=True,
        )
        User.objects.create_user(
            username="inactive",
            password="test",
            total_points=100,  # Higher points but inactive
            is_active=False,
        )

        leaderboard = RankingService.get_current_leaderboard()

        assert len(leaderboard) == 1
        assert leaderboard[0]["username"] == "active"
