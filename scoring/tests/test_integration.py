"""Integration tests for the scoring system."""

from unittest.mock import patch

import pytest
from django.utils import timezone

from matches.models import Match, Team
from predictions.models import MatchPrediction
from scoring.match_scoring import ScoringService
from scoring.ranking_service import RankingService
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

    def test_champion_prediction_adds_to_total(self, db, tournament_setup: dict) -> None:
        """Test champion points are added to total correctly."""
        teams = tournament_setup["teams"]
        alice = tournament_setup["users"]["alice"]

        # Use update() to set predicted_champion and base points
        # This bypasses the champion change signal which would reset points
        User.objects.filter(pk=alice.pk).update(
            predicted_champion=teams["germany"],
            total_points=50,  # Simulate existing points from match predictions
        )

        # Create scheduled final match first (no results)
        final_match = Match.objects.create(
            team_home=teams["germany"],
            team_away=teams["brazil"],
            kickoff=timezone.now(),
            round="final",
            status="scheduled",
        )

        # Now add results and finish it
        # Match.save() automatically triggers update_live_champion_bonuses via signal
        final_match.goals_home = 1
        final_match.goals_away = 0
        final_match.status = "finished"
        final_match.save()

        alice.refresh_from_db()
        assert alice.total_points == 70  # 50 + 20 champion points


class TestRecalculationConsistency:
    """Test that recalculation produces consistent results."""

    def test_recalculation_matches_original_scoring(self, db, tournament_setup: dict) -> None:
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
        User.objects.filter(pk=alice.pk).update(total_points=0, exact_match_count=0, jokers_used=0)
        MatchPrediction.objects.filter(user=alice).update(points_earned=None, is_exact_match=False)

        ScoringService.score_all_predictions_for_match(match)

        alice.refresh_from_db()
        assert alice.total_points == original_points


class TestSnapshotCapturesState:
    """Test that snapshots correctly capture leaderboard state."""

    def test_snapshot_captures_current_state(self, db, tournament_setup: dict) -> None:
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


