"""Management command to sync teams from football-data.org API."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from matches.api_client import FootballDataAPIError
from matches.services import sync_teams_from_api


class Command(BaseCommand):
    """Sync teams from football-data.org API to the database."""

    help = "Sync teams from football-data.org API"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--competition",
            type=str,
            default="WC",
            help="Competition code (default: WC for World Cup)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        competition = options["competition"]

        self.stdout.write(f"Syncing teams for competition: {competition}")

        try:
            created, updated = sync_teams_from_api(competition)

            self.stdout.write(
                self.style.SUCCESS(f"✓ Team sync complete: {created} created, {updated} updated")
            )

        except FootballDataAPIError as e:
            raise CommandError(f"API error: {e}") from e
        except Exception as e:
            raise CommandError(f"Unexpected error: {e}") from e
