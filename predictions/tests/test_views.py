"""Tests for prediction views."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from matches.models import Match, Team
from predictions.models import MatchPrediction
from predictions.views import get_phase_stats


@pytest.fixture
def teams(db):
    """Create test teams."""
    team_a = Team.objects.create(name="Germany", fifa_code="GER")
    team_b = Team.objects.create(name="Brazil", fifa_code="BRA")
    team_c = Team.objects.create(name="France", fifa_code="FRA")
    team_d = Team.objects.create(name="Spain", fifa_code="ESP")
    return team_a, team_b, team_c, team_d


@pytest.fixture
def future_match(teams, db):
    """Create a future match."""
    team_a, team_b, _, _ = teams
    return Match.objects.create(
        team_home=team_a,
        team_away=team_b,
        kickoff=timezone.now() + timedelta(days=7),
        round="group",
    )


@pytest.fixture
def past_match(teams, db):
    """Create a past (locked) match."""
    team_a, team_b, _, _ = teams
    return Match.objects.create(
        team_home=team_a,
        team_away=team_b,
        kickoff=timezone.now() - timedelta(hours=1),
        round="group",
        status="finished",
        goals_home=2,
        goals_away=1,
    )


@pytest.fixture
def knockout_match(teams, db):
    """Create a future knockout match."""
    team_a, team_b, _, _ = teams
    return Match.objects.create(
        team_home=team_a,
        team_away=team_b,
        kickoff=timezone.now() + timedelta(days=30),
        round="r32",
    )


@pytest.fixture
def group_matches_for_limit(teams, db):
    """Create enough group matches to test the 36 limit."""
    team_a, team_b, team_c, team_d = teams
    matches = []
    base_time = timezone.now() + timedelta(days=1)
    for i in range(40):
        match = Match.objects.create(
            team_home=team_a if i % 2 == 0 else team_c,
            team_away=team_b if i % 2 == 0 else team_d,
            kickoff=base_time + timedelta(hours=i),
            round="group",
        )
        matches.append(match)
    return matches


class TestPredictionListView:
    """Tests for PredictionListView."""

    def test_requires_authentication(self, client, future_match):
        """GET /predictions/ should require login."""
        url = reverse("predictions:prediction-list")
        response = client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_returns_200_for_authenticated_user(self, client, regular_user, future_match):
        """GET /predictions/ should return 200 for authenticated user."""
        client.force_login(regular_user)
        url = reverse("predictions:prediction-list")
        response = client.get(url)
        assert response.status_code == 200

    def test_shows_all_matches_ordered_by_kickoff(self, client, regular_user, teams, db):
        """Matches should be ordered by kickoff time."""
        team_a, team_b, team_c, team_d = teams
        base_time = timezone.now() + timedelta(days=1)

        # Create matches out of order
        match3 = Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=base_time + timedelta(hours=3),
            round="group",
        )
        match1 = Match.objects.create(
            team_home=team_c,
            team_away=team_d,
            kickoff=base_time + timedelta(hours=1),
            round="group",
        )
        match2 = Match.objects.create(
            team_home=team_a,
            team_away=team_c,
            kickoff=base_time + timedelta(hours=2),
            round="group",
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-list")
        response = client.get(url)

        matches_data = response.context["matches_data"]
        assert len(matches_data) == 3
        assert matches_data[0]["match"] == match1
        assert matches_data[1]["match"] == match2
        assert matches_data[2]["match"] == match3

    def test_shows_existing_predictions(self, client, regular_user, future_match):
        """Should show user's existing predictions."""
        # Create prediction
        prediction = MatchPrediction.objects.create(
            user=regular_user,
            match=future_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-list")
        response = client.get(url)

        matches_data = response.context["matches_data"]
        assert matches_data[0]["prediction"] == prediction


class TestPredictionSaveView:
    """Tests for PredictionSaveView."""

    def test_requires_authentication(self, client, future_match):
        """POST /predictions/<id>/save/ should require login."""
        url = reverse("predictions:prediction-save", args=[future_match.id])
        response = client.post(
            url,
            data={
                "predicted_goals_home": 2,
                "predicted_goals_away": 1,
            },
        )
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_creates_new_prediction(self, client, regular_user, future_match):
        """Should create a new prediction."""
        client.force_login(regular_user)
        url = reverse("predictions:prediction-save", args=[future_match.id])

        response = client.post(
            url,
            data={
                "predicted_goals_home": 2,
                "predicted_goals_away": 1,
            },
        )

        assert response.status_code == 200
        prediction = MatchPrediction.objects.get(user=regular_user, match=future_match)
        assert prediction.predicted_goals_home == 2
        assert prediction.predicted_goals_away == 1

    def test_updates_existing_prediction(self, client, regular_user, future_match):
        """Should update an existing prediction."""
        # Create initial prediction
        prediction = MatchPrediction.objects.create(
            user=regular_user,
            match=future_match,
            predicted_goals_home=1,
            predicted_goals_away=0,
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-save", args=[future_match.id])

        response = client.post(
            url,
            data={
                "predicted_goals_home": 3,
                "predicted_goals_away": 2,
            },
        )

        assert response.status_code == 200
        prediction.refresh_from_db()
        assert prediction.predicted_goals_home == 3
        assert prediction.predicted_goals_away == 2

    def test_rejected_after_locktime(self, client, regular_user, past_match):
        """Should reject save after match kickoff."""
        client.force_login(regular_user)
        url = reverse("predictions:prediction-save", args=[past_match.id])

        response = client.post(
            url,
            data={
                "predicted_goals_home": 2,
                "predicted_goals_away": 1,
            },
        )

        assert response.status_code == 400
        assert not MatchPrediction.objects.filter(user=regular_user, match=past_match).exists()

    def test_rejected_when_group_limit_exceeded(
        self, client, regular_user, group_matches_for_limit
    ):
        """Should reject new group prediction when at 36 limit."""
        # Create 36 predictions
        for match in group_matches_for_limit[:36]:
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=1,
                predicted_goals_away=1,
            )

        client.force_login(regular_user)
        # Try to create 37th prediction
        new_match = group_matches_for_limit[36]
        url = reverse("predictions:prediction-save", args=[new_match.id])

        response = client.post(
            url,
            data={
                "predicted_goals_home": 2,
                "predicted_goals_away": 1,
            },
        )

        assert response.status_code == 400
        assert not MatchPrediction.objects.filter(user=regular_user, match=new_match).exists()

    def test_404_for_invalid_match(self, client, regular_user):
        """Should return 404 for non-existent match."""
        client.force_login(regular_user)
        url = reverse("predictions:prediction-save", args=[99999])

        response = client.post(
            url,
            data={
                "predicted_goals_home": 2,
                "predicted_goals_away": 1,
            },
        )

        assert response.status_code == 404


class TestPredictionDeleteView:
    """Tests for PredictionDeleteView."""

    def test_requires_authentication(self, client, future_match):
        """POST /predictions/<id>/delete/ should require login."""
        url = reverse("predictions:prediction-delete", args=[future_match.id])
        response = client.post(url)
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_removes_prediction(self, client, regular_user, future_match):
        """Should delete the prediction."""
        # Create prediction
        MatchPrediction.objects.create(
            user=regular_user,
            match=future_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-delete", args=[future_match.id])

        response = client.post(url)

        assert response.status_code == 200
        assert not MatchPrediction.objects.filter(user=regular_user, match=future_match).exists()

    def test_rejected_after_locktime(self, client, regular_user, past_match):
        """Should reject delete after match kickoff."""
        # Create prediction (would have been created before locktime)
        prediction = MatchPrediction.objects.create(
            user=regular_user,
            match=past_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-delete", args=[past_match.id])

        response = client.post(url)

        assert response.status_code == 400
        assert MatchPrediction.objects.filter(pk=prediction.pk).exists()

    def test_404_for_missing_prediction(self, client, regular_user, future_match):
        """Should return 404 if no prediction exists."""
        client.force_login(regular_user)
        url = reverse("predictions:prediction-delete", args=[future_match.id])

        response = client.post(url)

        assert response.status_code == 404


class TestPredictionJokerView:
    """Tests for PredictionJokerView."""

    def test_requires_authentication(self, client, knockout_match):
        """POST /predictions/<id>/joker/ should require login."""
        url = reverse("predictions:prediction-joker", args=[knockout_match.id])
        response = client.post(url)
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_toggles_joker_on(self, client, regular_user, knockout_match):
        """Should enable joker."""
        # Create prediction without joker
        prediction = MatchPrediction.objects.create(
            user=regular_user,
            match=knockout_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=False,
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-joker", args=[knockout_match.id])

        response = client.post(url)

        assert response.status_code == 200
        prediction.refresh_from_db()
        assert prediction.joker_active is True

    def test_toggles_joker_off(self, client, regular_user, knockout_match):
        """Should disable joker."""
        # Create prediction with joker
        prediction = MatchPrediction.objects.create(
            user=regular_user,
            match=knockout_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=True,
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-joker", args=[knockout_match.id])

        response = client.post(url)

        assert response.status_code == 200
        prediction.refresh_from_db()
        assert prediction.joker_active is False

    def test_rejected_for_group_stage(self, client, regular_user, future_match):
        """Should reject joker for group stage match."""
        # Create prediction for group match
        MatchPrediction.objects.create(
            user=regular_user,
            match=future_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-joker", args=[future_match.id])

        response = client.post(url)

        assert response.status_code == 400

    def test_rejected_when_limit_exceeded(self, client, regular_user, teams, db):
        """Should reject joker when round limit exceeded."""
        team_a, team_b, team_c, team_d = teams
        base_time = timezone.now() + timedelta(days=30)

        # Create 3 r32 matches with jokers (limit is 3)
        for i in range(3):
            match = Match.objects.create(
                team_home=team_a if i % 2 == 0 else team_c,
                team_away=team_b if i % 2 == 0 else team_d,
                kickoff=base_time + timedelta(hours=i),
                round="r32",
            )
            MatchPrediction.objects.create(
                user=regular_user,
                match=match,
                predicted_goals_home=2,
                predicted_goals_away=1,
                joker_active=True,
            )

        # Create 4th match without joker
        fourth_match = Match.objects.create(
            team_home=team_a,
            team_away=team_c,
            kickoff=base_time + timedelta(hours=4),
            round="r32",
        )
        prediction = MatchPrediction.objects.create(
            user=regular_user,
            match=fourth_match,
            predicted_goals_home=1,
            predicted_goals_away=0,
            joker_active=False,
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-joker", args=[fourth_match.id])

        response = client.post(url)

        assert response.status_code == 400
        prediction.refresh_from_db()
        assert prediction.joker_active is False

    def test_rejected_after_locktime(self, client, regular_user, teams, db):
        """Should reject joker toggle after match kickoff."""
        team_a, team_b, _, _ = teams
        past_knockout = Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() - timedelta(hours=1),
            round="r32",
        )
        prediction = MatchPrediction.objects.create(
            user=regular_user,
            match=past_knockout,
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=False,
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-joker", args=[past_knockout.id])

        response = client.post(url)

        assert response.status_code == 400
        prediction.refresh_from_db()
        assert prediction.joker_active is False

    def test_rejected_without_prediction(self, client, regular_user, knockout_match):
        """Should reject joker if no prediction exists."""
        client.force_login(regular_user)
        url = reverse("predictions:prediction-joker", args=[knockout_match.id])

        response = client.post(url)

        assert response.status_code == 400


class TestPointsDisplay:
    """Tests for points display in views."""

    def test_points_displayed_for_finished_match(self, client, regular_user, teams, db):
        """Should display points for finished match predictions."""
        team_a, team_b, _, _ = teams
        finished_match = Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() - timedelta(hours=3),
            round="group",
            status="finished",
            goals_home=2,
            goals_away=1,
        )
        # Create scored prediction
        MatchPrediction.objects.create(
            user=regular_user,
            match=finished_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=6,
            is_exact_match=True,
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-list")
        response = client.get(url)

        content = response.content.decode()
        assert "+6 Punkte" in content


class TestGetPhaseStats:
    """Tests for get_phase_stats() helper function."""

    def test_returns_all_phases(self, regular_user, db):
        """Should return stats for all 7 tournament phases."""
        from matches.constants import ROUND_ORDER
        
        stats = get_phase_stats(regular_user)

        assert list(stats.keys()) == ROUND_ORDER

    def test_returns_correct_structure(self, regular_user, db):
        """Each phase should have predictions, jokers, total_matches, joker_limit."""
        stats = get_phase_stats(regular_user)

        for _phase, data in stats.items():
            assert "predictions" in data
            assert "jokers" in data
            assert "total_matches" in data
            assert "joker_limit" in data

    def test_counts_matches_per_phase(self, regular_user, teams, db):
        """Should count total matches per phase (group uses limit of 36)."""
        team_a, team_b, _, _ = teams
        base_time = timezone.now() + timedelta(days=1)

        # Create matches in different phases
        Match.objects.create(team_home=team_a, team_away=team_b, kickoff=base_time, round="group")
        Match.objects.create(team_home=team_a, team_away=team_b, kickoff=base_time + timedelta(hours=1), round="group")
        Match.objects.create(team_home=team_a, team_away=team_b, kickoff=base_time + timedelta(hours=2), round="r32")

        stats = get_phase_stats(regular_user)

        # Group stage shows prediction limit (36) instead of actual match count
        assert stats["group"]["total_matches"] == 36
        assert stats["r32"]["total_matches"] == 1
        assert stats["r16"]["total_matches"] == 0

    def test_counts_predictions_per_phase(self, regular_user, teams, db):
        """Should count user predictions per phase."""
        team_a, team_b, _, _ = teams
        base_time = timezone.now() + timedelta(days=1)

        # Create matches
        group_match = Match.objects.create(team_home=team_a, team_away=team_b, kickoff=base_time, round="group")
        r32_match = Match.objects.create(team_home=team_a, team_away=team_b, kickoff=base_time + timedelta(hours=1), round="r32")

        # Create predictions
        MatchPrediction.objects.create(user=regular_user, match=group_match, predicted_goals_home=1, predicted_goals_away=0)
        MatchPrediction.objects.create(user=regular_user, match=r32_match, predicted_goals_home=2, predicted_goals_away=1)

        stats = get_phase_stats(regular_user)

        assert stats["group"]["predictions"] == 1
        assert stats["r32"]["predictions"] == 1
        assert stats["r16"]["predictions"] == 0

    def test_counts_jokers_per_phase(self, regular_user, teams, db):
        """Should count active jokers per phase."""
        team_a, team_b, _, _ = teams
        base_time = timezone.now() + timedelta(days=30)

        # Create knockout matches
        r32_match1 = Match.objects.create(team_home=team_a, team_away=team_b, kickoff=base_time, round="r32")
        r32_match2 = Match.objects.create(team_home=team_a, team_away=team_b, kickoff=base_time + timedelta(hours=1), round="r32")

        # Create predictions with jokers
        MatchPrediction.objects.create(user=regular_user, match=r32_match1, predicted_goals_home=1, predicted_goals_away=0, joker_active=True)
        MatchPrediction.objects.create(user=regular_user, match=r32_match2, predicted_goals_home=2, predicted_goals_away=1, joker_active=False)

        stats = get_phase_stats(regular_user)

        assert stats["r32"]["jokers"] == 1

    def test_group_stage_has_zero_joker_limit(self, regular_user, db):
        """Group stage should have joker_limit of 0."""
        stats = get_phase_stats(regular_user)

        assert stats["group"]["joker_limit"] == 0

    def test_knockout_phases_have_joker_limits(self, regular_user, db):
        """Knockout phases should have correct joker limits."""
        stats = get_phase_stats(regular_user)

        assert stats["r32"]["joker_limit"] == 3
        assert stats["r16"]["joker_limit"] == 3
        assert stats["qf"]["joker_limit"] == 2
        assert stats["sf"]["joker_limit"] == 2
        assert stats["3rd"]["joker_limit"] == 2
        assert stats["final"]["joker_limit"] == 2


class TestPhaseStatsInContext:
    """Tests for phase_stats in view context."""

    def test_context_contains_phase_stats(self, client, regular_user, teams, db):
        """View context should include phase_stats."""
        team_a, team_b, _, _ = teams
        Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() + timedelta(days=1),
            round="group"
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-list")
        response = client.get(url)

        assert "phase_stats" in response.context
        assert "phase_stats_json" in response.context
        assert "tournament_phases" in response.context

    def test_phase_stats_json_is_valid(self, client, regular_user, teams, db):
        """phase_stats_json should be valid JSON."""
        import json

        team_a, team_b, _, _ = teams
        Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() + timedelta(days=1),
            round="group"
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-list")
        response = client.get(url)

        # Should not raise
        parsed = json.loads(response.context["phase_stats_json"])
        assert "group" in parsed


class TestPhaseStatsView:
    """Tests for PhaseStatsView API endpoint."""

    def test_requires_authentication(self, client, db):
        """GET /predictions/phase-stats/ should require login."""
        url = reverse("predictions:phase-stats")
        response = client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_returns_json(self, client, regular_user, db):
        """Should return valid JSON response."""
        import json

        client.force_login(regular_user)
        url = reverse("predictions:phase-stats")
        response = client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"

        # Should parse as JSON
        data = json.loads(response.content)
        assert "group" in data
        assert "r32" in data
        assert "final" in data

    def test_returns_correct_stats(self, client, regular_user, teams, db):
        """Should return accurate prediction counts."""
        import json

        team_a, team_b, _, _ = teams
        base_time = timezone.now() + timedelta(days=1)

        # Create matches
        group_match = Match.objects.create(team_home=team_a, team_away=team_b, kickoff=base_time, round="group")
        r32_match = Match.objects.create(team_home=team_a, team_away=team_b, kickoff=base_time + timedelta(days=30), round="r32")

        # Create predictions
        MatchPrediction.objects.create(user=regular_user, match=group_match, predicted_goals_home=1, predicted_goals_away=0)
        MatchPrediction.objects.create(user=regular_user, match=r32_match, predicted_goals_home=2, predicted_goals_away=1, joker_active=True)

        client.force_login(regular_user)
        url = reverse("predictions:phase-stats")
        response = client.get(url)

        data = json.loads(response.content)

        assert data["group"]["predictions"] == 1
        assert data["group"]["total_matches"] == 36  # Group stage uses limit, not actual matches
        assert data["r32"]["predictions"] == 1
        assert data["r32"]["total_matches"] == 1
        assert data["r32"]["jokers"] == 1


class TestGetPollingInterval:
    """Tests for get_polling_interval() function."""

    def test_returns_idle_interval_when_no_matches(self, db):
        """Should return 60s when no matches exist."""
        from predictions.views import POLLING_INTERVAL_IDLE, get_polling_interval

        interval = get_polling_interval()

        assert interval == POLLING_INTERVAL_IDLE

    def test_returns_idle_interval_when_no_active_matches(self, teams, db):
        """Should return 60s when only future matches exist."""
        from predictions.views import POLLING_INTERVAL_IDLE, get_polling_interval

        team_a, team_b, _, _ = teams
        Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() + timedelta(days=1),
            round="group",
        )

        interval = get_polling_interval()

        assert interval == POLLING_INTERVAL_IDLE

    def test_returns_active_interval_during_match(self, teams, db):
        """Should return 10s when match started recently."""
        from predictions.views import POLLING_INTERVAL_ACTIVE, get_polling_interval

        team_a, team_b, _, _ = teams
        # Match kicked off 30 minutes ago
        Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() - timedelta(minutes=30),
            round="group",
            status="scheduled",
        )

        interval = get_polling_interval()

        assert interval == POLLING_INTERVAL_ACTIVE

    def test_returns_active_interval_during_extra_time(self, teams, db):
        """Should return 10s when match is in extra time (120 min)."""
        from predictions.views import POLLING_INTERVAL_ACTIVE, get_polling_interval

        team_a, team_b, _, _ = teams
        # Match kicked off 120 minutes ago (extra time)
        Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() - timedelta(minutes=120),
            round="r32",
            status="scheduled",
        )

        interval = get_polling_interval()

        assert interval == POLLING_INTERVAL_ACTIVE

    def test_returns_active_interval_during_penalties(self, teams, db):
        """Should return 10s when match could be in penalty shootout (150 min)."""
        from predictions.views import POLLING_INTERVAL_ACTIVE, get_polling_interval

        team_a, team_b, _, _ = teams
        # Match kicked off 150 minutes ago (penalties)
        Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() - timedelta(minutes=150),
            round="qf",
            status="scheduled",
        )

        interval = get_polling_interval()

        assert interval == POLLING_INTERVAL_ACTIVE

    def test_returns_idle_interval_after_match_window(self, teams, db):
        """Should return 60s when match started over 160 minutes ago."""
        from predictions.views import POLLING_INTERVAL_IDLE, get_polling_interval

        team_a, team_b, _, _ = teams
        # Match kicked off 180 minutes ago (well past any match duration)
        Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() - timedelta(minutes=180),
            round="group",
            status="scheduled",
        )

        interval = get_polling_interval()

        assert interval == POLLING_INTERVAL_IDLE

    def test_returns_idle_interval_for_finished_match_in_window(self, teams, db):
        """Should return 60s when match in window is already finished."""
        from predictions.views import POLLING_INTERVAL_IDLE, get_polling_interval

        team_a, team_b, _, _ = teams
        # Match kicked off 30 min ago but already marked finished
        Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() - timedelta(minutes=30),
            round="group",
            status="finished",
            goals_home=2,
            goals_away=1,
        )

        interval = get_polling_interval()

        assert interval == POLLING_INTERVAL_IDLE

    def test_multiple_matches_one_active(self, teams, db):
        """Should return 10s when at least one match is active."""
        from predictions.views import POLLING_INTERVAL_ACTIVE, get_polling_interval

        team_a, team_b, team_c, team_d = teams

        # Future match
        Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() + timedelta(days=1),
            round="group",
        )
        # Finished match
        Match.objects.create(
            team_home=team_c,
            team_away=team_d,
            kickoff=timezone.now() - timedelta(hours=3),
            round="group",
            status="finished",
            goals_home=1,
            goals_away=1,
        )
        # Active match
        Match.objects.create(
            team_home=team_a,
            team_away=team_c,
            kickoff=timezone.now() - timedelta(minutes=45),
            round="group",
            status="scheduled",
        )

        interval = get_polling_interval()

        assert interval == POLLING_INTERVAL_ACTIVE


