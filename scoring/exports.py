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


def generate_leaderboard_pdf(
    leaderboard: list[dict], title: str = "Shortytipp Leaderboard"
) -> bytes:
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


def csv_response(
    leaderboard: list[dict],
    filename: str = "leaderboard.csv",
    detailed: bool = False,
) -> HttpResponse:
    """
    Create an HttpResponse with CSV content for download.

    Args:
        leaderboard: List of dicts from RankingService.get_current_leaderboard()
        filename: Name of the downloaded file
        detailed: If True, include per-match prediction details

    Returns:
        HttpResponse with CSV content
    """
    if detailed:
        content = generate_detailed_leaderboard_csv(leaderboard)
    else:
        content = generate_leaderboard_csv(leaderboard)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def generate_detailed_leaderboard_csv(leaderboard: list[dict]) -> str:
    """
    Generate detailed CSV with leaderboard followed by predictions grouped by user.

    Format:
    - Section 1: Full leaderboard rankings
    - Section 2: For each user, their predictions in chronological order

    Args:
        leaderboard: List of dicts from RankingService.get_current_leaderboard()

    Returns:
        CSV content as string, formatted for readability
    """
    from matches.models import Match
    from predictions.models import MatchPrediction

    output = StringIO()
    writer = csv.writer(output)

    # ========== SECTION 1: LEADERBOARD ==========
    writer.writerow(["=" * 60])
    writer.writerow(["LEADERBOARD"])
    writer.writerow(["=" * 60])
    writer.writerow([])
    writer.writerow(["Rank", "Player", "Total Points", "Exact Matches", "Jokers Used"])

    for entry in leaderboard:
        writer.writerow(
            [
                entry["rank"],
                entry["username"],
                entry["total_points"],
                entry["exact_match_count"],
                entry["jokers_used"],
            ]
        )

    writer.writerow([])
    writer.writerow([])

    # ========== SECTION 2: PREDICTIONS BY USER ==========
    writer.writerow(["=" * 60])
    writer.writerow(["PREDICTIONS BY PLAYER"])
    writer.writerow(["=" * 60])

    # Get all finished matches ordered by kickoff
    matches = (
        Match.objects.filter(status="finished")
        .select_related("team_home", "team_away")
        .order_by("kickoff")
    )

    # Get all user_ids from leaderboard
    user_ids = [entry["user_id"] for entry in leaderboard]

    # Pre-fetch all predictions for these users
    predictions_by_user: dict[int, dict[int, MatchPrediction]] = {}
    predictions = MatchPrediction.objects.filter(user_id__in=user_ids).select_related("match")

    for pred in predictions:
        if pred.user_id not in predictions_by_user:
            predictions_by_user[pred.user_id] = {}
        predictions_by_user[pred.user_id][pred.match_id] = pred

    # Generate predictions for each user
    for entry in leaderboard:
        user_id = entry["user_id"]
        user_predictions = predictions_by_user.get(user_id, {})

        writer.writerow([])
        writer.writerow(["-" * 50])
        writer.writerow(
            [f"Player: {entry['username']} (Rank #{entry['rank']}, {entry['total_points']} points)"]
        )
        writer.writerow(["-" * 50])
        writer.writerow(
            ["Date", "Round", "Match", "Result", "Prediction", "Points", "Exact?", "Joker?"]
        )

        for match in matches:
            pred = user_predictions.get(match.pk)

            match_date = match.kickoff.strftime("%Y-%m-%d") if match.kickoff else ""
            match_str = f"{match.team_home.name if match.team_home else '?'} vs {match.team_away.name if match.team_away else '?'}"
            result_str = (
                f"{match.goals_home}-{match.goals_away}" if match.goals_home is not None else ""
            )

            if pred:
                pred_str = f"{pred.predicted_goals_home}-{pred.predicted_goals_away}"
                points = pred.points_earned if pred.points_earned is not None else "-"
                exact = "Yes" if pred.is_exact_match else "No"
                joker = "Yes" if pred.joker_active else "No"
            else:
                pred_str = "No prediction"
                points = "0"
                exact = ""
                joker = ""

            writer.writerow(
                [
                    match_date,
                    match.round,
                    match_str,
                    result_str,
                    pred_str,
                    points,
                    exact,
                    joker,
                ]
            )

    return output.getvalue()


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
