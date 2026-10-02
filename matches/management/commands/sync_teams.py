"""Management command to sync teams from football-data.org API."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from matches.api_client import FootballDataAPIError
from matches.models import Tournament
from matches.services import sync_teams_from_api
from matches.tournament import NoActiveTournamentError, get_active_tournament


class Command(BaseCommand):
    """Sync teams from football-data.org API to the database."""

    help = "Sync teams from football-data.org API"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--tournament",
            type=str,
            default=None,
            help="Slug of the tournament to sync (default: the active tournament)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        slug = options["tournament"]

        try:
            tournament = Tournament.objects.get(slug=slug) if slug else get_active_tournament()
        except Tournament.DoesNotExist as e:
            raise CommandError(f"No tournament with slug '{slug}'.") from e
        except NoActiveTournamentError as e:
            raise CommandError(str(e)) from e

        self.stdout.write(
            f"Syncing teams for {tournament.name} (competition: {tournament.api_competition_code})"
        )

        try:
            created, updated, unchanged = sync_teams_from_api(tournament)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Team sync complete: {created} created, {updated} updated, "
                    f"{unchanged} unchanged"
                )
            )

        except FootballDataAPIError as e:
            raise CommandError(f"API error: {e}") from e