class TestPredictionUpdatesPollingInterval:
    """Tests for polling interval in PredictionUpdatesView response."""

    def test_returns_polling_interval_header(self, client, regular_user, db):
        """Should return HX-Trigger header with polling interval."""
        import json

        client.force_login(regular_user)
        url = reverse("predictions:prediction-updates")
        response = client.get(url)

        assert response.status_code == 200
        assert "HX-Trigger" in response

        trigger = json.loads(response["HX-Trigger"])
        assert "pollingInterval" in trigger
        assert isinstance(trigger["pollingInterval"], int)

    def test_returns_active_interval_during_match(self, client, regular_user, teams, db):
        """Should return 10s polling interval when match is active."""
        import json

        from predictions.views import POLLING_INTERVAL_ACTIVE

        team_a, team_b, _, _ = teams
        # Active match
        Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=timezone.now() - timedelta(minutes=30),
            round="group",
            status="scheduled",
        )

        client.force_login(regular_user)
        url = reverse("predictions:prediction-updates")
        response = client.get(url)

        trigger = json.loads(response["HX-Trigger"])
        assert trigger["pollingInterval"] == POLLING_INTERVAL_ACTIVE

    def test_returns_idle_interval_when_no_active_match(self, client, regular_user, db):
        """Should return 60s polling interval when no active matches."""
        import json

        from predictions.views import POLLING_INTERVAL_IDLE

        client.force_login(regular_user)
        url = reverse("predictions:prediction-updates")
        response = client.get(url)

        trigger = json.loads(response["HX-Trigger"])
        assert trigger["pollingInterval"] == POLLING_INTERVAL_IDLE


