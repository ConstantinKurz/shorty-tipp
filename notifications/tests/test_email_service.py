"""Tests for the EmailService class."""

from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone

from conftest import make_match
from notifications.services import EmailService


@pytest.fixture
def user(db):
    """Create a test user."""
    from users.models import User

    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        first_name="Test",
    )


@pytest.fixture
def staff_user(db):
    """Create a test staff user."""
    from users.models import User

    return User.objects.create_user(
        username="staffuser",
        email="staff@example.com",
        password="testpass123",
        is_staff=True,
    )


@pytest.fixture
def inactive_user(db):
    """Create an inactive test user."""
    from users.models import User

    return User.objects.create_user(
        username="inactiveuser",
        email="inactive@example.com",
        password="testpass123",
        is_active=False,
    )


@pytest.fixture
def teams(db):
    """Create test teams."""
    from matches.models import Team

    home = Team.objects.create(name="Germany", fifa_code="GER")
    away = Team.objects.create(name="France", fifa_code="FRA")
    return home, away


@pytest.fixture
def upcoming_match(db, teams):
    """Create a match starting in 12 hours."""
    home, away = teams
    return make_match(
        team_home=home,
        team_away=away,
        kickoff=timezone.now() + timedelta(hours=12),
        round="group",
        status="scheduled",
    )


@pytest.fixture
def far_future_match(db, teams):
    """Create a match starting in 48 hours."""
    home, away = teams
    return make_match(
        team_home=home,
        team_away=away,
        kickoff=timezone.now() + timedelta(hours=48),
        round="group",
        status="scheduled",
    )


@pytest.fixture
def past_match(db, teams):
    """Create a match that already started."""
    home, away = teams
    return make_match(
        team_home=home,
        team_away=away,
        kickoff=timezone.now() - timedelta(hours=2),
        round="group",
        status="finished",
    )


@pytest.fixture
def leaderboard_snapshot(db):
    """Create a test leaderboard snapshot."""
    from scoring.models import LeaderboardSnapshot

    return LeaderboardSnapshot.objects.create(
        snapshot_type="daily",
        data=[
            {
                "rank": 1,
                "user_id": 1,
                "username": "leader",
                "total_points": 100,
                "exact_match_count": 5,
                "jokers_used": 2,
            },
            {
                "rank": 2,
                "user_id": 2,
                "username": "second",
                "total_points": 80,
                "exact_match_count": 3,
                "jokers_used": 1,
            },
        ],
    )


class TestSendLeaderboardToAdmin:
    """Tests for send_leaderboard_to_admin method."""

    def test_success_with_valid_config(self, leaderboard_snapshot):
        """Test successful email sending with valid configuration."""
        with patch("notifications.services.send_mail") as mock_send:
            with override_settings(LEADERBOARD_ADMIN_EMAIL="admin@test.com"):
                success, message = EmailService.send_leaderboard_to_admin()

        assert success is True
        assert "admin@test.com" in message
        mock_send.assert_called_once()

        # Verify email parameters
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["recipient_list"] == ["admin@test.com"]
        assert "Leaderboard Report" in call_kwargs["subject"]

    def test_fails_without_admin_email(self, leaderboard_snapshot):
        """Test failure when LEADERBOARD_ADMIN_EMAIL is not configured."""
        with override_settings(LEADERBOARD_ADMIN_EMAIL=""):
            success, message = EmailService.send_leaderboard_to_admin()

        assert success is False
        assert "not configured" in message

    def test_fails_without_snapshot(self, db):
        """Test failure when no leaderboard snapshot exists."""
        with override_settings(LEADERBOARD_ADMIN_EMAIL="admin@test.com"):
            success, message = EmailService.send_leaderboard_to_admin()

        assert success is False
        assert "No leaderboard snapshot" in message

    def test_handles_email_exception(self, leaderboard_snapshot):
        """Test handling of email sending exceptions."""
        with patch(
            "notifications.services.send_mail",
            side_effect=SMTPException("SMTP error"),
        ):
            with override_settings(LEADERBOARD_ADMIN_EMAIL="admin@test.com"):
                success, message = EmailService.send_leaderboard_to_admin()

        assert success is False
        assert "Failed to send email" in message

    def test_unexpected_exception_propagates(self, leaderboard_snapshot):
        """An error the service cannot handle is not swallowed into a (False, message)."""
        with patch(
            "notifications.services.send_mail",
            side_effect=RuntimeError("programming error"),
        ):
            with override_settings(LEADERBOARD_ADMIN_EMAIL="admin@test.com"):
                with pytest.raises(RuntimeError, match="programming error"):
                    EmailService.send_leaderboard_to_admin()


