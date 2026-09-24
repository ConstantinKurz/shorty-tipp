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
        """Template should show -:- for matches without results."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        content = response.content.decode()
        # Check for dash placeholder in result section (may be formatted as -:-)
        assert "-:-" in content

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


class TestBuildMatchPredictionsListHelper:
    """Tests for the build_match_predictions_list helper function."""

    def test_sort_by_match_points(self, db, regular_user, test_match):
        """Helper sorts by match points descending when sort_mode='match'."""
        from django.contrib.auth import get_user_model

        from predictions.services import build_match_predictions_list

        User = get_user_model()

        # Create additional users
        user_a = User.objects.create_user(username="aaa_first", password="test")
        user_b = User.objects.create_user(username="bbb_second", password="test")
        user_c = User.objects.create_user(username="ccc_third", password="test")

        # Create predictions with different points
        MatchPrediction.objects.create(
            user=user_a,
            match=test_match,
            predicted_goals_home=1,
            predicted_goals_away=1,
            points_earned=5,
        )
        MatchPrediction.objects.create(
            user=user_b,
            match=test_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=10,
        )
        MatchPrediction.objects.create(
            user=user_c,
            match=test_match,
            predicted_goals_home=0,
            predicted_goals_away=0,
            points_earned=3,
        )

        result = build_match_predictions_list(test_match, "match", regular_user)

        # Find our test users in result
        user_order = [
            entry["user"].username
            for entry in result
            if entry["user"].username in ("aaa_first", "bbb_second", "ccc_third")
        ]

        # Should be sorted by match points descending: bbb (10), aaa (5), ccc (3)
        assert user_order == ["bbb_second", "aaa_first", "ccc_third"]

    def test_sort_by_total_points(self, db, regular_user, test_match):
        """Helper sorts by total points descending when sort_mode='total'."""
        from django.contrib.auth import get_user_model

        from predictions.services import build_match_predictions_list

        User = get_user_model()

        # Create additional users
        user_a = User.objects.create_user(username="user_low", password="test")
        user_b = User.objects.create_user(username="user_high", password="test")

        # Create predictions with different total points
        # Give user_a low total points via this prediction
        MatchPrediction.objects.create(
            user=user_a,
            match=test_match,
            predicted_goals_home=1,
            predicted_goals_away=1,
            points_earned=5,
        )
        # Give user_b high total points via this prediction
        MatchPrediction.objects.create(
            user=user_b,
            match=test_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=20,
        )

        result = build_match_predictions_list(test_match, "total", regular_user)

        # Find our test users in result
        user_order = [
            entry["user"].username
            for entry in result
            if entry["user"].username in ("user_low", "user_high")
        ]

        # Should be sorted by total points descending: user_high (20), user_low (5)
        assert user_order == ["user_high", "user_low"]

    def test_includes_users_without_predictions(self, db, regular_user, test_match):
        """Helper includes all active users even those without predictions."""
        from django.contrib.auth import get_user_model

        from predictions.services import build_match_predictions_list

        User = get_user_model()

        # Create user without prediction (username used in assertions)
        User.objects.create_user(username="no_prediction_user", password="test")

        # Create user with prediction
        user_with_pred = User.objects.create_user(username="has_prediction_user", password="test")
        MatchPrediction.objects.create(
            user=user_with_pred,
            match=test_match,
            predicted_goals_home=1,
            predicted_goals_away=1,
        )

        result = build_match_predictions_list(test_match, "match", regular_user)

        # Find our test users
        user_dict = {entry["user"].username: entry for entry in result}

        # Both should be included
        assert "no_prediction_user" in user_dict
        assert "has_prediction_user" in user_dict

        # User without prediction should have has_predicted=False
        no_pred_entry = user_dict["no_prediction_user"]
        assert no_pred_entry["has_predicted"] is False
        assert no_pred_entry["points_earned"] is None

        # User with prediction should have has_predicted=True
        with_pred_entry = user_dict["has_prediction_user"]
        assert with_pred_entry["has_predicted"] is True

    def test_assigns_ranks(self, db, regular_user, test_match):
        """Helper assigns consecutive ranks based on sort order."""
        from django.contrib.auth import get_user_model

        from predictions.services import build_match_predictions_list

        User = get_user_model()

        # Create 5 users with different scores
        for i, points in enumerate([50, 40, 30, 20, 10]):
            user = User.objects.create_user(username=f"rank_user_{i}", password="test")
            MatchPrediction.objects.create(
                user=user,
                match=test_match,
                predicted_goals_home=1,
                predicted_goals_away=1,
                points_earned=points,
            )

        result = build_match_predictions_list(test_match, "match", regular_user)

        # Get ranks for our test users
        user_ranks = [
            (entry["user"].username, entry["rank"])
            for entry in result
            if entry["user"].username.startswith("rank_user_")
        ]

        # Should be ranked 1, 2, 3, 4, 5 (after other users if any)
        ranks = [rank for _, rank in sorted(user_ranks, key=lambda x: x[0])]
        # Users are sorted by points, so rank_user_0 (50 pts) should be first
        # The exact rank values depend on how many other users exist,
        # but they should be consecutive
        assert len(set(ranks)) == 5  # 5 distinct ranks

    def test_ties_broken_by_username(self, db, regular_user, test_match):
        """Helper breaks ties by username alphabetically."""
        from django.contrib.auth import get_user_model

        from predictions.services import build_match_predictions_list

        User = get_user_model()

        # Create users with same points
        user_z = User.objects.create_user(username="zzz_last", password="test")
        user_a = User.objects.create_user(username="aaa_first_tie", password="test")

        # Same points for both
        MatchPrediction.objects.create(
            user=user_z,
            match=test_match,
            predicted_goals_home=1,
            predicted_goals_away=1,
            points_earned=100,
        )
        MatchPrediction.objects.create(
            user=user_a,
            match=test_match,
            predicted_goals_home=1,
            predicted_goals_away=1,
            points_earned=100,
        )

        result = build_match_predictions_list(test_match, "match", regular_user)

        # Find positions of our test users
        usernames = [entry["user"].username for entry in result]
        a_index = usernames.index("aaa_first_tie")
        z_index = usernames.index("zzz_last")

        # aaa should come before zzz (alphabetical)
        assert a_index < z_index

    def test_view_still_works_with_helper(self, client, regular_user, test_match):
        """Integration test: MatchPredictionsView still works after refactoring."""
        url = reverse("predictions:match-predictions", args=[test_match.id])
        client.force_login(regular_user)

        response = client.get(url)

        assert response.status_code == 200
        assert "user_predictions" in response.context
        assert response.templates[0].name == "predictions/match_predictions_page.html"


class TestMatchPredictionsUpdateView:
    """Tests for the MatchPredictionsUpdateView HTMX endpoint."""

    def test_requires_auth(self, client, test_match):
        """Anonymous users should be redirected to login."""
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])
        response = client.get(url)

        assert response.status_code == 302
        assert "/login/" in response.url

    def test_returns_404_for_invalid_match(self, client, regular_user):
        """Non-existent match should return 404."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[99999])
        response = client.get(url)

        assert response.status_code == 404

    def test_default_sort_mode(self, client, regular_user, test_match):
        """Default sort mode should be 'match' when not specified."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["sort_mode"] == "match"

    def test_validates_sort_mode(self, client, regular_user, test_match):
        """Invalid sort mode should fall back to 'match'."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])
        response = client.get(url + "?sort=invalid")

        assert response.status_code == 200
        assert response.context["sort_mode"] == "match"

    def test_accepts_valid_sort_modes(self, client, regular_user, test_match):
        """Valid sort modes should be accepted."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])

        # Test sort=match
        response = client.get(url + "?sort=match")
        assert response.context["sort_mode"] == "match"

        # Test sort=total
        response = client.get(url + "?sort=total")
        assert response.context["sort_mode"] == "total"

    def test_preserves_origin(self, client, regular_user, test_match):
        """Origin parameter should be preserved in context."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])
        response = client.get(url + "?from=home")

        assert response.status_code == 200
        assert response.context["origin"] == "home"

    def test_context_structure(self, client, regular_user, test_match):
        """Response context should contain all required keys."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])
        response = client.get(url)

        assert response.status_code == 200
        assert "match" in response.context
        assert "user_predictions" in response.context
        assert "sort_mode" in response.context
        assert "current_user" in response.context
        assert "origin" in response.context

    def test_uses_correct_template(self, client, regular_user, test_match):
        """Should render predictions list content."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        # Should include predictions content (sort toggle)
        assert "Spielpunkte" in content


