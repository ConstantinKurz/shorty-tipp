"""URL configuration for predictions app."""

from django.urls import path

from predictions.views import (
    PredictionDeleteView,
    PredictionJokerView,
    PredictionListView,
    PredictionSaveView,
    PredictionUpdatesView,
)

app_name = "predictions"

urlpatterns = [
    path("", PredictionListView.as_view(), name="prediction-list"),
    path("updates/", PredictionUpdatesView.as_view(), name="prediction-updates"),
    path("<int:match_id>/save/", PredictionSaveView.as_view(), name="prediction-save"),
    path("<int:match_id>/delete/", PredictionDeleteView.as_view(), name="prediction-delete"),
    path("<int:match_id>/joker/", PredictionJokerView.as_view(), name="prediction-joker"),
]
