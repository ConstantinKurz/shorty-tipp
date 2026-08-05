"""URL configuration for users app."""

from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("rules/", views.RulesView.as_view(), name="rules"),
    path("settings/", views.UserSettingsView.as_view(), name="settings"),
]