class TestMatchPredictionsView:
    """Tests for MatchPredictionsView - viewing all predictions for a match."""

    def test_requires_authentication(self, client, future_match):
        """GET /predictions/match/<id>/predictions/ should require login."""
        url = reverse("predictions:match-predictions", args=[future_match.id])
        response = client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_returns_404_for_invalid_match(self, client, regular_user):
        """Should return 404 for non-existent match ID."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[99999])
        response = client.get(url)
        assert response.status_code == 404

    def test_returns_predictions_partial(self, client, regular_user, future_match):
        """Should return match predictions partial template."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[future_match.id])
        response = client.get(url)
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "predictions/partials/match_predictions.html" in template_names

    def test_shows_all_predictions_for_match(
        self, client, regular_user, multiple_users, future_match
    ):
        """Should include all users' predictions for the match."""
        # Create predictions from multiple users
        for idx, user in enumerate(multiple_users):
            MatchPrediction.objects.create(
                user=user,
                match=future_match,
                predicted_goals_home=idx,
                predicted_goals_away=idx + 1,
            )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[future_match.id])
        response = client.get(url)
        content = response.content.decode()

        # All 3 predictions should be visible
        for user in multiple_users:
            assert user.username in content

    def test_predictions_ordered_by_points_then_username(
        self, client, regular_user, multiple_users, past_match
    ):
        """Predictions should be ordered by points (desc), then username (asc)."""
        # Create predictions with different points
        MatchPrediction.objects.create(
            user=multiple_users[0],  # user1
            match=past_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=6,  # Exact match
        )
        MatchPrediction.objects.create(
            user=multiple_users[1],  # user2
            match=past_match,
            predicted_goals_home=3,
            predicted_goals_away=0,
            points_earned=0,
        )
        MatchPrediction.objects.create(
            user=multiple_users[2],  # user3
            match=past_match,
            predicted_goals_home=1,
            predicted_goals_away=0,
            points_earned=3,  # Correct tendency
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url)
        content = response.content.decode()

        # user1 (6pts) should come before user3 (3pts) before user2 (0pts)
        pos1 = content.find("user1")
        pos3 = content.find("user3")
        pos2 = content.find("user2")
        assert pos1 < pos3 < pos2

    def test_current_user_prediction_highlighted(
        self, client, regular_user, future_match
    ):
        """Current user's prediction should have highlight styling."""
        MatchPrediction.objects.create(
            user=regular_user,
            match=future_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[future_match.id])
        response = client.get(url)
        content = response.content.decode()

        # Check for highlight class (emerald background)
        assert "bg-emerald-50" in content or "bg-emerald-900" in content

    def test_shows_joker_indicator(self, client, regular_user, knockout_match):
        """Should show joker star indicator for joker predictions."""
        MatchPrediction.objects.create(
            user=regular_user,
            match=knockout_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=True,
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[knockout_match.id])
        response = client.get(url)
        content = response.content.decode()

        assert "⭐" in content

    def test_shows_empty_state_when_no_predictions(
        self, client, regular_user, future_match
    ):
        """Should show 'Kein Tipp' status when user has not submitted a prediction."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[future_match.id])
        response = client.get(url)
        content = response.content.decode()

        assert "Kein Tipp" in content

    def test_shows_match_result_if_available(self, client, regular_user, past_match):
        """Should display match result when available."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url)
        content = response.content.decode()

        # Result should be 2:1
        assert "2" in content and "1" in content

    def test_url_reverse_lookup(self, future_match):
        """URL should be reversible with match ID."""
        url = reverse("predictions:match-predictions", args=[future_match.id])
        assert f"/predictions/match/{future_match.id}/predictions/" in url

    def test_olympic_ranking_with_ties(
        self, client, regular_user, multiple_users, past_match
    ):
        """Should assign shared ranks for tied users (Olympic ranking)."""
        # Create predictions with various points: 6, 3, 3, 0
        MatchPrediction.objects.create(
            user=multiple_users[0],  # user1
            match=past_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=6,  # Rank 1
        )
        MatchPrediction.objects.create(
            user=multiple_users[1],  # user2
            match=past_match,
            predicted_goals_home=1,
            predicted_goals_away=0,
            points_earned=3,  # Rank 2 (tied)
        )
        MatchPrediction.objects.create(
            user=multiple_users[2],  # user3
            match=past_match,
            predicted_goals_home=1,
            predicted_goals_away=1,
            points_earned=3,  # Rank 2 (tied)
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url)
        content = response.content.decode()

        # user1 should be rank 1, user2 and user3 should both be rank 2
        # Find rank numbers by checking for "1.", "2.", "4." patterns
        assert "1." in content  # user1 with 6 points
        # Both user2 and user3 should show rank 2
        rank_2_count = content.count("2.")
        assert rank_2_count >= 2  # At least the two tied users
        # Next rank after tie should be 4, not 3
        assert "4." in content  # regular_user (no prediction = 0 points)

    def test_olympic_ranking_skips_after_tie(
        self, client, regular_user, multiple_users, past_match
    ):
        """After a tie, next rank should skip (1, 2, 2, 4 not 1, 2, 2, 3)."""
        # Create 4 predictions: 6, 3, 3, 1 points
        MatchPrediction.objects.create(
            user=multiple_users[0],
            match=past_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=6,  # Rank 1
        )
        MatchPrediction.objects.create(
            user=multiple_users[1],
            match=past_match,
            predicted_goals_home=1,
            predicted_goals_away=0,
            points_earned=3,  # Rank 2
        )
        MatchPrediction.objects.create(
            user=multiple_users[2],
            match=past_match,
            predicted_goals_home=1,
            predicted_goals_away=1,
            points_earned=3,  # Rank 2
        )
        MatchPrediction.objects.create(
            user=regular_user,
            match=past_match,
            predicted_goals_home=0,
            predicted_goals_away=0,
            points_earned=1,  # Rank 4 (skips 3)
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url)
        content = response.content.decode()

        # Should have ranks: 1, 2, 2, 4 (not 1, 2, 2, 3)
        assert "1." in content
        assert "2." in content
        assert "4." in content
        # Should NOT have rank 3 between the tie and next person
        lines = content.split("\n")
        # Count rank appearances more carefully
        rank_pattern = r'>\s*(\d+)\.\s*<'
        import re
        ranks = [int(m.group(1)) for m in re.finditer(rank_pattern, content)]
        # Should be [1, 2, 2, 4] for the four users
        assert 1 in ranks
        assert ranks.count(2) == 2
        assert 3 not in ranks  # Rank 3 is skipped
        assert 4 in ranks


