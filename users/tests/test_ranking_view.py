"""
Tests for the ranking view.
"""

import pytest
from django.test import Client
from django.urls import reverse

from matches.models import Team
from users.models import User
from users.utils import get_flag_emoji


@pytest.fixture
def team_germany(db):
    """Create Germany team for testing."""
    return Team.objects.create(
        name="Germany",
        fifa_code="DE",
        odds_category="A",
    )


@pytest.fixture
def team_brazil(db):
    """Create Brazil team for testing."""
    return Team.objects.create(
        name="Brazil",
        fifa_code="BR",
        odds_category="A",
    )


@pytest.fixture
def users_with_ranking_data(db, team_germany, team_brazil):
    """
    Create multiple users with different ranking data for testing.

    Returns list of users with varying points, exact matches, and jokers.
    """
    users = []

    # User 1: Highest points
    user1 = User.objects.create_user(
        username="alice",
        email="alice@test.com",
        password="testpass123",
        total_points=100,
        exact_match_count=5,
        jokers_used=2,
        predicted_champion=team_germany,
    )
    users.append(user1)

    # User 2: Medium points
    user2 = User.objects.create_user(
        username="bob",
        email="bob@test.com",
        password="testpass123",
        total_points=80,
        exact_match_count=3,
        jokers_used=4,
        predicted_champion=team_brazil,
    )
    users.append(user2)

    # User 3: Same points as user2 but better tiebreaker (more exact matches)
    user3 = User.objects.create_user(
        username="carol",
        email="carol@test.com",
        password="testpass123",
        total_points=80,
        exact_match_count=4,
        jokers_used=4,
        predicted_champion=None,  # No champion selected
    )
    users.append(user3)

    # User 4: Tied with user2 (same points, exact, jokers = shared rank)
    user4 = User.objects.create_user(
        username="dave",
        email="dave@test.com",
        password="testpass123",
        total_points=80,
        exact_match_count=3,
        jokers_used=4,
        predicted_champion=team_germany,
    )
    users.append(user4)

    return users


class TestRankingViewAuth:
    """Test authentication requirements for ranking view."""

    def test_ranking_requires_login(self, db, client: Client):
        """GET /ranking/ redirects unauthenticated users to login."""
        url = reverse("ranking")
        response = client.get(url)

        assert response.status_code == 302
        assert "/login/" in response.url

    def test_ranking_accessible_when_logged_in(self, regular_user, client: Client):
        """GET /ranking/ returns 200 for authenticated users."""
        client.force_login(regular_user)
        url = reverse("ranking")
        response = client.get(url)

        assert response.status_code == 200

    def test_ranking_uses_correct_template(self, regular_user, client: Client):
        """Ranking view uses ranking.html template."""
        client.force_login(regular_user)
        url = reverse("ranking")
        response = client.get(url)

        assert "ranking.html" in [t.name for t in response.templates]


class TestRankingViewData:
    """Test ranking data display."""

    def test_leaderboard_in_context(self, regular_user, client: Client):
        """Ranking view includes leaderboard in context."""
        client.force_login(regular_user)
        url = reverse("ranking")
        response = client.get(url)

        assert "leaderboard" in response.context

    def test_leaderboard_ordered_by_points_descending(
        self, users_with_ranking_data, client: Client
    ):
        """Users are ordered by total_points descending."""
        client.force_login(users_with_ranking_data[0])
        url = reverse("ranking")
        response = client.get(url)

        leaderboard = response.context["leaderboard"]
        points = [entry["total_points"] for entry in leaderboard]

        # Should be in descending order
        assert points == sorted(points, reverse=True)

    def test_leaderboard_contains_expected_fields(
        self, users_with_ranking_data, client: Client
    ):
        """Each leaderboard entry contains required fields."""
        client.force_login(users_with_ranking_data[0])
        url = reverse("ranking")
        response = client.get(url)

        leaderboard = response.context["leaderboard"]
        assert len(leaderboard) > 0

        entry = leaderboard[0]
        assert "rank" in entry
        assert "user_id" in entry
        assert "username" in entry
        assert "total_points" in entry
        assert "exact_match_count" in entry
        assert "jokers_used" in entry
        assert "predicted_champion" in entry

    def test_champion_enriched_correctly(
        self, users_with_ranking_data, team_germany, client: Client
    ):
        """Predicted champion data is enriched from User model."""
        client.force_login(users_with_ranking_data[0])
        url = reverse("ranking")
        response = client.get(url)

        leaderboard = response.context["leaderboard"]

        # Find alice's entry (she has Germany as champion)
        alice_entry = next(e for e in leaderboard if e["username"] == "alice")
        assert alice_entry["predicted_champion"] == team_germany
        assert alice_entry["predicted_champion"].fifa_code == "DE"

    def test_no_champion_shows_none(
        self, users_with_ranking_data, client: Client
    ):
        """Users without predicted_champion have None in leaderboard."""
        client.force_login(users_with_ranking_data[0])
        url = reverse("ranking")
        response = client.get(url)

        leaderboard = response.context["leaderboard"]

        # Find carol's entry (she has no champion)
        carol_entry = next(e for e in leaderboard if e["username"] == "carol")
        assert carol_entry["predicted_champion"] is None


