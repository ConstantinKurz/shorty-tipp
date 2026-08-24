"""Management command to continuously update matches from football-data.org API."""

from __future__ import annotations

import logging
import signal
import time
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import Match
from matches.services import sync_matches_from_api

logger = logging.getLogger(__name__)

# Active window for frequent polling
ACTIVE_WINDOW_BEFORE = timedelta(minutes=30)
ACTIVE_WINDOW_AFTER = timedelta(hours=3)


class Command(BaseCommand):
    """Continuously update matches from football-data.org API."""

    help = "Run continuous match updater that syncs from football-data.org API"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.running = True

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run once and exit (for testing)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        once = options["once"]

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        self.stdout.write(self.style.SUCCESS("Starting match updater..."))

        while self.running:
            try:
                # Record iteration start time
                iteration_time = timezone.now()
                
                # Sync matches from API
                # Note: sync_matches_from_api() calls match.save() which triggers
                # the match_result_entered signal, automatically scoring predictions
                # and updating champion bonuses via signal receivers
                results = sync_matches_from_api()

                # Track matches with goal changes for logging
                matches_with_changes = []
                for result in results:
                    if result.goals_changed:
                        matches_with_changes.append(result.match)
                        # Scoring happens automatically via signal - no manual call needed!

                # Calculate adaptive sleep interval
                interval = self._calculate_sleep_interval()

                # Log iteration summary with timestamp
                timestamp = iteration_time.strftime("%Y-%m-%d %H:%M:%S")
                self.stdout.write(
                    f"[{timestamp}] Synced {len(results)} matches, "
                    f"{len(matches_with_changes)} with goal changes. "
                    f"Next check in {interval}s."
                )
                
                # Log details of changed matches
                if matches_with_changes:
                    self.stdout.write(self.style.WARNING("  Matches with goal changes:"))
                    for match in matches_with_changes:
                        self.stdout.write(f"    • {match}")
                    self.stdout.write(
                        self.style.SUCCESS(
                            "  ✓ Predictions scored automatically via signals"
                        )
                    )
                # Exit if --once flag
                if once:
                    self.stdout.write(self.style.SUCCESS("✓ Single iteration complete"))
                    break

                # Sleep until next iteration
                time.sleep(interval)

            except KeyboardInterrupt:
                self.stdout.write("\nReceived interrupt signal")
                break

            except Exception as e:
                logger.exception("Update iteration failed: %s", e)
                self.stdout.write(
                    self.style.ERROR(f"Error: {e}. Retrying in 60 seconds...")
                )
                if once:
                    raise  # Re-raise in test mode
                time.sleep(60)

        self.stdout.write(self.style.SUCCESS("Match updater stopped"))

    def _shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received signal %d, shutting down gracefully...", signum)
        self.stdout.write("\nShutting down gracefully...")
        self.running = False

    def _calculate_sleep_interval(self) -> int:
        """
        Calculate adaptive polling interval based on match schedule.

        Returns:
            Sleep interval in seconds
        """
        now = timezone.now()

        # Check for live matches - poll very frequently
        if Match.objects.filter(status="live").exists():
            return 10  # 10 seconds for live matches

        # Check for matches in active window (kickoff passed but not finished yet)
        # This catches matches where kickoff has passed but API still reports "scheduled"
        active_window_start = now - ACTIVE_WINDOW_AFTER
        active_window_end = now + ACTIVE_WINDOW_BEFORE

        has_active_window_match = Match.objects.filter(
            kickoff__gte=active_window_start,
            kickoff__lte=active_window_end,
            status__in=["scheduled", "live"],
        ).exists()

        if has_active_window_match:
            return 30  # Poll frequently during active window

        # Find next upcoming match
        next_match = (
            Match.objects.filter(kickoff__gt=now, status="scheduled")
            .order_by("kickoff")
            .first()
        )

        if not next_match:
            return 1800  # 30 minutes - no upcoming matches

        # Calculate time until next match
        time_until = (next_match.kickoff - now).total_seconds()

        if time_until < 1800:  # < 30 minutes
            return 60  # 1 minute
        elif time_until < 7200:  # < 2 hours
            return 300  # 5 minutes
        else:
            return 600  # 10 minutes
