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
