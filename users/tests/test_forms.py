"""Tests for user forms."""

import pytest

from matches.models import Team
from users.forms import UserSettingsForm
from users.models import User


@pytest.mark.django_db
class TestUserSettingsForm:
    """Tests for UserSettingsForm validation."""

    def test_valid_data(self) -> None:
        """Test form with valid data."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "newname",
                "email": "new@example.com",
                "theme_preference": "dark",
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

    def test_username_max_20_chars(self) -> None:
        """Test form rejects username > 20 chars."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "a" * 21,
                "email": "test@example.com",
                "theme_preference": "system",
            },
            instance=user,
        )
        assert not form.is_valid()
        assert "username" in form.errors

    def test_username_exactly_20_chars_valid(self) -> None:
        """Test form accepts username with exactly 20 chars."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "a" * 20,
                "email": "test@example.com",
                "theme_preference": "system",
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

    def test_duplicate_username_rejected(self) -> None:
        """Test form rejects duplicate username."""
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="testpass123",
        )
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "existing",
                "email": "test@example.com",
                "theme_preference": "system",
            },
            instance=user,
        )
        assert not form.is_valid()
        assert "username" in form.errors
        assert "bereits vergeben" in str(form.errors["username"])

    def test_same_username_allowed(self) -> None:
        """Test user can keep their own username."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "theme_preference": "system",
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

    def test_duplicate_email_rejected(self) -> None:
        """Test form rejects duplicate email."""
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="testpass123",
        )
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "testuser",
                "email": "existing@example.com",
                "theme_preference": "system",
            },
            instance=user,
        )
        assert not form.is_valid()
        assert "email" in form.errors
        assert "bereits vergeben" in str(form.errors["email"])

    def test_same_email_allowed(self) -> None:
        """Test user can keep their own email."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "theme_preference": "system",
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

    def test_empty_champion_allowed(self) -> None:
        """Test form allows empty predicted_champion."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "theme_preference": "system",
                "predicted_champion": "",
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

    def test_valid_champion_selection(self) -> None:
        """Test form accepts valid team selection."""
        team = Team.objects.create(name="Germany", fifa_code="GER")
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "theme_preference": "system",
                "predicted_champion": team.pk,
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

    @pytest.mark.parametrize("theme", ["light", "dark", "system"])
    def test_all_theme_choices_valid(self, theme: str) -> None:
        """Test form accepts all theme choices."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "theme_preference": theme,
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

    def test_invalid_theme_rejected(self) -> None:
        """Test form rejects invalid theme choice."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        form = UserSettingsForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "theme_preference": "invalid",
            },
            instance=user,
        )
        assert not form.is_valid()
        assert "theme_preference" in form.errors
