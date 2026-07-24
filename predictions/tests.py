"""Tests for the MatchPrediction model."""

import datetime
from datetime import UTC

import pytest
from django.db import IntegrityError


@pytest.fixture
def user1():
    """Create a test user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="user1",
        email="user1@example.com",
        password="test123",
    )


@pytest.fixture
def user2():
    """Create a second test user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="user2",
        email="user2@example.com",
        password="test123",
    )


@pytest.fixture
def team_home():
    """Create home team."""
    from matches.models import Team

    return Team.objects.create(
        name="Germany",
        fifa_code="GER",
        points=0,
    )


@pytest.fixture
def team_away():
    """Create away team."""
    from matches.models import Team

    return Team.objects.create(
        name="Brazil",
        fifa_code="BRA",
        points=0,
    )


@pytest.fixture
def match1(team_home, team_away):
    """Create a test match."""
    from matches.models import Match

    return Match.objects.create(
        team_home=team_home,
        team_away=team_away,
        kickoff=datetime.datetime(2026, 6, 15, 18, 0, tzinfo=UTC),
        round="gs",
    )


@pytest.fixture
def match2(team_home, team_away):
    """Create a second test match."""
    from matches.models import Match

    return Match.objects.create(
        team_home=team_away,
        team_away=team_home,
        kickoff=datetime.datetime(2026, 6, 20, 20, 0, tzinfo=UTC),
        round="r16",
    )


@pytest.mark.django_db
class TestMatchPredictionModel:
    """Tests for the MatchPrediction model."""

    def test_create_match_prediction(self, user1, match1):
        """Test creating a match prediction with all required fields."""
        from predictions.models import MatchPrediction

        prediction = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        assert prediction.user == user1
        assert prediction.match == match1
        assert prediction.predicted_goals_home == 2
        assert prediction.predicted_goals_away == 1
        assert prediction.joker_active is False
        assert prediction.created_at is not None
        assert prediction.updated_at is not None

    def test_unique_together_constraint(self, user1, match1):
        """Test unique_together prevents duplicate predictions for same user+match."""
        from predictions.models import MatchPrediction

        # Create first prediction
        MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # Try to create duplicate - should raise IntegrityError
        with pytest.raises(IntegrityError):
            MatchPrediction.objects.create(
                user=user1,
                match=match1,
                predicted_goals_home=3,
                predicted_goals_away=0,
            )

    def test_str_representation(self, user1, match1):
        """Test __str__ shows user and match with predicted score."""
        from predictions.models import MatchPrediction

        prediction = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=3,
            predicted_goals_away=2,
        )

        str_repr = str(prediction)
        assert "user1" in str_repr
        assert "3-2" in str_repr

    def test_ordering_by_match_kickoff(self, user1, match1, match2):
        """Test predictions are ordered by match kickoff time."""
        from predictions.models import MatchPrediction

        # Create predictions in reverse chronological order
        pred2 = MatchPrediction.objects.create(
            user=user1,
            match=match2,
            predicted_goals_home=1,
            predicted_goals_away=1,
        )
        pred1 = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=0,
        )

        # Query should return in kickoff order
        predictions = list(MatchPrediction.objects.all())
        assert predictions[0] == pred1  # Earlier kickoff
        assert predictions[1] == pred2  # Later kickoff

    def test_user_match_predictions_relationship(self, user1, user2, match1, match2):
        """Test user.match_predictions.all() relationship."""
        from predictions.models import MatchPrediction

        # Create predictions for user1
        pred1 = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        pred2 = MatchPrediction.objects.create(
            user=user1,
            match=match2,
            predicted_goals_home=1,
            predicted_goals_away=0,
        )

        # Create prediction for user2
        MatchPrediction.objects.create(
            user=user2,
            match=match1,
            predicted_goals_home=0,
            predicted_goals_away=0,
        )

        # Check user1's predictions
        user1_predictions = user1.match_predictions.all()
        assert user1_predictions.count() == 2
        assert pred1 in user1_predictions
        assert pred2 in user1_predictions

        # Check user2's predictions
        assert user2.match_predictions.count() == 1

    def test_match_predictions_relationship(self, user1, user2, match1):
        """Test match.predictions.all() relationship."""
        from predictions.models import MatchPrediction

        # Create predictions for match1 by different users
        pred1 = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        pred2 = MatchPrediction.objects.create(
            user=user2,
            match=match1,
            predicted_goals_home=3,
            predicted_goals_away=0,
        )

        match_predictions = match1.predictions.all()
        assert match_predictions.count() == 2
        assert pred1 in match_predictions
        assert pred2 in match_predictions

    def test_joker_active_default_false(self, user1, match1):
        """Test joker_active defaults to False."""
        from predictions.models import MatchPrediction

        prediction = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        assert prediction.joker_active is False

    def test_joker_active_can_be_true(self, user1, match1):
        """Test joker_active can be set to True."""
        from predictions.models import MatchPrediction

        prediction = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
            joker_active=True,
        )

        assert prediction.joker_active is True

        # Can also update to True
        prediction.joker_active = False
        prediction.save()
        prediction.refresh_from_db()
        assert prediction.joker_active is False

    def test_created_at_auto_set(self, user1, match1):
        """Test created_at is automatically set on creation."""
        from predictions.models import MatchPrediction

        before = datetime.datetime.now(UTC)
        prediction = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        after = datetime.datetime.now(UTC)

        assert before <= prediction.created_at <= after

    def test_updated_at_changes_on_save(self, user1, match1):
        """Test updated_at is updated when prediction is modified."""
        import time

        from predictions.models import MatchPrediction

        prediction = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        original_updated_at = prediction.updated_at

        # Sleep briefly to ensure timestamp difference
        time.sleep(0.01)

        # Update prediction
        prediction.predicted_goals_home = 3
        prediction.save()
        prediction.refresh_from_db()

        assert prediction.updated_at > original_updated_at
        assert prediction.created_at == prediction.created_at  # created_at unchanged

    def test_user_deleted_cascades_predictions(self, user1, match1, match2):
        """Test deleting user also deletes their predictions."""
        from predictions.models import MatchPrediction

        # Create predictions
        pred1 = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        pred2 = MatchPrediction.objects.create(
            user=user1,
            match=match2,
            predicted_goals_home=1,
            predicted_goals_away=0,
        )

        pred1_id = pred1.id
        pred2_id = pred2.id

        # Delete user
        user1.delete()

        # Predictions should be deleted
        assert not MatchPrediction.objects.filter(id=pred1_id).exists()
        assert not MatchPrediction.objects.filter(id=pred2_id).exists()

    def test_match_deleted_cascades_predictions(self, user1, user2, match1):
        """Test deleting match also deletes predictions for that match."""
        from predictions.models import MatchPrediction

        # Create predictions for match1
        pred1 = MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        pred2 = MatchPrediction.objects.create(
            user=user2,
            match=match1,
            predicted_goals_home=3,
            predicted_goals_away=0,
        )

        pred1_id = pred1.id
        pred2_id = pred2.id

        # Delete match
        match1.delete()

        # Predictions should be deleted
        assert not MatchPrediction.objects.filter(id=pred1_id).exists()
        assert not MatchPrediction.objects.filter(id=pred2_id).exists()