class TestRoundBasedRankingFullFlow:
    """Integration test for round-based ranking filtering."""

    def test_round_based_ranking_full_flow(self, db) -> None:
        """Integration test creating matches across rounds and verifying filtered rankings."""
        # Setup: Create teams
        germany = Team.objects.create(name="Germany", fifa_code="GER", odds_category="A")
        brazil = Team.objects.create(name="Brazil", fifa_code="BRA", odds_category="A")

        # Setup: Create users
        alice = User.objects.create_user(username="alice", password="test")
        bob = User.objects.create_user(username="bob", password="test")

        # Create matches across different rounds
        # Group stage match
        group_match = Match.objects.create(
            team_home=germany,
            team_away=brazil,
            round="group",
            kickoff=timezone.now(),
            status="scheduled",
        )

        # R16 match
        r16_match = Match.objects.create(
            team_home=germany,
            team_away=brazil,
            round="r16",
            kickoff=timezone.now(),
            status="scheduled",
        )

        # Quarter-final match
        qf_match = Match.objects.create(
            team_home=germany,
            team_away=brazil,
            round="qf",
            kickoff=timezone.now(),
            status="scheduled",
        )

        # Alice makes predictions
        MatchPrediction.objects.create(
            user=alice,
            match=group_match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        MatchPrediction.objects.create(
            user=alice,
            match=r16_match,
            predicted_goals_home=1,
            predicted_goals_away=0,
        )
        MatchPrediction.objects.create(
            user=alice,
            match=qf_match,
            predicted_goals_home=3,
            predicted_goals_away=2,
        )

        # Bob makes predictions
        MatchPrediction.objects.create(
            user=bob,
            match=group_match,
            predicted_goals_home=3,
            predicted_goals_away=1,
        )
        MatchPrediction.objects.create(
            user=bob,
            match=r16_match,
            predicted_goals_home=1,
            predicted_goals_away=0,
        )
        MatchPrediction.objects.create(
            user=bob,
            match=qf_match,
            predicted_goals_home=0,
            predicted_goals_away=1,
        )

        # Score group match (alice exact, bob tendency)
        group_match.goals_home = 2
        group_match.goals_away = 1
        group_match.status = "finished"
        group_match.save()

        # Score R16 match (both exact)
        r16_match.goals_home = 1
        r16_match.goals_away = 0
        r16_match.status = "finished"
        r16_match.save()

        # Score QF match (alice exact, bob wrong)
        qf_match.goals_home = 3
        qf_match.goals_away = 2
        qf_match.status = "finished"
        qf_match.save()

        # Test 1: Leaderboard after group stage only
        group_leaderboard = RankingService.get_leaderboard_up_to_round("group")
        assert len(group_leaderboard) == 2
        # Alice: 6 (exact) * 1 (group multiplier) = 6
        # Bob: 4 (tendency + one goal) * 1 (group multiplier) = 4
        assert group_leaderboard[0]["username"] == "alice"
        assert group_leaderboard[0]["total_points"] == 6
        assert group_leaderboard[1]["username"] == "bob"
        assert group_leaderboard[1]["total_points"] == 4

        # Test 2: Leaderboard through R16
        r16_leaderboard = RankingService.get_leaderboard_up_to_round("r16")
        assert len(r16_leaderboard) == 2
        # Alice: 6 (group) + 6 * 2 (r16 exact) = 6 + 12 = 18
        # Bob: 4 (group) + 6 * 2 (r16 exact) = 4 + 12 = 16
        assert r16_leaderboard[0]["username"] == "alice"
        assert r16_leaderboard[0]["total_points"] == 18
        assert r16_leaderboard[1]["username"] == "bob"
        assert r16_leaderboard[1]["total_points"] == 16

        # Test 3: Leaderboard through QF
        qf_leaderboard = RankingService.get_leaderboard_up_to_round("qf")
        assert len(qf_leaderboard) == 2
        # Alice: 18 (through r16) + 6 * 3 (qf exact) = 18 + 18 = 36
        # Bob: 16 (through r16) + 0 (qf wrong) = 16
        assert qf_leaderboard[0]["username"] == "alice"
        assert qf_leaderboard[0]["total_points"] == 36
        assert qf_leaderboard[1]["username"] == "bob"
        assert qf_leaderboard[1]["total_points"] == 16

        # Test 4: Live view includes all rounds
        live_leaderboard = RankingService.get_current_leaderboard()
        # Should match cached User fields which were updated by match saves
        alice.refresh_from_db()
        bob.refresh_from_db()
        assert live_leaderboard[0]["username"] == "alice"
        assert live_leaderboard[0]["total_points"] == alice.total_points
        assert live_leaderboard[1]["username"] == "bob"
        assert live_leaderboard[1]["total_points"] == bob.total_points

        # Test 5: Verify ranking progression (points increase through rounds)
        group_alice_points = next(e for e in group_leaderboard if e["username"] == "alice")[
            "total_points"
        ]
        r16_alice_points = next(e for e in r16_leaderboard if e["username"] == "alice")[
            "total_points"
        ]
        qf_alice_points = next(e for e in qf_leaderboard if e["username"] == "alice")[
            "total_points"
        ]

        # Points should increase as rounds progress
        assert group_alice_points < r16_alice_points < qf_alice_points

        # Test 6: Verify Olympic ranking is maintained in all views
        for leaderboard in [group_leaderboard, r16_leaderboard, qf_leaderboard]:
            # All leaderboards should have rank 1 for alice, rank 2 for bob
            assert leaderboard[0]["rank"] == 1
            assert leaderboard[1]["rank"] == 2


class TestScoringReliabilityIntegration:
    """Integration tests for scoring reliability fixes."""

    def test_champion_scoring_idempotency_integration(self, db) -> None:
        """Test champion scoring called multiple times doesn't double-award points."""
        from django.utils import timezone

        from matches.models import Match, Team
        from scoring.champion_scoring import update_live_champion_bonuses
        from users.models import User

        # Create champion team (category A = 20 points)
        champion = Team.objects.create(
            name="Germany",
            fifa_code="GER",
            odds_category="A",
        )
        runner_up = Team.objects.create(
            name="Brazil",
            fifa_code="BRA",
            odds_category="B",
        )

        # Create finished final
        Match.objects.create(
            team_home=champion,
            team_away=runner_up,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=1,
            goals_away=0,
        )

        # Create user
        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=champion,
        )

        # Update champion bonuses multiple times
        count1 = update_live_champion_bonuses()
        assert count1 == 1

        count2 = update_live_champion_bonuses()
        assert count2 == 1  # User still awarded (bonuses are recalculated)

        count3 = update_live_champion_bonuses()
        assert count3 == 1  # User still awarded (bonuses are recalculated)

        # Verify user only got 20 points, not 60 (reset and re-awarded each time)
        user.refresh_from_db()
        assert user.total_points == 20
        assert user.champion_bonus_points == 20

    def test_locktime_consistency_across_views(self, db) -> None:
        """Test locktime is consistent between page load and HTMX updates."""
        from datetime import timedelta

        from django.utils import timezone

        from matches.models import Match, Team
        from predictions.services import PredictionLimitService
        from users.models import User

        # Create user
        User.objects.create_user(
            username="testuser",
            password="testpass",
        )

        # Create teams
        team_home = Team.objects.create(name="Germany", fifa_code="GER", odds_category="A")
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", odds_category="B")

        # Create match with kickoff in 5 minutes
        kickoff = timezone.now() + timedelta(minutes=5)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            status="scheduled",
        )

        # Test 4 minutes before kickoff - should NOT be locked
        reference_time_unlocked = kickoff - timedelta(minutes=4)
        assert PredictionLimitService.is_match_locked(match, reference_time_unlocked) is False

        # Test 2 minutes before kickoff - should be locked
        reference_time_locked = kickoff - timedelta(minutes=2)
        assert PredictionLimitService.is_match_locked(match, reference_time_locked) is True

        # Test exactly 3 minutes - should be locked (boundary)
        reference_time_boundary = kickoff - timedelta(minutes=3)
        assert PredictionLimitService.is_match_locked(match, reference_time_boundary) is True


