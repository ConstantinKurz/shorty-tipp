"""Tests for shared ranking utilities."""

from core.ranking import apply_olympic_ranking, create_tiebreaker_from_keys


class TestApplyOlympicRanking:
    """Test Olympic-style ranking application."""

    def test_simple_ranking_no_ties(self):
        """Test ranking with no tied positions."""
        items = [
            {"user": "alice", "points": 100},
            {"user": "bob", "points": 90},
            {"user": "carol", "points": 80},
        ]

        def tiebreaker(a, b):
            return a["points"] == b["points"]

        result = apply_olympic_ranking(items, tiebreaker)

        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
        assert result[2]["rank"] == 3

    def test_ranking_with_ties(self):
        """Test Olympic ranking with tied positions (1, 2, 2, 4)."""
        items = [
            {"user": "alice", "points": 100},
            {"user": "bob", "points": 90},
            {"user": "carol", "points": 90},
            {"user": "dave", "points": 80},
        ]

        def tiebreaker(a, b):
            return a["points"] == b["points"]

        result = apply_olympic_ranking(items, tiebreaker)

        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
        assert result[2]["rank"] == 2
        assert result[3]["rank"] == 4

    def test_ranking_multiple_ties(self):
        """Test ranking with multiple tied groups."""
        items = [
            {"user": "alice", "points": 100},
            {"user": "bob", "points": 90},
            {"user": "carol", "points": 90},
            {"user": "dave", "points": 80},
            {"user": "eve", "points": 80},
            {"user": "frank", "points": 70},
        ]

        def tiebreaker(a, b):
            return a["points"] == b["points"]

        result = apply_olympic_ranking(items, tiebreaker)

        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
        assert result[2]["rank"] == 2
        assert result[3]["rank"] == 4
        assert result[4]["rank"] == 4
        assert result[5]["rank"] == 6

    def test_ranking_all_tied(self):
        """Test ranking when all items share the same rank."""
        items = [
            {"user": "alice", "points": 100},
            {"user": "bob", "points": 100},
            {"user": "carol", "points": 100},
        ]

        def tiebreaker(a, b):
            return a["points"] == b["points"]

        result = apply_olympic_ranking(items, tiebreaker)

        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 1
        assert result[2]["rank"] == 1

    def test_ranking_empty_list(self):
        """Test ranking with empty list."""
        items = []

        def tiebreaker(a, b):
            return True

        result = apply_olympic_ranking(items, tiebreaker)

        assert result == []

    def test_ranking_single_item(self):
        """Test ranking with single item."""
        items = [{"user": "alice", "points": 100}]

        def tiebreaker(a, b):
            return a["points"] == b["points"]

        result = apply_olympic_ranking(items, tiebreaker)

        assert len(result) == 1
        assert result[0]["rank"] == 1

    def test_custom_rank_key(self):
        """Test using custom rank key name."""
        items = [
            {"user": "alice", "points": 100},
            {"user": "bob", "points": 90},
        ]

        def tiebreaker(a, b):
            return a["points"] == b["points"]

        result = apply_olympic_ranking(items, tiebreaker, rank_key="position")

        assert result[0]["position"] == 1
        assert result[1]["position"] == 2
        assert "rank" not in result[0]

    def test_multi_field_tiebreaker(self):
        """Test tiebreaker using multiple fields."""
        items = [
            {"user": "alice", "points": 100, "exact": 5},
            {"user": "bob", "points": 100, "exact": 4},
            {"user": "carol", "points": 100, "exact": 4},
            {"user": "dave", "points": 90, "exact": 5},
        ]

        def tiebreaker(a, b):
            return a["points"] == b["points"] and a["exact"] == b["exact"]

        result = apply_olympic_ranking(items, tiebreaker)

        assert result[0]["rank"] == 1  # alice: 100 points, 5 exact
        assert result[1]["rank"] == 2  # bob: 100 points, 4 exact
        assert result[2]["rank"] == 2  # carol: 100 points, 4 exact (tied with bob)
        assert result[3]["rank"] == 4  # dave: 90 points


class TestCreateTiebreakerFromKeys:
    """Test tiebreaker function factory."""

    def test_single_key(self):
        """Test tiebreaker with single key."""
        tiebreaker = create_tiebreaker_from_keys("points")

        assert tiebreaker({"points": 100}, {"points": 100}) is True
        assert tiebreaker({"points": 100}, {"points": 90}) is False

    def test_multiple_keys(self):
        """Test tiebreaker with multiple keys."""
        tiebreaker = create_tiebreaker_from_keys("points", "exact", "jokers")

        # All match
        assert (
            tiebreaker(
                {"points": 100, "exact": 5, "jokers": 2},
                {"points": 100, "exact": 5, "jokers": 2},
            )
            is True
        )

        # One differs
        assert (
            tiebreaker(
                {"points": 100, "exact": 5, "jokers": 2},
                {"points": 100, "exact": 4, "jokers": 2},
            )
            is False
        )

        # All differ
        assert (
            tiebreaker(
                {"points": 100, "exact": 5, "jokers": 2},
                {"points": 90, "exact": 4, "jokers": 1},
            )
            is False
        )

    def test_missing_keys(self):
        """Test tiebreaker with missing keys (should handle gracefully)."""
        tiebreaker = create_tiebreaker_from_keys("points", "exact")

        # Both missing same key
        assert tiebreaker({"points": 100}, {"points": 100}) is True

        # One has key, other doesn't
        assert tiebreaker({"points": 100, "exact": 5}, {"points": 100}) is False


class TestIntegrationWithRealData:
    """Integration tests mimicking real tipapp usage."""

    def test_tipapp_leaderboard_ranking(self):
        """Test ranking similar to tipapp leaderboard."""
        users = [
            {"username": "alice", "total_points": 100, "exact_count": 10, "jokers_count": 2},
            {"username": "bob", "total_points": 100, "exact_count": 10, "jokers_count": 2},
            {"username": "carol", "total_points": 95, "exact_count": 9, "jokers_count": 2},
            {"username": "dave", "total_points": 95, "exact_count": 8, "jokers_count": 1},
        ]

        tiebreaker = create_tiebreaker_from_keys("total_points", "exact_count", "jokers_count")
        result = apply_olympic_ranking(users, tiebreaker)

        assert result[0]["rank"] == 1  # alice
        assert result[1]["rank"] == 1  # bob (tied with alice)
        assert result[2]["rank"] == 3  # carol
        assert result[3]["rank"] == 4  # dave
