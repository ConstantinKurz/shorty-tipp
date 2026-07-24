"""Tests for user settings view."""

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from matches.models import Match, Team
from users.models import User


@pytest.mark.django_db
class TestUserSettingsView:
    """Tests for UserSettingsView."""

    def test_anonymous_user_redirected_to_login(self, client: Client) -> None:
        """Test anonymous user is redirected to login."""
        response = client.get(reverse("users:settings"))
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_authenticated_user_can_access(self, client: Client) -> None:
        """Test authenticated user can access settings page."""
        _user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        client.login(username="testuser", password="testpass123")
        response = client.get(reverse("users:settings"))
        assert response.status_code == 200

    def test_context_contains_teams(self, client: Client) -> None:
        """Test context includes all teams for dropdown."""
        _user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        Team.objects.create(name="Germany", fifa_code="GER")
        Team.objects.create(name="Brazil", fifa_code="BRA")

        client.login(username="testuser", password="testpass123")
        response = client.get(reverse("users:settings"))

        assert "teams" in response.context
        assert response.context["teams"].count() == 2

    def test_can_change_champion_before_first_match(self, client: Client) -> None:
        """Test champion flag is True before first match."""
        _user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        team1 = Team.objects.create(name="Germany", fifa_code="GER")
        team2 = Team.objects.create(name="Brazil", fifa_code="BRA")
        # Match in the future
        Match.objects.create(
            team_home=team1,
            team_away=team2,
            kickoff=timezone.now() + timedelta(days=1),
            round="group",
        )

        client.login(username="testuser", password="testpass123")
        response = client.get(reverse("users:settings"))

        assert response.context["can_change_champion"] is True

    def test_cannot_change_champion_after_first_match(self, client: Client) -> None:
        """Test champion flag is False after first match kickoff."""
        _user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        team1 = Team.objects.create(name="Germany", fifa_code="GER")
        team2 = Team.objects.create(name="Brazil", fifa_code="BRA")
        # Match in the past
        Match.objects.create(
            team_home=team1,
            team_away=team2,
            kickoff=timezone.now() - timedelta(days=1),
            round="group",
        )

        client.login(username="testuser", password="testpass123")
        response = client.get(reverse("users:settings"))

        assert response.context["can_change_champion"] is False

    def test_can_change_champion_when_no_matches(self, client: Client) -> None:
        """Test champion flag is True when no matches exist."""
        _user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        client.login(username="testuser", password="testpass123")
        response = client.get(reverse("users:settings"))

        assert response.context["can_change_champion"] is True

    def test_form_submission_updates_user(self, client: Client) -> None:
        """Test successful form submission updates user."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        client.login(username="testuser", password="testpass123")

        response = client.post(
            reverse("users:settings"),
            data={
                "username": "newusername",
                "email": "new@example.com",
                "theme_preference": "dark",
            },
        )

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.username == "newusername"
        assert user.email == "new@example.com"
        assert user.theme_preference == "dark"

    def test_success_message_shown(self, client: Client) -> None:
        """Test success message is shown after save."""
        _user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        client.login(username="testuser", password="testpass123")

        response = client.post(
            reverse("users:settings"),
            data={
                "username": "testuser",
                "email": "test@example.com",
                "theme_preference": "system",
            },
            follow=True,
        )

        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert len(messages) == 1
        assert "gespeichert" in str(messages[0])

    def test_redirects_to_settings_after_save(self, client: Client) -> None:
        """Test redirects back to settings page after save."""
        _user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        client.login(username="testuser", password="testpass123")

        response = client.post(
            reverse("users:settings"),
            data={
                "username": "testuser",
                "email": "test@example.com",
                "theme_preference": "system",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("users:settings")
