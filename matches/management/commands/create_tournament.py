"""Management command to create a tournament, optionally from a preset."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from matches.presets import TOURNAMENT_PRESETS
from matches.tournament import UnknownPresetError, create_tournament


class Command(BaseCommand):
    """Create a tournament and its rounds from a preset."""

    help = "Create a tournament, optionally from a round preset"

    def add_arguments(self, parser: Any) -> None:
        """Add command arguments."""
        parser.add_argument("--name", type=str, required=True, help="Tournament name")
        parser.add_argument("--slug", type=str, required=True, help="Unique short identifier")
        parser.add_argument(
            "--competition",
            type=str,
            required=True,
            help="football-data.org competition code (e.g., WC, EC)",
        )
        parser.add_argument(
            "--season", type=int, default=None, help="football-data.org season year"
        )
        parser.add_argument(
            "--preset",
            type=str,
            default=None,
            choices=sorted(TOURNAMENT_PRESETS),
            help="Round preset; omit to create a tournament without rounds",
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Make this the active tournament, deactivating the previous one",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        try:
            tournament = create_tournament(
                name=options["name"],
                slug=options["slug"],
                api_competition_code=options["competition"],
                api_season=options["season"],
                preset=options["preset"],
                activate=options["activate"],
            )
        except UnknownPresetError as e:
            raise CommandError(str(e)) from e
        except IntegrityError as e:
            raise CommandError(f"Could not create tournament: {e}") from e

        round_count = tournament.rounds.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Created tournament '{tournament.name}' with {round_count} round(s)"
                f"{' and activated it' if tournament.is_active else ''}."
            )
        )
