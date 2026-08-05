"""
URL configuration for the scoring app.
"""

from django.urls import path

from scoring.views import RankingUpdatesView

app_name = "scoring"

urlpatterns = [
    path("ranking-updates/", RankingUpdatesView.as_view(), name="ranking-updates"),
]