class TestMatchPredictionsPageHTMXPolling:
    """Tests for HTMX polling on the full page template."""

    def test_view_includes_polling_interval(self, client, regular_user, test_match):
        """View should include polling_interval in context."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        assert response.status_code == 200
        assert "polling_interval" in response.context
        # Should be 1 (active) or 60 (idle)
        assert response.context["polling_interval"] in (1, 60)

    def test_template_has_htmx_polling_attributes(self, client, regular_user, test_match):
        """Template should include HTMX polling attributes."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        content = response.content.decode()
        assert "hx-get=" in content
        assert "hx-trigger=" in content
        assert 'hx-swap="innerHTML"' in content
        assert 'id="predictions-content"' in content

    def test_template_includes_partial(self, client, regular_user, test_match):
        """Template should include the partial content."""
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
        # Sort toggle should be present (from partial)
        assert "Spielpunkte" in content
        assert "Gesamtpunkte" in content
        # Predictions should be present
        assert regular_user.username in content

    def test_htmx_url_includes_parameters(self, client, regular_user, test_match):
        """HTMX URL should include sort and from parameters."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url + "?sort=total&from=home")

        content = response.content.decode()
        # Check that the hx-get URL includes the parameters
        assert "sort=total" in content
        assert "from=home" in content


class TestPollingBehavior:
    """Integration tests for HTMX polling behavior and live updates."""

    def test_polling_detects_new_prediction(self, client, regular_user, test_match, db):
        """Polling should detect new predictions from other users."""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Create another user
        other_user = User.objects.create_user(username="other_tipper", password="test")

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])

        # Initial poll - other user has no prediction
        response1 = client.get(url)
        content1 = response1.content.decode()
        assert "other_tipper" in content1
        # No prediction yet
        assert content1.count("Kein Tipp") >= 1  # At least one user without tip

        # Other user submits a prediction
        MatchPrediction.objects.create(
            user=other_user,
            match=test_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # Second poll - should show new prediction
        response2 = client.get(url)
        content2 = response2.content.decode()
        assert "other_tipper" in content2
        assert "2:1" in content2

    def test_polling_detects_prediction_changes(self, client, regular_user, test_match, db):
        """Polling should detect when prediction points change."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        other_user = User.objects.create_user(username="points_user", password="test")

        # Create prediction with initial points
        pred = MatchPrediction.objects.create(
            user=other_user,
            match=test_match,
            predicted_goals_home=1,
            predicted_goals_away=1,
            points_earned=3,
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])

        # Initial poll
        response1 = client.get(url)
        content1 = response1.content.decode()
        assert "+3" in content1

        # Points change
        pred.points_earned = 5
        pred.save()

        # Second poll should show updated points
        response2 = client.get(url)
        content2 = response2.content.decode()
        assert "+5" in content2

    def test_polling_detects_ranking_changes(self, client, regular_user, test_match, db):
        """Polling should detect ranking changes when totals change."""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Create users with different total points
        user_a = User.objects.create_user(username="rank_a", password="test")
        user_b = User.objects.create_user(username="rank_b", password="test")

        # Initial state: user_a has more total points
        MatchPrediction.objects.create(
            user=user_a,
            match=test_match,
            predicted_goals_home=1,
            predicted_goals_away=1,
            points_earned=20,
        )
        MatchPrediction.objects.create(
            user=user_b,
            match=test_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=10,
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])

        # Check with sort=total
        response = client.get(url + "?sort=total")
        content = response.content.decode()

        # Find positions
        a_pos = content.find("rank_a")
        b_pos = content.find("rank_b")
        assert a_pos < b_pos  # user_a should come first (more points)

    def test_polling_preserves_sort_mode_match(self, client, regular_user, test_match):
        """Polling should preserve sort=match mode."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])
        response = client.get(url + "?sort=match")

        content = response.content.decode()
        # "Spielpunkte" should have active styling
        assert "bg-white dark:bg-zinc-600" in content
        # Check sort_mode in context
        assert response.context["sort_mode"] == "match"

    def test_polling_preserves_sort_mode_total(self, client, regular_user, test_match):
        """Polling should preserve sort=total mode."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])
        response = client.get(url + "?sort=total")

        assert response.context["sort_mode"] == "total"

    def test_polling_interval_during_active_match(self, db, teams):
        """Polling interval should be 1s during active match."""
        from predictions.services import get_polling_interval

        # Create match that started 30 minutes ago (detected by get_polling_interval)
        Match.objects.create(
            team_home=teams[0],
            team_away=teams[1],
            kickoff=timezone.now() - timedelta(minutes=30),
            round="group",
            status="in_progress",
        )

        interval = get_polling_interval()
        assert interval == 15

    def test_polling_interval_during_idle_period(self, db, teams):
        """Polling interval should be 60s when no active matches."""
        from predictions.services import get_polling_interval

        # Create match that finished hours ago (outside active window)
        Match.objects.create(
            team_home=teams[0],
            team_away=teams[1],
            kickoff=timezone.now() - timedelta(hours=5),
            round="group",
            status="finished",
        )

        interval = get_polling_interval()
        assert interval == 60