class TestMatchPredictionsViewStatistics:
    """Tests for user statistics aggregation in MatchPredictionsView."""

    def test_includes_user_statistics_in_context(
        self, client, regular_user, multiple_users, teams, db
    ):
        """Context should include aggregated user statistics."""
        team_a, team_b, team_c, team_d = teams
        base_time = timezone.now() + timedelta(days=1)

        # Create match for viewing
        match = Match.objects.create(
            team_home=team_a,
            team_away=team_b,
            kickoff=base_time,
            round="group",
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[match.id])
        response = client.get(url)

        # Check context has user_predictions with statistics
        user_preds = response.context["user_predictions"]
        assert len(user_preds) > 0

        # Each entry should have statistics keys
        for entry in user_preds:
            assert "total_points" in entry
            assert "exact_count" in entry
            assert "jokers_count" in entry
            assert "champion" in entry
            assert "match_points" in entry

    def test_total_points_aggregation(
        self, client, regular_user, multiple_users, teams, db
    ):
        """Should correctly sum total_points across all predictions."""
        team_a, team_b, team_c, team_d = teams
        base_time = timezone.now() - timedelta(days=1)

        # Create past matches for user1
        m1 = Match.objects.create(
            team_home=team_a, team_away=team_b,
            kickoff=base_time, round="group", status="finished",
            goals_home=2, goals_away=1
        )
        m2 = Match.objects.create(
            team_home=team_c, team_away=team_d,
            kickoff=base_time + timedelta(hours=2), round="group", status="finished",
            goals_home=0, goals_away=0
        )

        # Create predictions with points for user1
        MatchPrediction.objects.create(
            user=multiple_users[0],  # user1
            match=m1,
            predicted_goals_home=2, predicted_goals_away=1,
            points_earned=6, is_exact_match=True
        )
        MatchPrediction.objects.create(
            user=multiple_users[0],  # user1
            match=m2,
            predicted_goals_home=1, predicted_goals_away=0,
            points_earned=0, is_exact_match=False
        )

        # Create viewing match
        view_match = Match.objects.create(
            team_home=team_a, team_away=team_c,
            kickoff=timezone.now() + timedelta(days=1), round="group"
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[view_match.id])
        response = client.get(url)

        user_preds = response.context["user_predictions"]
        user1_entry = next(e for e in user_preds if e["user"].username == "user1")

        # user1 should have total_points = 6 + 0 = 6
        assert user1_entry["total_points"] == 6

    def test_exact_count_aggregation(
        self, client, regular_user, multiple_users, teams, db
    ):
        """Should correctly count exact predictions."""
        team_a, team_b, team_c, team_d = teams
        base_time = timezone.now() - timedelta(days=1)

        # Create matches
        m1 = Match.objects.create(
            team_home=team_a, team_away=team_b,
            kickoff=base_time, round="group", status="finished",
            goals_home=2, goals_away=1
        )
        m2 = Match.objects.create(
            team_home=team_c, team_away=team_d,
            kickoff=base_time + timedelta(hours=2), round="group", status="finished",
            goals_home=0, goals_away=0
        )

        # Create predictions for user1: 2 exact matches
        MatchPrediction.objects.create(
            user=multiple_users[0], match=m1,
            predicted_goals_home=2, predicted_goals_away=1,
            points_earned=6, is_exact_match=True
        )
        MatchPrediction.objects.create(
            user=multiple_users[0], match=m2,
            predicted_goals_home=0, predicted_goals_away=0,
            points_earned=6, is_exact_match=True
        )

        view_match = Match.objects.create(
            team_home=team_a, team_away=team_c,
            kickoff=timezone.now() + timedelta(days=1), round="group"
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[view_match.id])
        response = client.get(url)

        user_preds = response.context["user_predictions"]
        user1_entry = next(e for e in user_preds if e["user"].username == "user1")

        assert user1_entry["exact_count"] == 2

    def test_jokers_count_aggregation(
        self, client, regular_user, multiple_users, teams, db
    ):
        """Should correctly count jokers used."""
        team_a, team_b, team_c, team_d = teams
        base_time = timezone.now() + timedelta(days=30)

        # Create knockout matches
        m1 = Match.objects.create(
            team_home=team_a, team_away=team_b,
            kickoff=base_time, round="r32"
        )
        m2 = Match.objects.create(
            team_home=team_c, team_away=team_d,
            kickoff=base_time + timedelta(hours=2), round="r32"
        )

        # Create predictions with jokers for user1
        MatchPrediction.objects.create(
            user=multiple_users[0], match=m1,
            predicted_goals_home=2, predicted_goals_away=1,
            joker_active=True
        )
        MatchPrediction.objects.create(
            user=multiple_users[0], match=m2,
            predicted_goals_home=0, predicted_goals_away=0,
            joker_active=True
        )

        view_match = Match.objects.create(
            team_home=team_a, team_away=team_c,
            kickoff=timezone.now() + timedelta(days=1), round="group"
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[view_match.id])
        response = client.get(url)

        user_preds = response.context["user_predictions"]
        user1_entry = next(e for e in user_preds if e["user"].username == "user1")

        assert user1_entry["jokers_count"] == 2

    def test_champion_prediction_included(
        self, client, regular_user, teams, db
    ):
        """Should include user's champion prediction."""
        team_a, team_b, _, _ = teams

        # Set champion prediction for regular_user
        regular_user.predicted_champion = team_a
        regular_user.save()

        match = Match.objects.create(
            team_home=team_a, team_away=team_b,
            kickoff=timezone.now() + timedelta(days=1), round="group"
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[match.id])
        response = client.get(url)

        user_preds = response.context["user_predictions"]
        current_entry = next(e for e in user_preds if e["user"] == regular_user)

        assert current_entry["champion"] == team_a
        assert current_entry["champion"].name == "Germany"

    def test_no_predictions_shows_zero_stats(
        self, client, regular_user, teams, db
    ):
        """User with no predictions should show 0 for all stats."""
        team_a, team_b, _, _ = teams

        match = Match.objects.create(
            team_home=team_a, team_away=team_b,
            kickoff=timezone.now() + timedelta(days=1), round="group"
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[match.id])
        response = client.get(url)

        user_preds = response.context["user_predictions"]
        current_entry = next(e for e in user_preds if e["user"] == regular_user)

        assert current_entry["total_points"] == 0
        assert current_entry["exact_count"] == 0
        assert current_entry["jokers_count"] == 0


