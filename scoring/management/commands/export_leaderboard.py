"""
Management command to export the current leaderboard.

Exports the leaderboard to CSV or PDF format.
"""

import csv
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from scoring.exports import generate_leaderboard_pdf
from scoring.ranking_service import RankingService


class Command(BaseCommand):
    help = "Export the current leaderboard to CSV or PDF"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "output_path",
            help="Output file path (use .csv or .pdf extension)",
        )
        parser.add_argument(
            "--format",
            choices=["csv", "pdf"],
            help="Output format (defaults to extension-based detection)",
        )

    def handle(self, *args, **options) -> None:
        output_path = Path(options["output_path"])
        output_format = options.get("format")

        # Auto-detect format from extension if not specified
        if not output_format:
            if output_path.suffix.lower() == ".csv":
                output_format = "csv"
            elif output_path.suffix.lower() == ".pdf":
                output_format = "pdf"
            else:
                raise CommandError(
                    "Cannot determine format from extension. Use --format csv or --format pdf"
                )

        self.stdout.write(f"Generating {output_format.upper()} leaderboard...")

        leaderboard = RankingService.get_current_leaderboard()

        if not leaderboard:
            raise CommandError("Leaderboard is empty - nothing to export")

        if output_format == "csv":
            self._export_csv(leaderboard, output_path)
        else:
            self._export_pdf(leaderboard, output_path)

        self.stdout.write(
            self.style.SUCCESS(f"Exported {len(leaderboard)} entries to {output_path}")
        )

    def _export_csv(self, leaderboard: list[dict[str, Any]], output_path: Path) -> None:
        """Export leaderboard to CSV format."""
        fieldnames = [
            "rank",
            "username",
            "total_points",
            "exact_match_count",
            "jokers_used",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(leaderboard)

    def _export_pdf(self, leaderboard: list[dict[str, Any]], output_path: Path) -> None:
        """Export leaderboard to PDF format using ReportLab."""
        output_path.write_bytes(generate_leaderboard_pdf(leaderboard))
