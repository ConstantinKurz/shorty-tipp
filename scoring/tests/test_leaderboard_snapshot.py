"""Tests for LeaderboardSnapshot model and creation."""

import pytest

from scoring.models import LeaderboardSnapshot
from scoring.services import RankingService
from users.models import User


@pytest.fixture
def users_for_snapshot(db) -> list[User]:
    """Create users for snapshot tests."""
    return [
        User.objects.create_user(
            username="leader",
            password="test",
            total_points=100,
            exact_match_count=5,
            jokers_used=2,
        ),
        User.objects.create_user(
            username="runner_up",
            password="test",
            total_points=80,
            exact_match_count=4,
            jokers_used=3,
        ),
    ]


class TestSnapshotCreation:
    """Test LeaderboardSnapshot creation."""

    def test_create_snapshot(self, db, users_for_snapshot: list[User]) -> None:
        """Test snapshot is created with current leaderboard data."""
        snapshot = RankingService.create_snapshot("daily")

        assert snapshot.pk is not None
        assert snapshot.snapshot_type == "daily"
        assert len(snapshot.data) == 2

    def test_snapshot_data_structure(
        self, db, users_for_snapshot: list[User]
    ) -> None:
        """Test snapshot data contains expected fields."""
        snapshot = RankingService.create_snapshot("daily")

        entry = snapshot.data[0]
        assert "rank" in entry
        assert "user_id" in entry
        assert "username" in entry
        assert "total_points" in entry
        assert "exact_match_count" in entry
        assert "jokers_used" in entry

    def test_snapshot_captures_rankings_correctly(
        self, db, users_for_snapshot: list[User]
    ) -> None:
        """Test snapshot captures correct ranking order."""
        snapshot = RankingService.create_snapshot("final")

        assert snapshot.data[0]["username"] == "leader"
        assert snapshot.data[0]["rank"] == 1
        assert snapshot.data[1]["username"] == "runner_up"
        assert snapshot.data[1]["rank"] == 2


class TestSnapshotImmutability:
    """Test that snapshots are immutable historical records."""

    def test_snapshot_preserves_data_after_stats_change(
        self, db, users_for_snapshot: list[User]
    ) -> None:
        """Test snapshot data doesn't change when user stats change."""
        snapshot = RankingService.create_snapshot("daily")
        original_points = snapshot.data[0]["total_points"]

        # Change user stats
        leader = User.objects.get(username="leader")
        leader.total_points = 200
        leader.save()

        # Refresh snapshot from DB
        snapshot.refresh_from_db()

        # Snapshot should retain original value
        assert snapshot.data[0]["total_points"] == original_points


class TestSnapshotQuerying:
    """Test querying snapshots."""

    def test_query_by_type(self, db, users_for_snapshot: list[User]) -> None:
        """Test filtering snapshots by type."""
        RankingService.create_snapshot("daily")
        RankingService.create_snapshot("daily")
        RankingService.create_snapshot("final")

        daily_snapshots = LeaderboardSnapshot.objects.filter(snapshot_type="daily")
        final_snapshots = LeaderboardSnapshot.objects.filter(snapshot_type="final")

        assert daily_snapshots.count() == 2
        assert final_snapshots.count() == 1

    def test_ordering_by_date(self, db, users_for_snapshot: list[User]) -> None:
        """Test snapshots are ordered by created_at descending."""
        snap1 = RankingService.create_snapshot("daily")
        snap2 = RankingService.create_snapshot("daily")
        snap3 = RankingService.create_snapshot("daily")

        snapshots = list(LeaderboardSnapshot.objects.all())

        # Most recent first
        assert snapshots[0].pk == snap3.pk
        assert snapshots[1].pk == snap2.pk
        assert snapshots[2].pk == snap1.pk


class TestSnapshotTypes:
    """Test different snapshot types."""

    def test_daily_snapshot(self, db, users_for_snapshot: list[User]) -> None:
        """Test creating daily snapshot."""
        snapshot = RankingService.create_snapshot("daily")
        assert snapshot.snapshot_type == "daily"

    def test_final_snapshot(self, db, users_for_snapshot: list[User]) -> None:
        """Test creating final snapshot."""
        snapshot = RankingService.create_snapshot("final")
        assert snapshot.snapshot_type == "final"


class TestSnapshotStrMethod:
    """Test LeaderboardSnapshot string representation."""

    def test_str_method(self, db, users_for_snapshot: list[User]) -> None:
        """Test __str__ returns readable description."""
        snapshot = RankingService.create_snapshot("daily")
        str_repr = str(snapshot)

        assert "Daily" in str_repr
        assert "snapshot" in str_repr