class TestMatchPredictionsViewSorting:
    """Tests for sort mode parameter in MatchPredictionsView."""

    def test_default_sort_is_match(self, client, regular_user, future_match):
        """Without sort parameter, should default to match points."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[future_match.id])
        response = client.get(url)

        assert response.context["sort_mode"] == "match"

    def test_sort_parameter_match(self, client, regular_user, future_match):
        """?sort=match should set sort_mode to match."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[future_match.id])
        response = client.get(url + "?sort=match")

        assert response.context["sort_mode"] == "match"

    def test_sort_parameter_total(self, client, regular_user, future_match):
        """?sort=total should set sort_mode to total."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[future_match.id])
        response = client.get(url + "?sort=total")

        assert response.context["sort_mode"] == "total"

    def test_invalid_sort_defaults_to_match(self, client, regular_user, future_match):
        """Invalid sort value should default to match."""
        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[future_match.id])
        response = client.get(url + "?sort=invalid")

        assert response.context["sort_mode"] == "match"

    def test_sort_by_match_points_order(
        self, client, regular_user, multiple_users, teams, db
    ):
        """Sort=match should order by match points descending."""
        team_a, team_b, _, _ = teams
        base_time = timezone.now() - timedelta(days=1)

        # Create multiple matches
        past_match = Match.objects.create(
            team_home=team_a, team_away=team_b,
            kickoff=base_time, round="group", status="finished",
            goals_home=2, goals_away=1
        )
        other_match = Match.objects.create(
            team_home=team_a, team_away=team_b,
            kickoff=base_time + timedelta(hours=2), round="group", status="finished",
            goals_home=1, goals_away=0
        )

        # user1: 0 pts on past_match, but 6 pts on other_match (high total)
        MatchPrediction.objects.create(
            user=multiple_users[0], match=past_match,
            predicted_goals_home=0, predicted_goals_away=0,
            points_earned=0
        )
        MatchPrediction.objects.create(
            user=multiple_users[0], match=other_match,
            predicted_goals_home=1, predicted_goals_away=0,
            points_earned=6, is_exact_match=True
        )

        # user2: 6 pts on past_match, 0 pts total other matches
        MatchPrediction.objects.create(
            user=multiple_users[1], match=past_match,
            predicted_goals_home=2, predicted_goals_away=1,
            points_earned=6, is_exact_match=True
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url + "?sort=match")
        content = response.content.decode()

        # user2 (6 match pts) should be before user1 (0 match pts)
        pos_user2 = content.find("user2")
        pos_user1 = content.find("user1")
        assert pos_user2 < pos_user1

    def test_sort_by_total_points_order(
        self, client, regular_user, multiple_users, teams, db
    ):
        """Sort=total should order by total points descending."""
        team_a, team_b, _, _ = teams
        base_time = timezone.now() - timedelta(days=1)

        # Create multiple matches
        past_match = Match.objects.create(
            team_home=team_a, team_away=team_b,
            kickoff=base_time, round="group", status="finished",
            goals_home=2, goals_away=1
        )
        other_match = Match.objects.create(
            team_home=team_a, team_away=team_b,
            kickoff=base_time + timedelta(hours=2), round="group", status="finished",
            goals_home=1, goals_away=0
        )

        # user1: 0 pts on past_match, 6 pts on other_match = 6 total
        MatchPrediction.objects.create(
            user=multiple_users[0], match=past_match,
            predicted_goals_home=0, predicted_goals_away=0,
            points_earned=0
        )
        MatchPrediction.objects.create(
            user=multiple_users[0], match=other_match,
            predicted_goals_home=1, predicted_goals_away=0,
            points_earned=6, is_exact_match=True
        )

        # user2: 3 pts on past_match = 3 total
        MatchPrediction.objects.create(
            user=multiple_users[1], match=past_match,
            predicted_goals_home=1, predicted_goals_away=0,
            points_earned=3
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[past_match.id])
        response = client.get(url + "?sort=total")
        content = response.content.decode()

        # user1 (6 total pts) should be before user2 (3 total pts)
        pos_user1 = content.find("user1")
        pos_user2 = content.find("user2")
        assert pos_user1 < pos_user2

    def test_olympic_ranking_in_total_mode(
        self, client, regular_user, multiple_users, teams, db
    ):
        """Olympic ranking should work correctly in total mode."""
        team_a, team_b, team_c, team_d = teams
        base_time = timezone.now() - timedelta(days=1)

        # Create matches
        m1 = Match.objects.create(
            team_home=team_a, team_away=team_b,
            kickoff=base_time, round="group", status="finished",
            goals_home=2, goals_away=1
        )
        m2 = Match.objects.create(
            team_home=team_c, team_away=team_d,
            kickoff=base_time + timedelta(hours=2), round="group", status="finished",
            goals_home=0, goals_away=0
        )
        view_match = Match.objects.create(
            team_home=team_a, team_away=team_c,
            kickoff=timezone.now() + timedelta(days=1), round="group"
        )

        # user1: 6 total pts
        MatchPrediction.objects.create(
            user=multiple_users[0], match=m1,
            predicted_goals_home=2, predicted_goals_away=1,
            points_earned=6, is_exact_match=True
        )
        # user2: 6 total pts (tie with user1)
        MatchPrediction.objects.create(
            user=multiple_users[1], match=m2,
            predicted_goals_home=0, predicted_goals_away=0,
            points_earned=6, is_exact_match=True
        )
        # user3: 3 total pts
        MatchPrediction.objects.create(
            user=multiple_users[2], match=m1,
            predicted_goals_home=1, predicted_goals_away=0,
            points_earned=3
        )

        client.force_login(regular_user)
        url = reverse("predictions:match-predictions", args=[view_match.id])
        response = client.get(url + "?sort=total")

        user_preds = response.context["user_predictions"]

        # Find entries for each user
        user1_entry = next(e for e in user_preds if e["user"].username == "user1")
        user2_entry = next(e for e in user_preds if e["user"].username == "user2")
        user3_entry = next(e for e in user_preds if e["user"].username == "user3")

        # user1 and user2 should both be rank 1 (tied at 6 pts)
        assert user1_entry["rank"] == 1
        assert user2_entry["rank"] == 1
        # user3 should be rank 3 (skips 2)
        assert user3_entry["rank"] == 3
