"""
Pytest configuration and fixtures for tipapp.
"""

import pytest


@pytest.fixture
def admin_user(db):
    """
    Create a superuser for testing admin functionality.

    Returns:
        User: Superuser instance with full permissions
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="admin123",
    )


@pytest.fixture
def regular_user(db):
    """
    Create a regular user for testing standard functionality.

    Returns:
        User: Regular user instance without staff permissions
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="user@test.com",
        password="testpass123",
    )


@pytest.fixture
def multiple_users(db):
    """
    Create multiple users for testing ranking and leaderboard functionality.

    Returns:
        list[User]: List of 3 regular user instances
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    users = []
    for i in range(1, 4):
        user = User.objects.create_user(
            username=f"user{i}",
            email=f"user{i}@test.com",
            password="testpass123",
        )
        users.append(user)
    return users
