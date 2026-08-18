"""
Management command to create a leaderboard snapshot.

Creates a point-in-time snapshot of the current leaderboard
for historical tracking and trend analysis.
"""

from django.core.management.base import BaseCommand, CommandError

from scoring.ranking_service import RankingService


class Command(BaseCommand):
    help = "Create a snapshot of the current leaderboard"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "snapshot_type",
            choices=["daily", "final"],
            help="Type of snapshot to create (daily or final)",
        )

    def handle(self, *args, **options) -> None:
        snapshot_type = options["snapshot_type"]

        self.stdout.write(f"Creating {snapshot_type} snapshot...")

        try:
            snapshot = RankingService.create_snapshot(snapshot_type)
        except Exception as e:
            raise CommandError(f"Failed to create snapshot: {e}") from e

        entries = len(snapshot.data) if snapshot.data else 0

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {snapshot_type} snapshot with {entries} entries "
                f"(ID: {snapshot.pk})"
            )
        )
