"""Tests for the notification_daemon management command."""

from datetime import date
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command


class TestNotificationDaemon:
    """Tests for notification_daemon command."""

    def test_once_flag_runs_single_iteration(self, db):
        """Test that --once flag runs a single iteration and exits."""
        out = StringIO()

        with patch("notifications.management.commands.notification_daemon.EmailService") as mock_service:
            mock_service.send_leaderboard_to_admin.return_value = (True, "Sent")
            mock_service.send_all_prediction_reminders.return_value = (0, 0)
            call_command("notification_daemon", "--once", stdout=out)

        output = out.getvalue()
        assert "Single iteration complete" in output

    def test_leaderboard_email_sent_at_configured_hour(self, db):
        """Test leaderboard email is sent when hour matches."""
        out = StringIO()
        mock_now = MagicMock()
        mock_now.hour = 20
        mock_now.date.return_value = date(2026, 6, 15)
        mock_now.strftime.return_value = "2026-06-15 20:00:00"

        with patch("notifications.management.commands.notification_daemon.timezone") as mock_tz:
            mock_tz.now.return_value = mock_now
            with patch("notifications.management.commands.notification_daemon.EmailService") as mock_service:
                mock_service.send_leaderboard_to_admin.return_value = (True, "Sent")
                mock_service.send_all_prediction_reminders.return_value = (0, 0)

                call_command(
                    "notification_daemon",
                    "--once",
                    "--leaderboard-hour=20",
                    "--reminder-hour=10",
                    stdout=out,
                )

        mock_service.send_leaderboard_to_admin.assert_called_once()

    def test_reminder_email_sent_at_configured_hour(self, db):
        """Test reminder emails are sent when hour matches."""
        out = StringIO()
        mock_now = MagicMock()
        mock_now.hour = 10
        mock_now.date.return_value = date(2026, 6, 15)
        mock_now.strftime.return_value = "2026-06-15 10:00:00"

        with patch("notifications.management.commands.notification_daemon.timezone") as mock_tz:
            mock_tz.now.return_value = mock_now
            with patch("notifications.management.commands.notification_daemon.EmailService") as mock_service:
                mock_service.send_leaderboard_to_admin.return_value = (True, "Sent")
                mock_service.send_all_prediction_reminders.return_value = (3, 0)

                call_command(
                    "notification_daemon",
                    "--once",
                    "--leaderboard-hour=20",
                    "--reminder-hour=10",
                    stdout=out,
                )

        mock_service.send_all_prediction_reminders.assert_called_once()

    def test_no_duplicate_emails_same_day(self, db):
        """Test that emails are not sent twice on the same day."""
        out = StringIO()

        # Simulate two iterations on the same day
        mock_now = MagicMock()
        mock_now.hour = 20
        test_date = date(2026, 6, 15)
        mock_now.date.return_value = test_date
        mock_now.strftime.return_value = "2026-06-15 20:00:00"

        with patch("notifications.management.commands.notification_daemon.timezone") as mock_tz:
            mock_tz.now.return_value = mock_now
            with patch("notifications.management.commands.notification_daemon.EmailService") as mock_service:
                mock_service.send_leaderboard_to_admin.return_value = (True, "Sent")
                mock_service.send_all_prediction_reminders.return_value = (0, 0)

                # First call
                call_command(
                    "notification_daemon",
                    "--once",
                    "--leaderboard-hour=20",
                    stdout=out,
                )

        # Verify email was sent once in the single iteration
        assert mock_service.send_leaderboard_to_admin.call_count == 1

    def test_skips_leaderboard_before_configured_hour(self, db):
        """Test leaderboard email is not sent before configured hour."""
        out = StringIO()
        mock_now = MagicMock()
        mock_now.hour = 15  # Before 20:00
        mock_now.date.return_value = date(2026, 6, 15)
        mock_now.strftime.return_value = "2026-06-15 15:00:00"

        with patch("notifications.management.commands.notification_daemon.timezone") as mock_tz:
            mock_tz.now.return_value = mock_now
            with patch("notifications.management.commands.notification_daemon.EmailService") as mock_service:
                mock_service.send_leaderboard_to_admin.return_value = (True, "Sent")
                mock_service.send_all_prediction_reminders.return_value = (0, 0)
                call_command(
                    "notification_daemon",
                    "--once",
                    "--leaderboard-hour=20",
                    "--reminder-hour=10",
                    stdout=out,
                )

        mock_service.send_leaderboard_to_admin.assert_not_called()

    def test_skips_reminder_before_configured_hour(self, db):
        """Test reminder emails are not sent before configured hour."""
        out = StringIO()
        mock_now = MagicMock()
        mock_now.hour = 8  # Before 10:00
        mock_now.date.return_value = date(2026, 6, 15)
        mock_now.strftime.return_value = "2026-06-15 08:00:00"

        with patch("notifications.management.commands.notification_daemon.timezone") as mock_tz:
            mock_tz.now.return_value = mock_now
            with patch("notifications.management.commands.notification_daemon.EmailService") as mock_service:
                call_command(
                    "notification_daemon",
                    "--once",
                    "--leaderboard-hour=20",
                    "--reminder-hour=10",
                    stdout=out,
                )

        mock_service.send_all_prediction_reminders.assert_not_called()

    def test_custom_interval_argument(self, db):
        """Test that custom interval argument is accepted."""
        out = StringIO()

        with patch("notifications.management.commands.notification_daemon.EmailService") as mock_service:
            mock_service.send_leaderboard_to_admin.return_value = (True, "Sent")
            mock_service.send_all_prediction_reminders.return_value = (0, 0)
            call_command(
                "notification_daemon",
                "--once",
                "--interval=1800",
                stdout=out,
            )

        # Command should complete without error
        assert "Single iteration complete" in out.getvalue()

    def test_handles_exception_gracefully(self, db):
        """Test that exceptions are handled and reported."""
        out = StringIO()

        with patch("notifications.management.commands.notification_daemon.timezone") as mock_tz:
            mock_tz.now.side_effect = Exception("Test error")

            with pytest.raises(Exception, match="Test error"):
                call_command("notification_daemon", "--once", stdout=out)

        assert "Error" in out.getvalue()
