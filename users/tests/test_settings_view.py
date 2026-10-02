"""Tests for user settings view."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from conftest import make_match
from matches.models import Team
from users.models import User

REFERENCE_NOW = datetime(2026, 6, 11, 18, 0, tzinfo=UTC)
KICKOFF_BEFORE_NOW = datetime(2026, 6, 11, 16, 0, tzinfo=UTC)
KICKOFF_AFTER_NOW = datetime(2026, 6, 11, 20, 0, tzinfo=UTC)


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
        make_match(
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
        make_match(
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


@pytest.mark.django_db
class TestChampionLockEnforcement:
    """Tests for server-side enforcement of the champion pick lock."""

    def _create_user(self, champion: Team | None = None) -> User:
        """Create a logged-in-able test user with an optional champion pick."""
        return User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            predicted_champion=champion,
        )

    def _create_first_match(self, kickoff: datetime) -> None:
        """Create the tournament's first match at a fixed kickoff time."""
        make_match(
            team_home=Team.objects.create(name="Mexico", fifa_code="MEX"),
            team_away=Team.objects.create(name="Canada", fifa_code="CAN"),
            kickoff=kickoff,
            round="group",
        )

    def test_champion_change_accepted_before_first_kickoff(self, client: Client) -> None:
        """Test champion can be changed while the first match has not started."""
        germany = Team.objects.create(name="Germany", fifa_code="GER")
        brazil = Team.objects.create(name="Brazil", fifa_code="BRA")
        user = self._create_user(champion=germany)
        self._create_first_match(KICKOFF_AFTER_NOW)
        client.login(username="testuser", password="testpass123")

        with patch("users.views.timezone.now", return_value=REFERENCE_NOW):
            response = client.post(
                reverse("users:settings"),
                data={
                    "username": "testuser",
                    "email": "test@example.com",
                    "theme_preference": "system",
                    "predicted_champion": brazil.pk,
                },
            )

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.predicted_champion == brazil

    def test_champion_change_rejected_after_first_kickoff(self, client: Client) -> None:
        """Test a posted champion is ignored once the first match kicked off."""
        germany = Team.objects.create(name="Germany", fifa_code="GER")
        brazil = Team.objects.create(name="Brazil", fifa_code="BRA")
        user = self._create_user(champion=germany)
        self._create_first_match(KICKOFF_BEFORE_NOW)
        client.login(username="testuser", password="testpass123")

        with patch("users.views.timezone.now", return_value=REFERENCE_NOW):
            response = client.post(
                reverse("users:settings"),
                data={
                    "username": "testuser",
                    "email": "test@example.com",
                    "theme_preference": "system",
                    "predicted_champion": brazil.pk,
                },
            )

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.predicted_champion == germany

    def test_champion_preserved_on_unrelated_save_after_kickoff(self, client: Client) -> None:
        """Test saving only theme after kickoff does not wipe the champion pick."""
        germany = Team.objects.create(name="Germany", fifa_code="GER")
        user = self._create_user(champion=germany)
        self._create_first_match(KICKOFF_BEFORE_NOW)
        client.login(username="testuser", password="testpass123")

        with patch("users.views.timezone.now", return_value=REFERENCE_NOW):
            response = client.post(
                reverse("users:settings"),
                data={
                    "username": "testuser",
                    "email": "test@example.com",
                    "theme_preference": "dark",
                },
            )

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.predicted_champion == germany
        assert user.theme_preference == "dark"

    def test_champion_editable_when_no_matches_exist(self, client: Client) -> None:
        """Test champion stays editable while no matches are scheduled."""
        brazil = Team.objects.create(name="Brazil", fifa_code="BRA")
        user = self._create_user()
        client.login(username="testuser", password="testpass123")

        with patch("users.views.timezone.now", return_value=REFERENCE_NOW):
            response = client.post(
                reverse("users:settings"),
                data={
                    "username": "testuser",
                    "email": "test@example.com",
                    "theme_preference": "system",
                    "predicted_champion": brazil.pk,
                },
            )

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.predicted_champion == brazil

    def test_settings_page_renders_champion_field_before_kickoff(self, client: Client) -> None:
        """Test the champion select is rendered before the first kickoff."""
        self._create_user()
        self._create_first_match(KICKOFF_AFTER_NOW)
        client.login(username="testuser", password="testpass123")

        with patch("users.views.timezone.now", return_value=REFERENCE_NOW):
            response = client.get(reverse("users:settings"))

        assert response.status_code == 200
        assert 'name="predicted_champion"' in response.content.decode()

    def test_settings_page_hides_champion_field_after_kickoff(self, client: Client) -> None:
        """Test no champion form control is rendered after the first kickoff."""
        germany = Team.objects.create(name="Germany", fifa_code="GER")
        self._create_user(champion=germany)
        self._create_first_match(KICKOFF_BEFORE_NOW)
        client.login(username="testuser", password="testpass123")

        with patch("users.views.timezone.now", return_value=REFERENCE_NOW):
            response = client.get(reverse("users:settings"))

        content = response.content.decode()
        assert response.status_code == 200
        assert 'name="predicted_champion"' not in content
        assert "Germany" in content
