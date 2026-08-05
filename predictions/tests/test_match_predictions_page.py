"""
Integration tests for the dedicated all-tips page.

Tests navigation flow, origin parameter handling, sort parameter persistence,
and template rendering for the MatchPredictionsView full page.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from matches.models import Match, Team
from predictions.models import MatchPrediction


@pytest.fixture
def teams(db):
    """Create test teams."""
    return [
        Team.objects.create(name="Team A", fifa_code="TEA"),
        Team.objects.create(name="Team B", fifa_code="TEB"),
    ]


@pytest.fixture
def test_match(teams, db):
    """Create a test match."""
    return Match.objects.create(
        team_home=teams[0],
        team_away=teams[1],
        kickoff=timezone.now() + timedelta(days=1),
        round="group",
    )


@pytest.fixture
def past_match(teams, db):
    """Create a past match with a result."""
    return Match.objects.create(
        team_home=teams[0],
        team_away=teams[1],
        kickoff=timezone.now() - timedelta(days=1),
        round="group",
        status="finished",
        goals_home=2,
        goals_away=1,
    )


class TestMatchPredictionsPageNavigation:
    """Tests for origin parameter and back navigation."""

    def test_anonymous_user_redirected(self, client, test_match):
        """Anonymous users should be redirected to login."""
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_authenticated_user_can_access(self, client, regular_user, test_match):
        """Authenticated users should be able to access the page."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)
        assert response.status_code == 200

    def test_invalid_match_returns_404(self, client, regular_user):
        """Non-existent match should return 404."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[99999])
        response = client.get(url)
        assert response.status_code == 404

    def test_origin_predictions_renders_correctly(self, client, regular_user, test_match):
        """Page should render with origin=predictions in context."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url + "?from=predictions")

        assert response.status_code == 200
        assert response.context["origin"] == "predictions"

    def test_origin_home_renders_correctly(self, client, regular_user, test_match):
        """Page should render with origin=home in context."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url + "?from=home")

        assert response.status_code == 200
        assert response.context["origin"] == "home"

    def test_back_button_uses_history_back(self, client, regular_user, test_match):
        """Back button should use history.back() for proper scroll position restoration."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        content = response.content.decode()
        assert "history.back()" in content
        assert "Zurück" in content

    def test_invalid_origin_defaults_to_predictions(self, client, regular_user, test_match):
        """Invalid origin parameter should default to predictions."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])

        # Test various invalid origins
        for invalid_origin in ["invalid", "ranking", "", "12345"]:
            response = client.get(url + f"?from={invalid_origin}")
            assert response.context["origin"] == "predictions"

    def test_missing_origin_defaults_to_predictions(self, client, regular_user, test_match):
        """Missing origin parameter should default to predictions."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        assert response.context["origin"] == "predictions"


class TestMatchPredictionsPageSorting:
    """Tests for sort parameter handling."""

    def test_sort_toggle_preserves_origin(self, client, regular_user, test_match):
        """Sort toggle links should preserve the origin parameter."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url + "?from=home&sort=match")

        content = response.content.decode()
        # Both sort links should include from=home
        assert "sort=match&amp;from=home" in content or "sort=match&from=home" in content
        assert "sort=total&amp;from=home" in content or "sort=total&from=home" in content

    def test_invalid_sort_defaults_to_match(self, client, regular_user, test_match):
        """Invalid sort parameter should default to match."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])

        for invalid_sort in ["invalid", "points", "", "12345"]:
            response = client.get(url + f"?sort={invalid_sort}")
            assert response.context["sort_mode"] == "match"

    def test_missing_sort_defaults_to_match(self, client, regular_user, test_match):
        """Missing sort parameter should default to match."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        assert response.context["sort_mode"] == "match"

    def test_sort_total_sets_context(self, client, regular_user, test_match):
        """sort=total should set sort_mode to total in context."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url + "?sort=total")

        assert response.context["sort_mode"] == "total"


class TestMatchPredictionsPageTemplate:
    """Tests for template content and structure."""

    def test_template_contains_required_elements(self, client, regular_user, test_match):
        """Template should contain header, match info, and predictions list."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        content = response.content.decode()

        # Header with back button (SVG arrow + text)
        assert "history.back()" in content
        assert "Zurück" in content

        # Page title
        assert "Alle Tipps" in content

        # Match info
        assert test_match.team_home.name in content
        assert test_match.team_away.name in content

        # Sort toggle
        assert "Spielpunkte" in content
        assert "Gesamtpunkte" in content

    def test_template_shows_match_result_when_available(self, client, regular_user, past_match):
        """Template should show match result when goals are set."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url)

        content = response.content.decode()
        # Result should be displayed (2:1)
        assert "2" in content
        assert "1" in content

    def test_template_shows_pending_result_for_future_match(self, client, regular_user, test_match):
        """Template should show - : - for matches without results."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        content = response.content.decode()
        assert "- : -" in content

    def test_current_user_highlighted(self, client, regular_user, test_match):
        """Current user's prediction should be highlighted."""
        MatchPrediction.objects.create(
            user=regular_user,
            match=test_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        content = response.content.decode()
        # Check for highlight class
        assert "bg-emerald-50" in content or "bg-emerald-900" in content

    def test_empty_state_message(self, client, regular_user, test_match):
        """Should show empty state when user has no prediction."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        content = response.content.decode()
        assert "Kein Tipp" in content

    def test_context_contains_all_required_keys(self, client, regular_user, test_match):
        """Context should contain all required keys for template rendering."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        context = response.context
        assert "match" in context
        assert "user_predictions" in context
        assert "sort_mode" in context
        assert "origin" in context
        assert "current_user" in context

    def test_user_predictions_list_structure(self, client, regular_user, test_match):
        """User predictions list should have correct structure."""
        MatchPrediction.objects.create(
            user=regular_user,
            match=test_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        user_predictions = response.context["user_predictions"]
        assert len(user_predictions) > 0

        # Check structure of first entry
        entry = user_predictions[0]
        assert "user" in entry
        assert "rank" in entry
        assert "has_predicted" in entry
        assert "total_points" in entry
        assert "exact_count" in entry
        assert "jokers_count" in entry
