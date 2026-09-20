"""Tests for management commands in the users app."""

from io import StringIO

from django.core.management import call_command

from users.models import User


class TestSeedGlobalRanksCommand:
    """Tests for the seed_global_ranks management command."""

    def test_seed_global_ranks_command(self, db):
        """Test seed_global_ranks command updates user ranks."""
        # Create test users
        user1 = User.objects.create_user("alice", password="test")
        user1.total_points = 100
        user1.save()

        user2 = User.objects.create_user("bob", password="test")
        user2.total_points = 80
        user2.save()

        # Verify ranks are None initially
        assert user1.global_rank is None
        assert user2.global_rank is None

        # Run the command
        out = StringIO()
        call_command("seed_global_ranks", stdout=out)

        # Verify output
        output = out.getvalue()
        assert "Calculating global ranks..." in output
        assert "Updated global ranks for 2 users" in output

        # Verify ranks are now set
        user1.refresh_from_db()
        user2.refresh_from_db()
        assert user1.global_rank == 1
        assert user2.global_rank == 2

    def test_seed_global_ranks_command_empty_database(self, db):
        """Test seed_global_ranks command handles empty database."""
        out = StringIO()
        call_command("seed_global_ranks", stdout=out)

        output = out.getvalue()
        assert "Calculating global ranks..." in output
        assert "Updated global ranks for 0 users" in output