class TestScoringFailureHandling:
    """Test that scoring failures are surfaced and leave no partial state."""

    @pytest.fixture
    def scored_setup(self, db) -> dict:
        """Create a match with one unscored prediction."""
        team_home = Team.objects.create(name="Germany", fifa_code="GER", odds_category="A")
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", odds_category="B")
        user = User.objects.create_user(username="alice", password="test")

        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="group",
            status="scheduled",
        )
        prediction = MatchPrediction.objects.create(
            user=user,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )

        return {"match": match, "prediction": prediction, "user": user}

    def test_receiver_reraises_scoring_error(self, db, scored_setup: dict) -> None:
        """A failure in ScoringService must propagate to the caller of Match.save()."""
        match = scored_setup["match"]

        with patch.object(
            ScoringService,
            "score_all_predictions_for_match",
            side_effect=RuntimeError("scoring boom"),
        ):
            match.goals_home = 2
            match.goals_away = 1
            match.status = "finished"

            with pytest.raises(RuntimeError, match="scoring boom"):
                match.save()

    def test_failed_scoring_leaves_no_partial_state(self, db, scored_setup: dict) -> None:
        """A failure after scoring must roll back predictions and user totals."""
        match = scored_setup["match"]
        prediction = scored_setup["prediction"]
        user = scored_setup["user"]

        with patch.object(
            RankingService,
            "update_all_user_ranks",
            side_effect=RuntimeError("ranking boom"),
        ):
            match.goals_home = 2
            match.goals_away = 1
            match.status = "finished"

            with pytest.raises(RuntimeError, match="ranking boom"):
                match.save()

        prediction.refresh_from_db()
        user.refresh_from_db()
        assert prediction.points_earned is None
        assert prediction.is_exact_match is False
        assert user.total_points == 0
        assert user.exact_match_count == 0