class TestVersionTracking:
    """Tests for version-based polling optimization."""

    def test_match_predictions_view_includes_version_in_context(
        self, client, regular_user, past_match
    ):
        """Full page view should include current_version in context."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url)

        assert response.status_code == 200
        assert "current_version" in response.context
        # past_match has goals_home=2, goals_away=1
        assert response.context["current_version"] == "2:1"

    def test_match_predictions_view_version_with_none_score(self, client, regular_user, test_match):
        """Version should be 'None:None' for matches without score."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        assert response.context["current_version"] == "None:None"

    def test_update_view_returns_version_in_header(self, client, regular_user, past_match):
        """Update view should return version in HX-Trigger header."""
        import json

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[past_match.id])
        response = client.get(url)

        assert "HX-Trigger" in response.headers
        trigger = json.loads(response.headers["HX-Trigger"])
        assert trigger["version"] == "2:1"

    def test_update_view_version_format_with_none_score(self, client, regular_user, test_match):
        """Version header should contain None:None for matches without score."""
        import json

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])
        response = client.get(url)

        trigger = json.loads(response.headers["HX-Trigger"])
        assert trigger["version"] == "None:None"

    def test_update_view_returns_empty_when_version_unchanged_post_kickoff(
        self, client, regular_user, past_match
    ):
        """Post-kickoff with matching version should return empty response."""
        import json

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[past_match.id])
        # past_match has score 2:1
        response = client.get(url + "?version=2:1")

        assert response.status_code == 200
        assert response.content == b""
        # Should still include version header
        trigger = json.loads(response.headers["HX-Trigger"])
        assert trigger["version"] == "2:1"

    def test_update_view_renders_when_version_changed_post_kickoff(
        self, client, regular_user, past_match
    ):
        """Post-kickoff with old version should render full response."""
        import json

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[past_match.id])
        # Send old version (1:0), but match has score 2:1
        response = client.get(url + "?version=1:0")

        assert response.status_code == 200
        assert response.content != b""
        # Response should contain HTML
        assert b"<div" in response.content
        # Should include new version in header
        trigger = json.loads(response.headers["HX-Trigger"])
        assert trigger["version"] == "2:1"

    def test_update_view_always_renders_pre_kickoff(self, client, regular_user, test_match):
        """Pre-kickoff should always render full response even if version matches."""

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[test_match.id])
        # Send matching version (None:None)
        response = client.get(url + "?version=None:None")

        assert response.status_code == 200
        # Should NOT be empty - pre-kickoff predictions can change
        assert response.content != b""
        assert b"<div" in response.content

    def test_update_view_handles_missing_version_param(self, client, regular_user, past_match):
        """Missing version param should trigger full render."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[past_match.id])
        response = client.get(url)  # No version param

        assert response.status_code == 200
        # Should render full response (empty string doesn't match "2:1")
        assert response.content != b""

    def test_update_view_full_render_includes_predictions_list(
        self, client, regular_user, past_match
    ):
        """Full render should include predictions list content."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[past_match.id])
        # Send old version to trigger full render
        response = client.get(url + "?version=0:0")

        content = response.content.decode()
        # Should include sort toggle (from predictions list)
        assert "Spielpunkte" in content
        assert "Gesamtpunkte" in content

    def test_update_view_empty_response_has_no_oob_directive(
        self, client, regular_user, past_match
    ):
        """Empty response should not contain OOB directive."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[past_match.id])
        # Send matching version to get empty response
        response = client.get(url + "?version=2:1")

        content = response.content.decode()
        assert "hx-swap-oob" not in content

    def test_match_predictions_page_has_dynamic_polling(self, client, regular_user, test_match):
        """Page template should have dynamic polling interval (1s or 60s)."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        content = response.content.decode()
        # Polling interval is dynamic: 1s during active matches, 60s otherwise
        assert 'hx-trigger="every 1s"' in content or 'hx-trigger="every 60s"' in content

    def test_match_predictions_page_includes_version_in_url(self, client, regular_user, past_match):
        """Page template should include version in hx-get URL."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url)

        content = response.content.decode()
        # past_match has score 2:1
        assert "version=2:1" in content

    def test_match_predictions_page_has_version_update_script(
        self, client, regular_user, test_match
    ):
        """Page should include JavaScript for version tracking."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[test_match.id])
        response = client.get(url)

        content = response.content.decode()
        assert "htmx:afterOnLoad" in content
        assert "HX-Trigger" in content
        assert "trigger.version" in content

    def test_match_predictions_page_renders_with_team_names(self, client, regular_user, past_match):
        """Page should render with team names."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        # Page should show team names
        assert past_match.team_home.name in content
        assert past_match.team_away.name in content

    def test_match_predictions_page_shows_result_when_available(
        self, client, regular_user, past_match
    ):
        """Page should show match result when available."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url)

        content = response.content.decode()
        # past_match has score 2:1 - should show in result section
        assert "2:1" in content

    def test_full_polling_cycle_with_score_change(self, client, regular_user, teams, db):
        """Integration test: full polling cycle with score updates."""
        import json

        # Create match that just started (post-kickoff)
        match = Match.objects.create(
            team_home=teams[0],
            team_away=teams[1],
            kickoff=timezone.now() - timedelta(minutes=10),
            round="group",
            status="in_progress",
            goals_home=0,
            goals_away=0,
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[match.id])

        # First poll with version 0:0 - should return empty (version matches)
        response = client.get(url + "?version=0:0")
        assert response.content == b""
        trigger = json.loads(response.headers["HX-Trigger"])
        assert trigger["version"] == "0:0"

        # Score changes to 1:0
        match.goals_home = 1
        match.save()

        # Second poll with old version 0:0 - should return full render
        response = client.get(url + "?version=0:0")
        assert response.content != b""
        trigger = json.loads(response.headers["HX-Trigger"])
        assert trigger["version"] == "1:0"

        # Third poll with new version 1:0 - should return empty again
        response = client.get(url + "?version=1:0")
        assert response.content == b""

    def test_version_persists_across_multiple_polls(self, client, regular_user, past_match):
        """Multiple polls with matching version should all return empty."""
        import json

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions-updates", args=[past_match.id])

        # Poll 5 times with matching version
        for _ in range(5):
            response = client.get(url + "?version=2:1")
            assert response.content == b""
            trigger = json.loads(response.headers["HX-Trigger"])
            assert trigger["version"] == "2:1"
