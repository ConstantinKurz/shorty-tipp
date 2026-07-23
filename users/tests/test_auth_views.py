"""
Tests for authentication views and templates.

Tests login, logout functionality and template rendering.
"""

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse


@pytest.fixture
def test_user(db):
    """Create a test user for authentication tests."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="authuser",
        email="authuser@test.com",
        password="testpass123",
    )


@pytest.fixture
def client():
    """Provide a Django test client."""
    return Client()


@pytest.mark.django_db
class TestLoginView:
    """Tests for the login view and template."""

    def test_login_page_returns_200(self, client):
        """GET /login/ should return HTTP 200."""
        response = client.get(reverse("login"))
        assert response.status_code == 200

    def test_login_page_uses_correct_template(self, client):
        """GET /login/ should use login.html template."""
        response = client.get(reverse("login"))
        assert "login.html" in [t.name for t in response.templates]

    def test_login_page_contains_username_input(self, client):
        """Login page should contain username input field."""
        response = client.get(reverse("login"))
        content = response.content.decode()
        assert 'name="username"' in content
        assert 'id="id_username"' in content

    def test_login_page_contains_password_input(self, client):
        """Login page should contain password input field."""
        response = client.get(reverse("login"))
        content = response.content.decode()
        assert 'name="password"' in content
        assert 'id="id_password"' in content

    def test_login_page_contains_csrf_token(self, client):
        """Login page should contain CSRF token."""
        response = client.get(reverse("login"))
        content = response.content.decode()
        assert "csrfmiddlewaretoken" in content

    def test_login_page_contains_dark_mode_toggle(self, client):
        """Login page should contain dark mode toggle element."""
        response = client.get(reverse("login"))
        content = response.content.decode()
        assert 'id="dark-mode-toggle"' in content

    def test_login_with_valid_credentials_redirects(self, client, test_user):
        """POST /login/ with valid credentials should redirect to LOGIN_REDIRECT_URL."""
        response = client.post(
            reverse("login"),
            {"username": "authuser", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == settings.LOGIN_REDIRECT_URL

    def test_login_with_valid_credentials_authenticates_user(self, client, test_user):
        """POST /login/ with valid credentials should authenticate the user."""
        client.post(
            reverse("login"),
            {"username": "authuser", "password": "testpass123"},
        )
        # Check session contains user
        assert "_auth_user_id" in client.session

    def test_login_with_invalid_credentials_returns_200(self, client, test_user):
        """POST /login/ with invalid credentials should stay on login page (200)."""
        response = client.post(
            reverse("login"),
            {"username": "authuser", "password": "wrongpassword"},
        )
        assert response.status_code == 200

    def test_login_with_invalid_credentials_shows_error(self, client, test_user):
        """POST /login/ with invalid credentials should display error message."""
        response = client.post(
            reverse("login"),
            {"username": "authuser", "password": "wrongpassword"},
        )
        content = response.content.decode()
        # Django's default error message for invalid login
        assert (
            "Please enter a correct username and password" in content
            or "Bitte" in content  # In case of localization
            or "non_field_errors" in str(response.context.get("form", {}).errors)
            or response.context["form"].non_field_errors()
        )

    def test_login_with_nonexistent_user_returns_200(self, client, db):
        """POST /login/ with nonexistent user should stay on login page."""
        response = client.post(
            reverse("login"),
            {"username": "doesnotexist", "password": "anypassword"},
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestLogoutView:
    """Tests for the logout view."""

    def test_logout_redirects_to_logout_redirect_url(self, client, test_user):
        """POST /logout/ should redirect to LOGOUT_REDIRECT_URL."""
        # Login first
        client.login(username="authuser", password="testpass123")

        response = client.post(reverse("logout"))
        assert response.status_code == 302
        assert response.url == settings.LOGOUT_REDIRECT_URL

    def test_logout_logs_user_out(self, client, test_user):
        """POST /logout/ should log out the authenticated user."""
        # Login first
        client.login(username="authuser", password="testpass123")
        assert "_auth_user_id" in client.session

        client.post(reverse("logout"))
        # Session should not contain user after logout
        assert "_auth_user_id" not in client.session

    def test_logout_when_not_authenticated_redirects(self, client, db):
        """POST /logout/ when not authenticated should still redirect."""
        response = client.post(reverse("logout"))
        assert response.status_code == 302


@pytest.mark.django_db
class TestBaseTemplate:
    """Tests for base template elements."""

    def test_base_template_dark_mode_toggle_present(self, client):
        """Base template should include dark mode toggle functionality."""
        response = client.get(reverse("login"))
        content = response.content.decode()
        # Check for toggle button
        assert "toggleDarkMode" in content
        # Check for localStorage usage
        assert "localStorage" in content

    def test_base_template_tailwind_cdn_included(self, client):
        """Base template should include Tailwind CSS CDN."""
        response = client.get(reverse("login"))
        content = response.content.decode()
        assert "cdn.tailwindcss.com" in content
