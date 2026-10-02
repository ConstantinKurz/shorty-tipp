"""
Management command to recalculate all scores from scratch.

Resets all user statistics and prediction scores, then iterates
through all finished matches to recalculate. Useful after rule
changes or to fix inconsistencies.
"""

from django.core.management.base import BaseCommand

from scoring.match_scoring import recalculate_all_scores


class Command(BaseCommand):
    help = "Recalculate all scores from scratch"

    def handle(self, *args, **options) -> None:
        self.stdout.write("Resetting all statistics and re-scoring finished matches...")

        total_scored = recalculate_all_scores()

        self.stdout.write(self.style.SUCCESS(f"\nDone! Scored {total_scored} predictions."))
