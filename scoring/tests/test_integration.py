"""Integration tests for the scoring system."""

import pytest
from django.utils import timezone

from matches.models import Match, Team
from predictions.models import MatchPrediction
from scoring.services import RankingService, ScoringService
from users.models import User


@pytest.fixture
def tournament_setup(db) -> dict:
    """Set up a mini tournament scenario."""
    # Teams
    germany = Team.objects.create(name="Germany", fifa_code="GER", odds_category="A")
    brazil = Team.objects.create(name="Brazil", fifa_code="BRA", odds_category="B")
    france = Team.objects.create(name="France", fifa_code="FRA", odds_category="A")
    argentina = Team.objects.create(name="Argentina", fifa_code="ARG", odds_category="A")

    # Users
    alice = User.objects.create_user(username="alice", password="test")
    bob = User.objects.create_user(username="bob", password="test")
    carol = User.objects.create_user(username="carol", password="test")

    return {
        "teams": {
            "germany": germany,
            "brazil": brazil,
            "france": france,
            "argentina": argentina,
        },
        "users": {
            "alice": alice,
            "bob": bob,
            "carol": carol,
        },
    }


class TestEndToEndScoring:
    """Test complete scoring flow from predictions to leaderboard."""

    def test_predictions_to_match_result_to_scoring_to_leaderboard(
        self, db, tournament_setup: dict
    ) -> None:
        """Test complete flow: predictions → result → scoring → leaderboard."""
        teams = tournament_setup["teams"]
        users = tournament_setup["users"]

        # Create a group stage match
        match = Match.objects.create(
            team_home=teams["germany"],
            team_away=teams["brazil"],
            kickoff=timezone.now(),
            round="group",
            status="scheduled",
        )

        # Users make predictions
        # Alice: exact prediction
        MatchPrediction.objects.create(
            user=users["alice"],
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        # Bob: tendency only
        MatchPrediction.objects.create(
            user=users["bob"],
            match=match,
            predicted_goals_home=5,
            predicted_goals_away=0,
        )
        # Carol: wrong prediction
        MatchPrediction.objects.create(
            user=users["carol"],
            match=match,
            predicted_goals_home=0,
            predicted_goals_away=3,
        )

        # Match finishes with result 2-1
        match.goals_home = 2
        match.goals_away = 1
        match.status = "finished"
        match.save()  # This triggers scoring

        # Refresh users from DB
        for user in users.values():
            user.refresh_from_db()

        # Check points
        assert users["alice"].total_points == 6  # Exact
        assert users["bob"].total_points == 3  # Tendency only
        assert users["carol"].total_points == 0  # Wrong

        # Check leaderboard
        leaderboard = RankingService.get_current_leaderboard()

        assert leaderboard[0]["username"] == "alice"
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[1]["username"] == "bob"
        assert leaderboard[1]["rank"] == 2


class TestMultipleMatchesWithMultipliers:
    """Test scoring across multiple matches with different multipliers."""

    def test_group_and_knockout_matches(self, db, tournament_setup: dict) -> None:
        """Test scoring across group stage and knockout rounds."""
        teams = tournament_setup["teams"]
        alice = tournament_setup["users"]["alice"]

        # Group stage match (x1 multiplier) - create without results first
        group_match = Match.objects.create(
            team_home=teams["germany"],
            team_away=teams["brazil"],
            kickoff=timezone.now(),
            round="group",
            status="scheduled",
        )

        MatchPrediction.objects.create(
            user=alice,
            match=group_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # Add result and save
        group_match.goals_home = 2
        group_match.goals_away = 1
        group_match.status = "finished"
        group_match.save()

        # Quarter-final match (x3 multiplier)
        qf_match = Match.objects.create(
            team_home=teams["france"],
            team_away=teams["argentina"],
            kickoff=timezone.now(),
            round="qf",
            status="scheduled",
        )

        MatchPrediction.objects.create(
            user=alice,
            match=qf_match,
            predicted_goals_home=1,
            predicted_goals_away=0,
        )

        # Add result and save
        qf_match.goals_home = 1
        qf_match.goals_away = 0
        qf_match.status = "finished"
        qf_match.save()

        alice.refresh_from_db()

        # 6 * 1 (group) + 6 * 3 (qf) = 6 + 18 = 24
        assert alice.total_points == 24
        assert alice.exact_match_count == 2


class TestJokerImpact:
    """Test joker impact on scoring."""

    def test_joker_doubles_knockout_points(self, db, tournament_setup: dict) -> None:
        """Test joker doubles points in knockout round."""
        teams = tournament_setup["teams"]
        alice = tournament_setup["users"]["alice"]

        # Round of 16 match (x2 multiplier) - create without results first
        match = Match.objects.create(
            team_home=teams["germany"],
            team_away=teams["brazil"],
            kickoff=timezone.now(),
            round="r16",
            status="scheduled",
        )

        # Alice predicts with joker
        MatchPrediction.objects.create(
            user=alice,
            match=match,
            predicted_goals_home=3,
            predicted_goals_away=0,
            joker_active=True,
        )

        # Add result and save
        match.goals_home = 3
        match.goals_away = 0
        match.status = "finished"
        match.save()

        alice.refresh_from_db()

        # 6 base * 2 round * 2 joker = 24
        assert alice.total_points == 24
        assert alice.jokers_used == 1


class TestChampionPredictionFlow:
    """Test champion prediction scoring flow."""

    def test_champion_prediction_adds_to_total(
        self, db, tournament_setup: dict
    ) -> None:
        """Test champion points are added to total correctly."""
        teams = tournament_setup["teams"]
        alice = tournament_setup["users"]["alice"]

        # Set Germany as champion (category A = 20 pts)
        teams["germany"].is_champion = True
        teams["germany"].save()

        # Alice predicted Germany as champion
        alice.predicted_champion = teams["germany"]
        alice.total_points = 50  # Existing points from match predictions
        alice.save()

        # Create scheduled final match first (no results)
        final_match = Match.objects.create(
            team_home=teams["germany"],
            team_away=teams["brazil"],
            kickoff=timezone.now(),
            round="final",
            status="scheduled",
        )

        # Now add results and finish it (this triggers champion scoring)
        final_match.goals_home = 1
        final_match.goals_away = 0
        final_match.status = "finished"
        final_match.save()

        alice.refresh_from_db()
        assert alice.total_points == 70  # 50 + 20 champion points


class TestRecalculationConsistency:
    """Test that recalculation produces consistent results."""

    def test_recalculation_matches_original_scoring(
        self, db, tournament_setup: dict
    ) -> None:
        """Test that recalculating scores produces same result."""
        teams = tournament_setup["teams"]
        alice = tournament_setup["users"]["alice"]

        # Create match without results first
        match = Match.objects.create(
            team_home=teams["germany"],
            team_away=teams["brazil"],
            kickoff=timezone.now(),
            round="group",
            status="scheduled",
        )

        MatchPrediction.objects.create(
            user=alice,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        # Add results (triggers scoring)
        match.goals_home = 2
        match.goals_away = 1
        match.status = "finished"
        match.save()

        alice.refresh_from_db()
        original_points = alice.total_points
        assert original_points == 6  # Verify scoring happened

        # Reset and recalculate
        User.objects.filter(pk=alice.pk).update(
            total_points=0, exact_match_count=0, jokers_used=0
        )
        MatchPrediction.objects.filter(user=alice).update(
            points_earned=None, is_exact_match=False
        )

        ScoringService.score_all_predictions_for_match(match)

        alice.refresh_from_db()
        assert alice.total_points == original_points


class TestSnapshotCapturesState:
    """Test that snapshots correctly capture leaderboard state."""

    def test_snapshot_captures_current_state(
        self, db, tournament_setup: dict
    ) -> None:
        """Test snapshot captures rankings at time of creation."""
        users = tournament_setup["users"]

        # Set up different points
        users["alice"].total_points = 100
        users["alice"].save()
        users["bob"].total_points = 80
        users["bob"].save()
        users["carol"].total_points = 60
        users["carol"].save()

        # Create snapshot
        snapshot = RankingService.create_snapshot("daily")

        # Verify snapshot data
        assert len(snapshot.data) == 3
        assert snapshot.data[0]["username"] == "alice"
        assert snapshot.data[0]["total_points"] == 100
        assert snapshot.data[1]["username"] == "bob"
        assert snapshot.data[2]["username"] == "carol"

        # Change points after snapshot
        users["carol"].total_points = 200
        users["carol"].save()

        # Snapshot should still have original values
        snapshot.refresh_from_db()
        assert snapshot.data[2]["total_points"] == 60
