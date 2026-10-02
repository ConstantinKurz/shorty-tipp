"""
Pytest configuration and fixtures for tipapp.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from matches.models import Match, Round, Team
from matches.tournament import get_active_tournament


@pytest.fixture
def tournament(db):
    """
    Return the active tournament seeded by the migrations.

    Returns:
        Tournament: The active tournament of the test database.
    """
    return get_active_tournament()


@pytest.fixture
def rounds(tournament):
    """
    Return the rounds of the active tournament keyed by their code.

    Returns:
        dict[str, Round]: Mapping of round code to Round instance.
    """
    return {match_round.code: match_round for match_round in tournament.rounds.all()}


def make_team(name, fifa_code, **kwargs):
    """
    Create a Team for tests.

    Args:
        name: Team name (e.g., "Germany")
        fifa_code: FIFA country code (e.g., "GER")
        **kwargs: Additional Team field values

    Returns:
        Team: The created team
    """
    return Team.objects.create(name=name, fifa_code=fifa_code, **kwargs)


def make_match(*, team_home, team_away, kickoff=None, round="group", **kwargs):
    """
    Create a Match for tests.

    Tests must not construct Match directly so that schema changes to the model
    touch this factory instead of every call site.

    Args:
        team_home: Home team instance
        team_away: Away team instance
        kickoff: Match start time, defaults to one day in the future
        round: Round code (e.g., "group", "r16", "final") or a Round instance
        **kwargs: Additional Match field values

    Returns:
        Match: The created match
    """
    if kickoff is None:
        kickoff = timezone.now() + timedelta(days=1)

    if isinstance(round, str):
        round = Round.objects.get(tournament__is_active=True, code=round)

    return Match.objects.create(
        team_home=team_home,
        team_away=team_away,
        kickoff=kickoff,
        round=round,
        **kwargs,
    )


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
