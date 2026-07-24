"""Tests for prediction views."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from matches.models import Match, Team
from predictions.models import MatchPrediction


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