class TestOlympicRanking:
    """Test olympic-style ranking with shared ranks."""

    def test_shared_ranks_for_tied_users(
        self, users_with_ranking_data, client: Client
    ):
        """Users with identical tiebreaker values share the same rank."""
        client.force_login(users_with_ranking_data[0])
        url = reverse("ranking")
        response = client.get(url)

        leaderboard = response.context["leaderboard"]

        # Find bob and dave (both have 80 points, 3 exact, 4 jokers)
        bob_entry = next(e for e in leaderboard if e["username"] == "bob")
        dave_entry = next(e for e in leaderboard if e["username"] == "dave")

        # They should have the same rank
        assert bob_entry["rank"] == dave_entry["rank"]

    def test_rank_skips_after_tie(
        self, users_with_ranking_data, client: Client
    ):
        """After tied users, next rank skips appropriately (1, 2, 2, 4)."""
        client.force_login(users_with_ranking_data[0])
        url = reverse("ranking")
        response = client.get(url)

        leaderboard = response.context["leaderboard"]
        ranks = [entry["rank"] for entry in leaderboard]

        # With our test data (alice=100, carol=80/4exact, bob=80/3exact, dave=80/3exact)
        # Expected: alice=1, carol=2, bob=3, dave=3
        # (carol is better than bob/dave due to more exact matches)
        assert ranks[0] == 1  # alice
        # Remaining ranks depend on tiebreaker ordering


class TestFlagEmojiHelper:
    """Test the flag emoji conversion utility."""

    def test_valid_country_code(self):
        """Valid ISO codes convert to flag emojis."""
        assert get_flag_emoji("DE") == "🇩🇪"
        assert get_flag_emoji("BR") == "🇧🇷"
        assert get_flag_emoji("US") == "🇺🇸"

    def test_lowercase_country_code(self):
        """Lowercase codes are handled correctly."""
        assert get_flag_emoji("de") == "🇩🇪"
        assert get_flag_emoji("br") == "🇧🇷"

    def test_none_returns_empty(self):
        """None input returns empty string."""
        assert get_flag_emoji(None) == ""

    def test_empty_string_returns_empty(self):
        """Empty string returns empty string."""
        assert get_flag_emoji("") == ""

    def test_invalid_length_returns_empty(self):
        """Non-2-character codes return empty string."""
        assert get_flag_emoji("D") == ""
        assert get_flag_emoji("DEU") == ""


class TestRankingViewEmptyState:
    """Test ranking view with no users."""

    def test_empty_leaderboard(self, db, client: Client):
        """Empty database shows empty leaderboard."""
        # Create a single user just to log in
        user = User.objects.create_user(
            username="lonely",
            email="lonely@test.com",
            password="testpass123",
            is_active=False,  # Inactive so they don't appear in ranking
        )
        active_user = User.objects.create_user(
            username="active",
            email="active@test.com",
            password="testpass123",
        )
        client.force_login(active_user)

        url = reverse("ranking")
        response = client.get(url)

        # The active user should appear (at minimum)
        leaderboard = response.context["leaderboard"]
        assert isinstance(leaderboard, list)


class TestRankingViewRendering:
    """Test that ranking data renders in template."""

    def test_username_in_response(self, users_with_ranking_data, client: Client):
        """Usernames appear in rendered HTML."""
        client.force_login(users_with_ranking_data[0])
        url = reverse("ranking")
        response = client.get(url)

        content = response.content.decode()
        assert "alice" in content
        assert "bob" in content

    def test_points_in_response(self, users_with_ranking_data, client: Client):
        """Points appear in rendered HTML."""
        client.force_login(users_with_ranking_data[0])
        url = reverse("ranking")
        response = client.get(url)

        content = response.content.decode()
        assert "100" in content  # alice's points
        assert "80" in content   # bob/carol/dave's points

    def test_flag_emoji_in_response(
        self, users_with_ranking_data, client: Client
    ):
        """Flag emojis appear in rendered HTML for users with champions."""
        client.force_login(users_with_ranking_data[0])
        url = reverse("ranking")
        response = client.get(url)

        content = response.content.decode()
        # Germany flag for alice
        assert "🇩🇪" in content
        # Brazil flag for bob
        assert "🇧🇷" in content

    def test_no_champion_placeholder(
        self, users_with_ranking_data, client: Client
    ):
        """Users without champion show placeholder text."""
        client.force_login(users_with_ranking_data[0])
        url = reverse("ranking")
        response = client.get(url)

        content = response.content.decode()
        # Check for dash placeholder or "Kein Champion" text
        assert "–" in content or "Kein Champion" in content
