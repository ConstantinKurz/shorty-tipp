"""
Management command to detect and repair matches whose predictions were never scored.

A match that has both goals set but still has predictions with ``points_earned IS NULL``
was left unscored, e.g. because a scoring run failed. This command finds those matches
and re-runs scoring for them. Scoring and champion bonuses are idempotent, so running the
command on a healthy database changes nothing.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from django.db.models import Exists, OuterRef, QuerySet

from matches.models import Match
from predictions.models import MatchPrediction
from scoring.champion_scoring import update_live_champion_bonuses
from scoring.match_scoring import ScoringService
from scoring.ranking_service import RankingService


def find_unscored_matches() -> QuerySet[Match]:
    """
    Find matches that have a result but at least one unscored prediction.

    Returns:
        Matches with both goals set and predictions without points_earned,
        ordered by kickoff. Matches without predictions are never returned.
    """
    # Exists() instead of a join filter: an ``isnull=True`` join would promote to a
    # LEFT JOIN and also match matches that have no predictions at all.
    unscored_predictions = MatchPrediction.objects.filter(
        match=OuterRef("pk"),
        points_earned__isnull=True,
    )

    return (
        Match.objects.filter(
            goals_home__isnull=False,
            goals_away__isnull=False,
        )
        .filter(Exists(unscored_predictions))
        .order_by("kickoff")
    )


class Command(BaseCommand):
    help = "Detect and repair matches whose predictions were never scored"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--check",
            action="store_true",
            help="Only report matches that need repair, do not write anything",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        matches = list(find_unscored_matches().select_related("team_home", "team_away"))

        if not matches:
            self.stdout.write(self.style.SUCCESS("No matches need scoring repair."))
            return

        self.stdout.write(f"{len(matches)} match(es) need scoring repair:")
        for match in matches:
            self.stdout.write(f"  [{match.pk}] {match}")

        if options["check"]:
            raise CommandError(f"{len(matches)} match(es) need scoring repair.")

        repaired = 0
        failures: list[int] = []
        final_affected = False

        for match in matches:
            try:
                scored = ScoringService.score_all_predictions_for_match(match)
            except (ValueError, TypeError, KeyError, ValidationError, DatabaseError) as exc:
                failures.append(match.pk)
                self.stderr.write(self.style.ERROR(f"  [{match.pk}] repair failed: {exc}"))
                continue

            repaired += 1
            final_affected = final_affected or match.round == "final"
            self.stdout.write(f"  [{match.pk}] scored {scored} prediction(s)")

        if final_affected:
            bonus_count = update_live_champion_bonuses()
            self.stdout.write(f"Updated champion bonuses for {bonus_count} user(s)")

        rank_count = RankingService.update_all_user_ranks()
        self.stdout.write(f"Updated global ranks for {rank_count} user(s)")

        if failures:
            raise CommandError(f"Repaired {repaired} match(es), {len(failures)} failed: {failures}")

        self.stdout.write(self.style.SUCCESS(f"Repaired {repaired} match(es)."))