class TestGetUsersWithMissingPredictions:
    """Tests for get_users_with_missing_predictions method."""

    def test_finds_user_without_prediction(self, user, upcoming_match):
        """Test finding user without prediction for upcoming match."""
        result = EmailService.get_users_with_missing_predictions()

        assert user in result
        assert upcoming_match in result[user]

    def test_ignores_user_with_prediction(self, user, upcoming_match):
        """Test that users with existing predictions are not included."""
        from predictions.models import MatchPrediction

        MatchPrediction.objects.create(
            user=user,
            match=upcoming_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        result = EmailService.get_users_with_missing_predictions()

        assert user not in result

    def test_ignores_far_future_matches(self, user, far_future_match):
        """Test that matches more than 24h away are not included."""
        result = EmailService.get_users_with_missing_predictions()

        # User should not be in result since match is > 24h away
        if user in result:
            assert far_future_match not in result[user]

    def test_ignores_past_matches(self, user, past_match):
        """Test that past matches are not included."""
        result = EmailService.get_users_with_missing_predictions()

        if user in result:
            assert past_match not in result[user]

    def test_ignores_staff_users(self, staff_user, upcoming_match):
        """Test that staff users are excluded."""
        result = EmailService.get_users_with_missing_predictions()

        assert staff_user not in result

    def test_ignores_inactive_users(self, inactive_user, upcoming_match):
        """Test that inactive users are excluded."""
        result = EmailService.get_users_with_missing_predictions()

        assert inactive_user not in result

    def test_returns_empty_when_no_upcoming_matches(self, user, db):
        """Test returns empty dict when no matches in next 24h."""
        result = EmailService.get_users_with_missing_predictions()

        assert result == {}

    def test_multiple_missing_matches(self, user, teams):
        """Test user with multiple missing predictions."""
        home, away = teams
        make_match(
            team_home=home,
            team_away=away,
            kickoff=timezone.now() + timedelta(hours=6),
            round="group",
            status="scheduled",
        )
        make_match(
            team_home=away,
            team_away=home,
            kickoff=timezone.now() + timedelta(hours=18),
            round="group",
            status="scheduled",
        )

        result = EmailService.get_users_with_missing_predictions()

        assert user in result
        assert len(result[user]) == 2


class TestSendPredictionReminder:
    """Tests for send_prediction_reminder method."""

    def test_success_with_valid_user_and_matches(self, user, upcoming_match):
        """Test successful reminder email sending."""
        with patch("notifications.services.send_mail") as mock_send:
            success, message = EmailService.send_prediction_reminder(user, [upcoming_match])

        assert success is True
        assert user.email in message
        mock_send.assert_called_once()

        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["recipient_list"] == [user.email]
        assert "fehlt" in call_kwargs["subject"]

    def test_fails_with_no_email(self, upcoming_match, db):
        """Test failure when user has no email address."""
        from users.models import User

        user_no_email = User.objects.create_user(username="noemail", email="", password="test123")

        success, message = EmailService.send_prediction_reminder(user_no_email, [upcoming_match])

        assert success is False
        assert "no email address" in message

    def test_fails_with_empty_matches(self, user):
        """Test failure when no matches provided."""
        success, message = EmailService.send_prediction_reminder(user, [])

        assert success is False
        assert "No matches" in message

    def test_handles_email_exception(self, user, upcoming_match):
        """Test handling of email sending exceptions."""
        with patch(
            "notifications.services.send_mail",
            side_effect=SMTPException("SMTP error"),
        ):
            success, message = EmailService.send_prediction_reminder(user, [upcoming_match])

        assert success is False
        assert "Failed to send email" in message

    def test_unexpected_exception_propagates(self, user, upcoming_match):
        """An error the service cannot handle is not swallowed into a (False, message)."""
        with patch(
            "notifications.services.send_mail",
            side_effect=RuntimeError("programming error"),
        ):
            with pytest.raises(RuntimeError, match="programming error"):
                EmailService.send_prediction_reminder(user, [upcoming_match])


class TestSendAllPredictionReminders:
    """Tests for send_all_prediction_reminders method."""

    def test_sends_to_all_users_with_missing_predictions(self, user, upcoming_match, db):
        """Test sending reminders to all users with missing predictions."""
        from users.models import User

        User.objects.create_user(username="user2", email="user2@test.com", password="test123")

        with patch("notifications.services.send_mail"):
            success_count, fail_count = EmailService.send_all_prediction_reminders()

        assert success_count == 2
        assert fail_count == 0

    def test_returns_zero_when_no_missing_predictions(self, db):
        """Test returns zeros when no one has missing predictions."""
        success_count, fail_count = EmailService.send_all_prediction_reminders()

        assert success_count == 0
        assert fail_count == 0

    def test_counts_failures_correctly(self, user, upcoming_match, db):
        """Test that failed sends are counted correctly."""
        from users.models import User

        User.objects.create_user(username="user2", email="user2@test.com", password="test123")

        with patch(
            "notifications.services.send_mail",
            side_effect=[None, SMTPException("Failed")],
        ):
            success_count, fail_count = EmailService.send_all_prediction_reminders()

        assert success_count == 1
        assert fail_count == 1
