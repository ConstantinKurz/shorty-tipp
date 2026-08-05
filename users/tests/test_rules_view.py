"""Tests for Rules view."""

import pytest
from django.test import Client
from django.urls import resolve, reverse

from users.models import User
from users.views import RulesView


@pytest.mark.django_db
class TestRulesView:
    """Tests for RulesView."""

    def test_rules_url_resolves_to_rules_view(self) -> None:
        """Test that /rules/ URL resolves to RulesView."""
        resolver = resolve("/rules/")
        assert resolver.func.view_class == RulesView

    def test_rules_view_accessible_to_anonymous(self, client: Client) -> None:
        """Test anonymous user can access the rules page (no login required)."""
        response = client.get(reverse("users:rules"))
        assert response.status_code == 200

    def test_rules_view_accessible_to_authenticated(self, client: Client) -> None:
        """Test authenticated user can access the rules page."""
        _user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        client.login(username="testuser", password="testpass123")
        response = client.get(reverse("users:rules"))
        assert response.status_code == 200

    def test_rules_view_uses_correct_template(self, client: Client) -> None:
        """Test that rules view uses the correct template."""
        response = client.get(reverse("users:rules"))
        assert "users/rules.html" in [t.name for t in response.templates]

    def test_rules_view_context_includes_page_title(self, client: Client) -> None:
        """Test that page_title is in context."""
        response = client.get(reverse("users:rules"))
        assert "page_title" in response.context
        assert response.context["page_title"] == "Rules & How to Play"

    def test_rules_page_contains_scoring_section(self, client: Client) -> None:
        """Test that page contains Match Scoring section."""
        response = client.get(reverse("users:rules"))
        content = response.content.decode()
        assert "Match Scoring" in content

    def test_rules_page_contains_joker_section(self, client: Client) -> None:
        """Test that page contains Joker System section."""
        response = client.get(reverse("users:rules"))
        content = response.content.decode()
        assert "Joker System" in content

    def test_rules_page_contains_round_multipliers_section(self, client: Client) -> None:
        """Test that page contains Round Multipliers section."""
        response = client.get(reverse("users:rules"))
        content = response.content.decode()
        assert "Round Multipliers" in content

    def test_rules_page_contains_champion_prediction_section(self, client: Client) -> None:
        """Test that page contains Champion Prediction section."""
        response = client.get(reverse("users:rules"))
        content = response.content.decode()
        assert "Champion Prediction" in content

    def test_rules_page_contains_how_to_use_section(self, client: Client) -> None:
        """Test that page contains How to Use section."""
        response = client.get(reverse("users:rules"))
        content = response.content.decode()
        assert "How to Use" in content

    def test_rules_page_contains_quick_links(self, client: Client) -> None:
        """Test that page contains Quick Links section."""
        response = client.get(reverse("users:rules"))
        content = response.content.decode()
        assert "Quick Links" in content
        assert "Make Predictions" in content
        assert "View Rankings" in content
        assert "User Settings" in content
