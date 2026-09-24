"""Management command for running the notification daemon."""

from __future__ import annotations

import logging
import signal
import time
from datetime import date
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.services import EmailService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Run continuous notification daemon that sends scheduled emails.

    Sends:
    - Daily leaderboard report to admin at configured hour
    - Daily prediction reminders to users at configured hour
    """

    help = "Run notification daemon for scheduled email delivery"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.running = True
        self.last_leaderboard_date: date | None = None
        self.last_reminder_date: date | None = None

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run once and exit (for testing)",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=3600,
            help="Check interval in seconds (default: 3600)",
        )
        parser.add_argument(
            "--leaderboard-hour",
            type=int,
            default=20,
            help="Hour to send leaderboard email (0-23, default: 20)",
        )
        parser.add_argument(
            "--reminder-hour",
            type=int,
            default=10,
            help="Hour to send prediction reminders (0-23, default: 10)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        once = options["once"]
        interval = options["interval"]
        leaderboard_hour = options["leaderboard_hour"]
        reminder_hour = options["reminder_hour"]

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting notification daemon (leaderboard: {leaderboard_hour}:00, "
                f"reminders: {reminder_hour}:00, interval: {interval}s)..."
            )
        )

        while self.running:
            try:
                now = timezone.now()
                today = now.date()
                current_hour = now.hour

                # Send leaderboard email at configured hour
                if current_hour >= leaderboard_hour and self.last_leaderboard_date != today:
                    self._send_leaderboard_email()
                    self.last_leaderboard_date = today

                # Send prediction reminders at configured hour
                if current_hour >= reminder_hour and self.last_reminder_date != today:
                    self._send_prediction_reminders()
                    self.last_reminder_date = today

                # Log iteration
                timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
                self.stdout.write(f"[{timestamp}] Check complete. Next check in {interval}s.")

                # Exit if --once flag
                if once:
                    self.stdout.write(self.style.SUCCESS("✓ Single iteration complete"))
                    break

                # Sleep until next iteration
                time.sleep(interval)

            except KeyboardInterrupt:
                self.stdout.write("\nReceived interrupt signal")
                break

            # Broad catch: this supervisor loop must survive unexpected errors.
            except Exception as e:
                logger.exception("Notification daemon iteration failed: %s", e)
                self.stdout.write(self.style.ERROR(f"Error: {e}. Retrying in 60 seconds..."))
                if once:
                    raise  # Re-raise in test mode
                time.sleep(60)

        self.stdout.write(self.style.SUCCESS("Notification daemon stopped"))

    def _shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received signal %d, shutting down gracefully...", signum)
        self.stdout.write("\nShutting down gracefully...")
        self.running = False

    def _send_leaderboard_email(self) -> None:
        """Send leaderboard email to admin."""
        self.stdout.write("Sending leaderboard email to admin...")
        success, message = EmailService.send_leaderboard_to_admin()
        if success:
            self.stdout.write(self.style.SUCCESS(f"  ✓ {message}"))
        else:
            self.stdout.write(self.style.WARNING(f"  ⚠ {message}"))

    def _send_prediction_reminders(self) -> None:
        """Send prediction reminders to users."""
        self.stdout.write("Sending prediction reminders...")
        success_count, fail_count = EmailService.send_all_prediction_reminders()
        if success_count > 0 or fail_count > 0:
            self.stdout.write(self.style.SUCCESS(f"  ✓ {success_count} sent, {fail_count} failed"))
        else:
            self.stdout.write("  No users with missing predictions")
