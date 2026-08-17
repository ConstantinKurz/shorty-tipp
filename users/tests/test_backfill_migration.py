"""Tests for champion_bonus_points backfill migration."""

import importlib.util
import sys
from pathlib import Path

import pytest


def get_backfill_function():
    """Import the backfill function from the migration file."""
    migration_file = (
        Path(__file__).parent.parent
        / "migrations"
        / "0008_backfill_champion_bonus_points.py"
    )
    spec = importlib.util.spec_from_file_location(
        "backfill_migration", migration_file
    )
    if spec is None or spec.loader is None:
        raise ImportError("Could not load migration file")

    module = importlib.util.module_from_spec(spec)
    sys.modules["backfill_migration"] = module
    spec.loader.exec_module(module)
    return module.backfill_champion_bonus_points


@pytest.mark.django_db
class TestBackfillChampionBonusPoints:
    """Test backfill migration for champion_bonus_points field."""

    def test_backfill_sets_correct_bonus_amount(self, db):
        """Test backfill sets champion_bonus_points to correct value."""
        from django.utils import timezone

        from matches.models import Match, Team
        from users.models import User

        # Create champion team (category A = 20 points)
        champion = Team.objects.create(
            name="Germany",
            fifa_code="GER",
            odds_category="A",
            is_champion=True,
        )
        runner_up = Team.objects.create(
            name="Brazil",
            fifa_code="BRA",
            odds_category="B",
        )

        # Create finished final
        Match.objects.create(
            team_home=champion,
            team_away=runner_up,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=1,
            goals_away=0,
        )

        # Create users
        user_correct = User.objects.create_user(
            username="correct_predictor",
            password="test",
            predicted_champion=champion,
            total_points=20,  # Already has bonus in total
            champion_bonus_points=0,  # Not yet tracked
        )

        user_wrong = User.objects.create_user(
            username="wrong_predictor",
            password="test",
            predicted_champion=runner_up,
            total_points=0,
            champion_bonus_points=0,
        )

        # Run the backfill function
        backfill_champion_bonus_points = get_backfill_function()

        class FakeApps:
            """Fake apps registry for migration testing."""

            @staticmethod
            def get_model(app, model):
                if app == "users" and model == "User":
                    return User
                if app == "matches" and model == "Team":
                    return Team
                if app == "matches" and model == "Match":
                    return Match
                raise ValueError(f"Unknown model: {app}.{model}")

        backfill_champion_bonus_points(FakeApps(), None)

        # Refresh from DB
        user_correct.refresh_from_db()
        user_wrong.refresh_from_db()

        # Check correct user got bonus tracked
        assert user_correct.champion_bonus_points == 20
        # Wrong prediction should still be 0
        assert user_wrong.champion_bonus_points == 0

    def test_backfill_handles_no_champion_case(self, db):
        """Test backfill safely handles case where no champion is set."""
        from users.models import User

        # Create user without champion prediction
        user = User.objects.create_user(
            username="testuser",
            password="test",
            champion_bonus_points=0,
        )

        # Run the backfill function (should not crash)
        backfill_champion_bonus_points = get_backfill_function()

        class FakeApps:
            """Fake apps registry for migration testing."""

            @staticmethod
            def get_model(app, model):
                from matches.models import Match, Team

                if app == "users" and model == "User":
                    return User
                if app == "matches" and model == "Team":
                    return Team
                if app == "matches" and model == "Match":
                    return Match
                raise ValueError(f"Unknown model: {app}.{model}")

        # Should not raise any exception
        backfill_champion_bonus_points(FakeApps(), None)

        user.refresh_from_db()
        assert user.champion_bonus_points == 0

    def test_backfill_is_idempotent(self, db):
        """Test running backfill twice doesn't break data."""
        from django.utils import timezone

        from matches.models import Match, Team
        from users.models import User

        # Create champion team (category B = 30 points)
        champion = Team.objects.create(
            name="Brazil",
            fifa_code="BRA",
            odds_category="B",
            is_champion=True,
        )
        other = Team.objects.create(
            name="Germany",
            fifa_code="GER",
            odds_category="A",
        )

        # Create finished final
        Match.objects.create(
            team_home=champion,
            team_away=other,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=2,
            goals_away=1,
        )

        # Create user
        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=champion,
            total_points=30,
            champion_bonus_points=0,
        )

        # Run backfill
        backfill_champion_bonus_points = get_backfill_function()

        class FakeApps:
            """Fake apps registry for migration testing."""

            @staticmethod
            def get_model(app, model):
                from matches.models import Match, Team

                if app == "users" and model == "User":
                    return User
                if app == "matches" and model == "Team":
                    return Team
                if app == "matches" and model == "Match":
                    return Match
                raise ValueError(f"Unknown model: {app}.{model}")

        backfill_champion_bonus_points(FakeApps(), None)
        user.refresh_from_db()
        assert user.champion_bonus_points == 30

        # Run again - should not change anything
        backfill_champion_bonus_points(FakeApps(), None)
        user.refresh_from_db()
        assert user.champion_bonus_points == 30  # Still 30, not 60

