"""
Tests for the User model.
"""

import pytest


@pytest.mark.django_db
class TestUserModel:
    """Tests for the custom User model."""

    def test_create_user(self):
        """Test creating a regular user."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self):
        """Test creating a superuser."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123",
        )
        assert admin.username == "admin"
        assert admin.is_active
        assert admin.is_staff
        assert admin.is_superuser

    def test_user_str_representation(self):
        """Test the string representation of a user."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        assert str(user) == "testuser"

    def test_admin_user_fixture(self, admin_user):
        """Test the admin_user fixture from conftest."""
        assert admin_user.is_superuser
        assert admin_user.username == "admin"

    def test_regular_user_fixture(self, regular_user):
        """Test the regular_user fixture from conftest."""
        assert not regular_user.is_superuser
        assert regular_user.username == "testuser"

    def test_user_with_predicted_champion(self):
        """Test user with predicted champion set."""
        from django.contrib.auth import get_user_model

        from matches.models import Team

        User = get_user_model()
        team = Team.objects.create(
            name="Germany",
            fifa_code="GER",
            points=0,
        )
        user = User.objects.create_user(
            username="predictor",
            email="predictor@example.com",
            password="test123",
        )
        user.predicted_champion = team
        user.save()

        assert user.predicted_champion == team
        assert user.predicted_champion.name == "Germany"

    def test_user_without_predicted_champion(self):
        """Test user without predicted champion (NULL)."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="noprediction",
            email="noprediction@example.com",
            password="test123",
        )

        assert user.predicted_champion is None

    def test_team_champion_predictions_relationship(self):
        """Test relationship: team.champion_predictions.all()."""
        from django.contrib.auth import get_user_model

        from matches.models import Team

        User = get_user_model()
        team = Team.objects.create(
            name="Brazil",
            fifa_code="BRA",
            points=0,
        )

        # Create multiple users predicting this team
        user1 = User.objects.create_user(username="user1", password="test123")
        user1.predicted_champion = team
        user1.save()

        user2 = User.objects.create_user(username="user2", password="test123")
        user2.predicted_champion = team
        user2.save()

        # User without prediction
        User.objects.create_user(username="user3", password="test123")

        # Query users who predicted this team
        predictions = team.champion_predictions.all()
        assert predictions.count() == 2
        assert user1 in predictions
        assert user2 in predictions

    def test_team_deleted_sets_predicted_champion_null(self):
        """Test cascade behavior: team deleted sets predicted_champion to NULL."""
        from django.contrib.auth import get_user_model

        from matches.models import Team

        User = get_user_model()
        team = Team.objects.create(
            name="Argentina",
            fifa_code="ARG",
            points=0,
        )
        user = User.objects.create_user(
            username="argfan",
            email="argfan@example.com",
            password="test123",
        )
        user.predicted_champion = team
        user.save()

        team.delete()

        # Refresh user from database
        user.refresh_from_db()

        # User still exists but champion is NULL
        assert User.objects.filter(username="argfan").exists()
        assert user.predicted_champion is None

