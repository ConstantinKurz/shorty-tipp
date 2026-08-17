"""
Management command to recalculate all scores from scratch.

Resets all user statistics and prediction scores, then iterates
through all finished matches to recalculate. Useful after rule
changes or to fix inconsistencies.
"""

from django.core.management.base import BaseCommand

from matches.models import Match
from predictions.models import MatchPrediction
from scoring.services import ScoringService
from users.models import User


class Command(BaseCommand):
    help = "Recalculate all scores from scratch"

    def handle(self, *args, **options) -> None:
        self.stdout.write("Resetting all statistics...")

        # Reset user statistics
        user_count = User.objects.update(
            total_points=0,
            exact_match_count=0,
            jokers_used=0,
        )
        self.stdout.write(f"  Reset {user_count} users")

        # Reset prediction scores
        prediction_count = MatchPrediction.objects.update(
            points_earned=None,
            is_exact_match=False,
        )
        self.stdout.write(f"  Reset {prediction_count} predictions")

        # Get finished matches ordered by kickoff
        finished_matches = Match.objects.filter(
            status="finished",
            goals_home__isnull=False,
            goals_away__isnull=False,
        ).order_by("kickoff")

        self.stdout.write(f"\nScoring {finished_matches.count()} finished matches...")

        total_scored = 0
        for match in finished_matches:
            scored = ScoringService.score_all_predictions_for_match(match)
            total_scored += scored
            self.stdout.write(f"  {match}: {scored} predictions")

        # Update champion bonuses if applicable
        champion_count = ScoringService.update_live_champion_bonuses()
        if champion_count > 0:
            self.stdout.write(f"\nAwarded champion points to {champion_count} users")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! Scored {total_scored} predictions across "
                f"{finished_matches.count()} matches."
            )
        )
