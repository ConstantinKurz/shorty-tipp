"""Tests for leaderboard export helpers in ``scoring/exports.py``."""

import tempfile
from io import StringIO
from pathlib import Path

import pytest
import reportlab.rl_config
from django.core.management import call_command
from django.utils import timezone

from conftest import make_match
from matches.models import Team
from predictions.models import MatchPrediction
from scoring.exports import generate_leaderboard_csv, generate_leaderboard_pdf
from scoring.ranking_service import RankingService
from users.models import User


@pytest.fixture
def leaderboard() -> list[dict]:
    """Return a leaderboard payload in the shape RankingService produces."""
    return [
        {
            "user_id": 1,
            "rank": 1,
            "username": "alice",
            "total_points": 42,
            "exact_match_count": 3,
            "jokers_used": 1,
        },
        {
            "user_id": 2,
            "rank": 2,
            "username": "bob",
            "total_points": 17,
            "exact_match_count": 1,
            "jokers_used": 0,
        },
    ]


@pytest.fixture
def deterministic_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make reportlab output reproducible by removing timestamps and random IDs."""
    monkeypatch.setattr(reportlab.rl_config, "invariant", 1)


@pytest.fixture
def scored_prediction(db) -> None:
    """Create a single scored prediction so the leaderboard is non-empty."""
    team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
    team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)
    user = User.objects.create_user(username="testuser", password="test", total_points=6)
    match = make_match(
        team_home=team_home,
        team_away=team_away,
        kickoff=timezone.now(),
        round="group",
        status="finished",
        goals_home=2,
        goals_away=1,
    )
    MatchPrediction.objects.create(
        user=user,
        match=match,
        predicted_goals_home=2,
        predicted_goals_away=1,
        points_earned=6,
        is_exact_match=True,
    )


class TestGenerateLeaderboardPdf:
    """Tests for generate_leaderboard_pdf()."""

    def test_returns_pdf_bytes(self, leaderboard: list[dict]) -> None:
        """PDF generation returns non-empty bytes with a PDF header."""
        content = generate_leaderboard_pdf(leaderboard)

        assert isinstance(content, bytes)
        assert content
        assert content.startswith(b"%PDF")

    def test_empty_leaderboard_still_produces_pdf(self) -> None:
        """An empty leaderboard produces a PDF containing only the header row."""
        content = generate_leaderboard_pdf([])

        assert content.startswith(b"%PDF")


class TestExportLeaderboardCommandPdf:
    """Tests for the export_leaderboard command PDF path."""

    def test_pdf_file_matches_generate_leaderboard_pdf(
        self, db, scored_prediction: None, deterministic_pdf: None
    ) -> None:
        """The command writes exactly what generate_leaderboard_pdf() returns."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = Path(f.name)

        try:
            call_command("export_leaderboard", str(output_path), "--format=pdf", stdout=StringIO())

            expected = generate_leaderboard_pdf(RankingService.get_current_leaderboard())
            written = output_path.read_bytes()

            assert written.startswith(b"%PDF")
            assert written == expected
        finally:
            output_path.unlink(missing_ok=True)

    def test_csv_export_unaffected(self, db, scored_prediction: None) -> None:
        """The CSV path still writes the same content as generate_leaderboard_csv()."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            call_command("export_leaderboard", str(output_path), "--format=csv", stdout=StringIO())

            content = output_path.read_text()
            expected = generate_leaderboard_csv(RankingService.get_current_leaderboard())

            assert content.replace("\r\n", "\n") == expected.replace("\r\n", "\n")
        finally:
            output_path.unlink(missing_ok=True)
