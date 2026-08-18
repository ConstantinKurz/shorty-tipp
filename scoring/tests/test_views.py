"""
Tests for scoring views.

Covers redirect behavior, ranking updates endpoint, and HomeView context.
"""

import pytest
from django.test import Client
from django.urls import reverse

from matches.models import Match, Team
from predictions.models import MatchPrediction
from scoring.ranking_service import RankingService
from users.models import User


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def other_user(db):
    """Create another test user."""
    return User.objects.create_user(username="otheruser", password="testpass123")


@pytest.fixture
def client():
    """Create a test client."""
    return Client()


@pytest.fixture
def authenticated_client(client, user):
    """Create an authenticated test client."""
    client.login(username="testuser", password="testpass123")
    return client


class TestRankingRedirect:
    """Tests for the /ranking/ to / redirect."""

    def test_ranking_redirects_to_home(self, client, user):
        """Test GET request to /ranking/ returns 302 status code."""
        client.login(username="testuser", password="testpass123")
        response = client.get("/ranking/")
        assert response.status_code == 302

    def test_ranking_redirect_location(self, client, user):
        """Test redirect Location header points to /."""
        client.login(username="testuser", password="testpass123")
        response = client.get("/ranking/", follow=False)
        assert response.url == "/"

    def test_ranking_redirect_follows_to_home(self, client, user):
        """Test accessing redirected URL loads home page successfully."""
        client.login(username="testuser", password="testpass123")
        response = client.get("/ranking/", follow=True)
        assert response.status_code == 200

    def test_ranking_url_resolves(self):
        """Test URL reverse lookup: reverse('ranking') returns /ranking/."""
        url = reverse("ranking")
        assert url == "/ranking/"


class TestRankingUpdatesView:
    """Tests for the RankingUpdatesView HTMX endpoint."""

    def test_ranking_updates_requires_authentication(self, client):
        """Test RankingUpdatesView requires authentication."""
        response = client.get(reverse("scoring:ranking-updates"))
        # Should redirect to login
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_ranking_updates_returns_200_when_authenticated(self, authenticated_client):
        """Test view returns 200 when authenticated."""
        response = authenticated_client.get(
            reverse("scoring:ranking-updates"),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200

    def test_ranking_updates_returns_partial_template(self, authenticated_client):
        """Test view returns ranking_updates.html partial."""
        response = authenticated_client.get(
            reverse("scoring:ranking-updates"),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        # Check that OOB swap attributes are present
        content = response.content.decode()
        assert 'hx-swap-oob="innerHTML"' in content

    def test_ranking_updates_includes_context_keys(self, authenticated_client):
        """Test view returns correct context keys."""
        response = authenticated_client.get(
            reverse("scoring:ranking-updates"),
            HTTP_HX_REQUEST="true",
        )
        assert "compact_leaderboard" in response.context
        assert "full_leaderboard" in response.context
        assert "leaderboard" in response.context
        assert "selected_round" in response.context
        assert "available_rounds" in response.context

    def test_ranking_updates_preserves_round_filter(self, authenticated_client):
        """Test ?round=group filters leaderboard correctly."""
        response = authenticated_client.get(
            reverse("scoring:ranking-updates") + "?round=group",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert response.context["selected_round"] == "group"

    def test_ranking_updates_invalid_round_ignored(self, authenticated_client):
        """Test invalid round parameter is ignored."""
        response = authenticated_client.get(
            reverse("scoring:ranking-updates") + "?round=invalid",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert response.context["selected_round"] is None


class TestHomeViewRankingContext:
    """Tests for HomeView ranking-related context."""

    def test_home_view_includes_ranking_interval(self, authenticated_client):
        """Test HomeView context includes ranking_interval."""
        response = authenticated_client.get(reverse("home"))
        assert response.status_code == 200
        assert "ranking_interval" in response.context
        # Should be 60 (idle) since no active matches
        assert response.context["ranking_interval"] in (1, 60)

    def test_home_view_includes_leaderboard_data(self, authenticated_client):
        """Test HomeView context includes leaderboard data."""
        response = authenticated_client.get(reverse("home"))
        assert "compact_leaderboard" in response.context
        assert "full_leaderboard" in response.context

    def test_home_view_round_filter(self, authenticated_client):
        """Test HomeView respects round filter."""
        response = authenticated_client.get(reverse("home") + "?round=group")
        assert response.status_code == 200
        assert response.context["selected_round"] == "group"
