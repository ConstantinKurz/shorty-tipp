"""Management command to test email sending."""

from django.core.management.base import BaseCommand

from notifications.services import EmailService
from users.models import User


class Command(BaseCommand):
    """Test email sending with real SMTP."""

    help = "Send test emails to verify SMTP configuration"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--leaderboard",
            action="store_true",
            help="Send leaderboard report to admin",
        )
        parser.add_argument(
            "--reminder",
            type=str,
            help="Send reminder to user (provide username)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        if options["leaderboard"]:
            self.stdout.write("Sending leaderboard report...")
            success, message = EmailService.send_leaderboard_to_admin()
            if success:
                self.stdout.write(self.style.SUCCESS(f"✓ {message}"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ {message}"))

        elif options["reminder"]:
            username = options["reminder"]
            try:
                user = User.objects.get(username=username)
                users_with_missing = EmailService.get_users_with_missing_predictions()

                if user in users_with_missing:
                    matches = users_with_missing[user]
                    self.stdout.write(
                        f"Sending reminder to {username} for {len(matches)} matches..."
                    )
                    success, message = EmailService.send_prediction_reminder(user, matches)
                    if success:
                        self.stdout.write(self.style.SUCCESS(f"✓ {message}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"✗ {message}"))
                else:
                    self.stdout.write(
                        self.style.WARNING(f"{username} has no missing predictions in next 24h")
                    )

            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User '{username}' not found"))

        else:
            self.stdout.write(
                self.style.WARNING("Specify --leaderboard or --reminder=USERNAME to test email")
            )
