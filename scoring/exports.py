"""
Export utilities for leaderboard data.

Provides functions to generate CSV and PDF exports of the leaderboard,
usable from management commands, views, or admin actions.
"""

import csv
from io import BytesIO, StringIO
from typing import TYPE_CHECKING

from django.http import HttpResponse

if TYPE_CHECKING:
    pass


def generate_leaderboard_csv(leaderboard: list[dict]) -> str:
    """
    Generate CSV content from leaderboard data.

    Args:
        leaderboard: List of dicts from RankingService.get_current_leaderboard()

    Returns:
        CSV content as string
    """
    output = StringIO()
    fieldnames = [
        "rank",
        "username",
        "total_points",
        "exact_match_count",
        "jokers_used",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(leaderboard)

    return output.getvalue()


def generate_leaderboard_pdf(leaderboard: list[dict], title: str = "WM 2026 Leaderboard") -> bytes:
    """
    Generate PDF content from leaderboard data.

    Args:
        leaderboard: List of dicts from RankingService.get_current_leaderboard()
        title: Title for the PDF document

    Returns:
        PDF content as bytes

    Raises:
        ImportError: If reportlab is not installed
    """
    try:
        from reportlab.lib import colors  # type: ignore
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
        from reportlab.lib.units import cm  # type: ignore
        from reportlab.platypus import (  # type: ignore
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as e:
        raise ImportError(
            "PDF export requires reportlab. Install with: pip install reportlab"
        ) from e

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(title, styles["Heading1"]))
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

    return output.getvalue()


def csv_response(leaderboard: list[dict], filename: str = "leaderboard.csv") -> HttpResponse:
    """
    Create an HttpResponse with CSV content for download.

    Args:
        leaderboard: List of dicts from RankingService.get_current_leaderboard()
        filename: Name of the downloaded file

    Returns:
        HttpResponse with CSV content
    """
    content = generate_leaderboard_csv(leaderboard)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def pdf_response(leaderboard: list[dict], filename: str = "leaderboard.pdf") -> HttpResponse:
    """
    Create an HttpResponse with PDF content for download.

    Args:
        leaderboard: List of dicts from RankingService.get_current_leaderboard()
        filename: Name of the downloaded file

    Returns:
        HttpResponse with PDF content
    """
    content = generate_leaderboard_pdf(leaderboard)
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
