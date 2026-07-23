"""
Management command to export the current leaderboard.

Exports the leaderboard to CSV or PDF format.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from scoring.services import RankingService


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
                    "Cannot determine format from extension. "
                    "Use --format csv or --format pdf"
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
            self.style.SUCCESS(
                f"Exported {len(leaderboard)} entries to {output_path}"
            )
        )

    def _export_csv(self, leaderboard: list[dict], output_path: Path) -> None:
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

    def _export_pdf(self, leaderboard: list[dict], output_path: Path) -> None:
        """Export leaderboard to PDF format using ReportLab."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError as e:
            raise CommandError(
                "PDF export requires reportlab. Install with: pip install reportlab"
            ) from e

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph("WM 2026 Leaderboard", styles["Heading1"]))
        elements.append(Spacer(1, 12))

        # Table data
        table_data = [
            ["Rank", "Player", "Points", "Exact", "Jokers"],
        ]
        for entry in leaderboard:
            table_data.append(
                [
                    str(entry["rank"]),
                    entry["username"],
                    str(entry["total_points"]),
                    str(entry["exact_match_count"]),
                    str(entry["jokers_used"]),
                ]
            )

        table = Table(table_data, colWidths=[2 * cm, 6 * cm, 3 * cm, 2 * cm, 2 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ALIGN", (1, 1), (1, -1), "LEFT"),
                ]
            )
        )

        elements.append(table)
        doc.build(elements)
