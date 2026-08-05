"""
Views for the scoring app.

Provides views for staff-only leaderboard exports.
"""

from datetime import date

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View

from scoring.exports import csv_response
from scoring.services import RankingService


@method_decorator(staff_member_required, name="dispatch")
class DownloadLeaderboardView(View):
    """
    Staff-only view for on-demand leaderboard CSV download.

    Supports both summary and detailed exports via query parameter.
    
    Query params:
        detailed: If "true", include per-match prediction details
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Generate and return leaderboard CSV."""
        leaderboard = RankingService.get_current_leaderboard()
        detailed = request.GET.get("detailed", "").lower() == "true"
        
        today = date.today().isoformat()
        suffix = "_detailed" if detailed else ""
        filename = f"leaderboard{suffix}_{today}.csv"
        
        return csv_response(leaderboard, filename=filename, detailed=detailed)
