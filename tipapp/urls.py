"""
tipapp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from users.views import RankingView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("ranking/", RankingView.as_view(), name="ranking"),
    path("predictions/", include("predictions.urls")),
]
