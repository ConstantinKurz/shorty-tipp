"""Tests for scoring management commands."""

import tempfile
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.utils import timezone

from matches.models import Match, Team
from predictions.models import MatchPrediction
from scoring.models import LeaderboardSnapshot
from users.models import User


@pytest.fixture
def setup_data(db) -> dict:
    """Create test data for command tests."""
    team_home = Team.objects.create(name="Germany", fifa_code="GER", odds_category="A")
    team_away = Team.objects.create(name="Brazil", fifa_code="BRA", odds_category="B")

    user = User.objects.create_user(
        username="testuser",
        password="test",
        total_points=100,  # Pre-existing points
        exact_match_count=5,
        jokers_used=2,
    )

    match = Match.objects.create(
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

    def test_recalculate_scores_resets_statistics(
        self, db, setup_data: dict
    ) -> None:
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
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
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
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
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
