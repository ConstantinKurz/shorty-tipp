"""Management command to seed global ranks for all active users."""

from django.core.management.base import BaseCommand

from scoring.ranking_service import RankingService


class Command(BaseCommand):
    """Calculate and store global ranks for all active users."""

    help = "Calculate and store global ranks for all active users"

    def handle(self, *args, **options):
        self.stdout.write("Calculating global ranks...")

        count = RankingService.update_all_user_ranks()

        self.stdout.write(
            self.style.SUCCESS(f"Updated global ranks for {count} users")
        )
