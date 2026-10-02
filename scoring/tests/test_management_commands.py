"""Tests for scoring management commands."""

import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from conftest import make_match
from matches.models import Team
from predictions.models import MatchPrediction
from scoring.match_scoring import ScoringService
from scoring.models import LeaderboardSnapshot
from users.models import User


@pytest.fixture
def setup_data(db) -> dict:
    """Create test data for command tests."""
    team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
    team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)

    user = User.objects.create_user(
        username="testuser",
        password="test",
        total_points=100,  # Pre-existing points
        exact_match_count=5,
        jokers_used=2,
    )

    match = make_match(
        team_home=team_home,
        team_away=team_away,
        kickoff=timezone.now(),
        round="group",
        status="finished",
        goals_home=2,
        goals_away=1,
    )

    prediction = MatchPrediction.objects.create(
        user=user,
        match=match,
        predicted_goals_home=2,
        predicted_goals_away=1,
        points_earned=6,
        is_exact_match=True,
    )

    return {
        "team_home": team_home,
        "team_away": team_away,
        "user": user,
        "match": match,
        "prediction": prediction,
    }


class TestRecalculateScoresCommand:
    """Tests for recalculate_scores management command."""

    def test_recalculate_scores_resets_statistics(self, db, setup_data: dict) -> None:
        """Test command resets and recalculates all statistics."""
        out = StringIO()
        call_command("recalculate_scores", stdout=out)

        # User stats should be recalculated
        setup_data["user"].refresh_from_db()
        assert setup_data["user"].total_points == 6  # From single exact prediction
        assert setup_data["user"].exact_match_count == 1
        assert setup_data["user"].jokers_used == 0

    def test_recalculate_scores_output(self, db, setup_data: dict) -> None:
        """Test command produces expected output."""
        out = StringIO()
        call_command("recalculate_scores", stdout=out)
        output = out.getvalue()

        assert "Resetting" in output
        assert "Done" in output


class TestCreateSnapshotCommand:
    """Tests for create_snapshot management command."""

    def test_create_daily_snapshot(self, db, setup_data: dict) -> None:
        """Test creating daily snapshot via command."""
        out = StringIO()
        call_command("create_snapshot", "daily", stdout=out)

        snapshot = LeaderboardSnapshot.objects.first()
        assert snapshot is not None
        assert snapshot.snapshot_type == "daily"

    def test_create_final_snapshot(self, db, setup_data: dict) -> None:
        """Test creating final snapshot via command."""
        out = StringIO()
        call_command("create_snapshot", "final", stdout=out)

        snapshot = LeaderboardSnapshot.objects.first()
        assert snapshot is not None
        assert snapshot.snapshot_type == "final"


class TestExportLeaderboardCommand:
    """Tests for export_leaderboard management command."""

    def test_export_csv(self, db, setup_data: dict) -> None:
        """Test CSV export via command."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            out = StringIO()
            call_command("export_leaderboard", output_path, stdout=out)

            # Check file was created with content
            content = Path(output_path).read_text()
            assert "rank" in content
            assert "testuser" in content
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_export_csv_format(self, db, setup_data: dict) -> None:
        """Test CSV export contains proper headers."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            call_command("export_leaderboard", output_path, stdout=StringIO())

            content = Path(output_path).read_text()
            lines = content.strip().split("\n")

            # Check header
            header = lines[0]
            assert "rank" in header
            assert "username" in header
            assert "total_points" in header
            assert "exact_match_count" in header
            assert "jokers_used" in header
        finally:
            Path(output_path).unlink(missing_ok=True)


class TestRepairScoringCommand:
    """Tests for the repair_scoring management command."""

    @pytest.fixture
    def broken_scoring(self, db) -> dict:
        """Create a finished match whose prediction was never scored."""
        team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)
        user = User.objects.create_user(username="unscored_user", password="test")

        match = make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="finished",
            goals_home=2,
            goals_away=1,
        )
        prediction = MatchPrediction.objects.create(
            user=user,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        return {
            "team_home": team_home,
            "team_away": team_away,
            "user": user,
            "match": match,
            "prediction": prediction,
        }

    def test_check_detects_unscored_match(self, db, broken_scoring: dict) -> None:
        """--check reports the broken match, writes nothing and fails."""
        out = StringIO()

        with pytest.raises(CommandError):
            call_command("repair_scoring", "--check", stdout=out)

        assert str(broken_scoring["match"].pk) in out.getvalue()
        broken_scoring["prediction"].refresh_from_db()
        assert broken_scoring["prediction"].points_earned is None

    def test_check_passes_on_healthy_database(self, db, setup_data: dict) -> None:
        """--check succeeds when every prediction with a result is scored."""
        out = StringIO()
        call_command("repair_scoring", "--check", stdout=out)

        assert "No matches need scoring repair" in out.getvalue()

    def test_match_without_predictions_is_not_reported(self, db) -> None:
        """A finished match nobody predicted must not be reported as broken."""
        team_home = Team.objects.create(name="France", fifa_code="FRA")
        team_away = Team.objects.create(name="Spain", fifa_code="ESP")
        make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="finished",
            goals_home=1,
            goals_away=0,
        )

        out = StringIO()
        call_command("repair_scoring", "--check", stdout=out)

        assert "No matches need scoring repair" in out.getvalue()

    def test_repair_scores_unscored_predictions(self, db, broken_scoring: dict) -> None:
        """Repair scores the prediction and updates user totals and ranks."""
        call_command("repair_scoring", stdout=StringIO())

        prediction = broken_scoring["prediction"]
        user = broken_scoring["user"]
        prediction.refresh_from_db()
        user.refresh_from_db()

        assert prediction.points_earned is not None
        assert prediction.points_earned > 0
        assert prediction.is_exact_match is True
        assert user.total_points == prediction.points_earned
        assert user.global_rank == 1

    def test_repair_is_idempotent(self, db, broken_scoring: dict) -> None:
        """A second repair run changes no points and succeeds."""
        call_command("repair_scoring", stdout=StringIO())

        prediction = broken_scoring["prediction"]
        user = broken_scoring["user"]
        prediction.refresh_from_db()
        user.refresh_from_db()
        points_after_first = prediction.points_earned
        total_after_first = user.total_points

        out = StringIO()
        call_command("repair_scoring", stdout=out)

        prediction.refresh_from_db()
        user.refresh_from_db()
        assert "No matches need scoring repair" in out.getvalue()
        assert prediction.points_earned == points_after_first
        assert user.total_points == total_after_first

    def test_repair_continues_after_match_failure(self, db, broken_scoring: dict) -> None:
        """A failing match is reported, the remaining matches are still repaired."""
        second_match = make_match(
            team_home=broken_scoring["team_away"],
            team_away=broken_scoring["team_home"],
            kickoff=timezone.now() + timedelta(days=1),
            round="group",
            status="finished",
            goals_home=0,
            goals_away=3,
        )
        MatchPrediction.objects.create(
            user=broken_scoring["user"],
            match=second_match,
            predicted_goals_home=0,
            predicted_goals_away=3,
        )

        with patch.object(
            ScoringService,
            "score_all_predictions_for_match",
            side_effect=[ValueError("scoring boom"), 1],
        ) as mocked:
            with pytest.raises(CommandError):
                call_command("repair_scoring", stdout=StringIO(), stderr=StringIO())

        assert mocked.call_count == 2
