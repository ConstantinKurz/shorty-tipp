"""
URL configuration for the scoring app.
"""

from django.urls import path

from scoring.views import DownloadLeaderboardView
from tipapp.views import RankingUpdatesView

app_name = "scoring"

urlpatterns = [
    path("ranking-updates/", RankingUpdatesView.as_view(), name="ranking-updates"),
    path(
        "admin/download-leaderboard/",
        DownloadLeaderboardView.as_view(),
        name="download-leaderboard",
    ),
]
