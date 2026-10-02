"""Tests for RankingService."""

import pytest
from django.utils import timezone

from conftest import make_match
from scoring.ranking_service import RankingService
from users.models import User


@pytest.fixture
def users_with_stats(db) -> list[User]:
    """Create users with various statistics for ranking tests."""
    users = [
        User.objects.create_user(
            username="alice",
            password="test",
            total_points=100,
            exact_match_count=8,
            jokers_used=5,
        ),
        User.objects.create_user(
            username="bob",
            password="test",
            total_points=95,
            exact_match_count=7,
            jokers_used=5,
        ),
        User.objects.create_user(
            username="carol",
            password="test",
            total_points=95,
            exact_match_count=7,
            jokers_used=5,
        ),
        User.objects.create_user(
            username="dave",
            password="test",
            total_points=90,
            exact_match_count=6,
            jokers_used=4,
        ),
        User.objects.create_user(
            username="eve",
            password="test",
            total_points=90,
            exact_match_count=6,
            jokers_used=5,
        ),
    ]
    return users


class TestRankingByPoints:
    """Test basic ranking by total points."""

    def test_ranking_orders_by_points_descending(self, db, users_with_stats: list[User]) -> None:
        """Test users are ranked by total points (highest first)."""
        leaderboard = RankingService.get_current_leaderboard()

        assert leaderboard[0]["username"] == "alice"
        assert leaderboard[0]["total_points"] == 100
        assert leaderboard[0]["rank"] == 1


class TestTiebreakers:
    """Test Olympic tiebreaker rules per Shortytipp rules section 10."""

    def test_tiebreaker_exact_matches(self, db) -> None:
        """Test first tiebreaker: exact match count (higher is better)."""
        User.objects.create_user(
            username="more_exact",
            password="test",
            total_points=50,
            exact_match_count=5,
            jokers_used=3,
        )
        User.objects.create_user(
            username="less_exact",
            password="test",
            total_points=50,
            exact_match_count=3,
            jokers_used=3,
        )

        leaderboard = RankingService.get_current_leaderboard()

        # Same points, more exact matches wins
        assert leaderboard[0]["username"] == "more_exact"
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[1]["username"] == "less_exact"
        assert leaderboard[1]["rank"] == 2

    def test_tiebreaker_jokers_used(self, db) -> None:
        """Test second tiebreaker: jokers used (fewer is better)."""
        User.objects.create_user(
            username="fewer_jokers",
            password="test",
            total_points=50,
            exact_match_count=5,
            jokers_used=2,
        )
        User.objects.create_user(
            username="more_jokers",
            password="test",
            total_points=50,
            exact_match_count=5,
            jokers_used=5,
        )

        leaderboard = RankingService.get_current_leaderboard()

        # Same points and exact, fewer jokers wins
        assert leaderboard[0]["username"] == "fewer_jokers"
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[1]["username"] == "more_jokers"
        assert leaderboard[1]["rank"] == 2


class TestSharedRanks:
    """Test shared rank handling."""

    def test_identical_stats_share_rank(self, db, users_with_stats: list[User]) -> None:
        """Test users with identical stats share the same rank."""
        leaderboard = RankingService.get_current_leaderboard()

        # bob and carol have identical stats (95 pts, 7 exact, 5 jokers)
        bob = next(e for e in leaderboard if e["username"] == "bob")
        carol = next(e for e in leaderboard if e["username"] == "carol")

        assert bob["rank"] == carol["rank"] == 2

    def test_rank_numbering_with_ties(self, db, users_with_stats: list[User]) -> None:
        """Test rank numbering skips after ties (1, 2, 2, 4 not 1, 2, 2, 3)."""
        leaderboard = RankingService.get_current_leaderboard()

        # alice: rank 1 (100 pts)
        # bob, carol: rank 2 (tied at 95 pts)
        # dave: rank 4 (90 pts, 4 jokers - fewer than eve)
        # eve: rank 5 (90 pts, 5 jokers)
        alice = next(e for e in leaderboard if e["username"] == "alice")
        bob = next(e for e in leaderboard if e["username"] == "bob")
        carol = next(e for e in leaderboard if e["username"] == "carol")
        dave = next(e for e in leaderboard if e["username"] == "dave")
        eve = next(e for e in leaderboard if e["username"] == "eve")

        assert alice["rank"] == 1
        assert bob["rank"] == 2
        assert carol["rank"] == 2
        assert dave["rank"] == 4  # Skipped 3 because of tie
        assert eve["rank"] == 5


class TestEdgeCases:
    """Test edge cases in ranking."""

    def test_empty_leaderboard(self, db) -> None:
        """Test empty leaderboard returns empty list."""
        leaderboard = RankingService.get_current_leaderboard()
        assert leaderboard == []

    def test_single_user_leaderboard(self, db) -> None:
        """Test leaderboard with single user."""
        User.objects.create_user(
            username="lonely",
            password="test",
            total_points=50,
            exact_match_count=3,
            jokers_used=2,
        )

        leaderboard = RankingService.get_current_leaderboard()

        assert len(leaderboard) == 1
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[0]["username"] == "lonely"

    def test_inactive_users_excluded(self, db) -> None:
        """Test inactive users are not included in leaderboard."""
        User.objects.create_user(
            username="active",
            password="test",
            total_points=50,
            is_active=True,
        )
        User.objects.create_user(
            username="inactive",
            password="test",
            total_points=100,  # Higher points but inactive
            is_active=False,
        )

        leaderboard = RankingService.get_current_leaderboard()

        assert len(leaderboard) == 1
        assert leaderboard[0]["username"] == "active"


@pytest.fixture
def matches_by_round(db):
    """Create matches across different tournament rounds."""
    from matches.models import Team

    team_a = Team.objects.create(name="Team A", fifa_code="TEA")
    team_b = Team.objects.create(name="Team B", fifa_code="TEB")

    matches = {
        "group": make_match(
            team_home=team_a,
            team_away=team_b,
            round="group",
            kickoff=timezone.now(),
            status="finished",
            goals_home=2,
            goals_away=1,
        ),
        "r16": make_match(
            team_home=team_a,
            team_away=team_b,
            round="r16",
            kickoff=timezone.now(),
            status="finished",
            goals_home=3,
            goals_away=0,
        ),
        "qf": make_match(
            team_home=team_a,
            team_away=team_b,
            round="qf",
            kickoff=timezone.now(),
            status="finished",
            goals_home=1,
            goals_away=1,
        ),
        "final": make_match(
            team_home=team_a,
            team_away=team_b,
            round="final",
            kickoff=timezone.now(),
            status="finished",
            goals_home=2,
            goals_away=2,
        ),
    }
    return matches


@pytest.fixture
def scored_predictions(db, matches_by_round):
    """Create users with scored predictions across rounds."""
    from predictions.models import MatchPrediction

    user_a = User.objects.create_user(username="user_a", password="test")
    user_b = User.objects.create_user(username="user_b", password="test")

    # User A predictions (exact match in group, tendency in r16)
    MatchPrediction.objects.create(
        user=user_a,
        match=matches_by_round["group"],
        predicted_goals_home=2,
        predicted_goals_away=1,
        points_earned=6,  # Exact match: 6 * 1 (group multiplier)
        is_exact_match=True,
    )
    MatchPrediction.objects.create(
        user=user_a,
        match=matches_by_round["r16"],
        predicted_goals_home=2,
        predicted_goals_away=0,
        points_earned=6,  # Tendency: 3 * 2 (r16 multiplier)
        is_exact_match=False,
    )
    MatchPrediction.objects.create(
        user=user_a,
        match=matches_by_round["qf"],
        predicted_goals_home=1,
        predicted_goals_away=1,
        points_earned=18,  # Exact: 6 * 3 (qf multiplier)
        is_exact_match=True,
    )

    # User B predictions (tendency in group, exact in r16)
    MatchPrediction.objects.create(
        user=user_b,
        match=matches_by_round["group"],
        predicted_goals_home=3,
        predicted_goals_away=1,
        points_earned=3,  # Tendency: 3 * 1 (group multiplier)
        is_exact_match=False,
    )
    MatchPrediction.objects.create(
        user=user_b,
        match=matches_by_round["r16"],
        predicted_goals_home=3,
        predicted_goals_away=0,
        points_earned=12,  # Exact: 6 * 2 (r16 multiplier)
        is_exact_match=True,
    )
    MatchPrediction.objects.create(
        user=user_b,
        match=matches_by_round["qf"],
        predicted_goals_home=2,
        predicted_goals_away=0,
        points_earned=0,  # Wrong
        is_exact_match=False,
    )

    return {"user_a": user_a, "user_b": user_b}


class TestRankingServiceRoundFiltering:
    """Test round-based filtering of leaderboards."""

    def test_get_leaderboard_up_to_round_group_stage(
        self, db, matches_by_round, scored_predictions
    ):
        """Test filtering by group stage only."""
        leaderboard = RankingService.get_leaderboard_up_to_round("group")

        assert len(leaderboard) == 2
        # User A: 6 points from group
        # User B: 3 points from group
        assert leaderboard[0]["username"] == "user_a"
        assert leaderboard[0]["total_points"] == 6
        assert leaderboard[1]["username"] == "user_b"
        assert leaderboard[1]["total_points"] == 3

    def test_get_leaderboard_up_to_round_r16(self, db, matches_by_round, scored_predictions):
        """Test filtering includes group + r32 + r16."""
        leaderboard = RankingService.get_leaderboard_up_to_round("r16")

        assert len(leaderboard) == 2
        # User B: 3 (group) + 12 (r16) = 15 total
        # User A: 6 (group) + 6 (r16) = 12 total
        assert leaderboard[0]["username"] == "user_b"
        assert leaderboard[0]["total_points"] == 15
        assert leaderboard[1]["username"] == "user_a"
        assert leaderboard[1]["total_points"] == 12

    def test_get_leaderboard_up_to_round_qf(self, db, matches_by_round, scored_predictions):
        """Test filtering through quarter-finals."""
        leaderboard = RankingService.get_leaderboard_up_to_round("qf")

        assert len(leaderboard) == 2
        # User A: 6 (group) + 6 (r16) + 18 (qf) = 30 total
        # User B: 3 (group) + 12 (r16) + 0 (qf) = 15 total
        assert leaderboard[0]["username"] == "user_a"
        assert leaderboard[0]["total_points"] == 30
        assert leaderboard[1]["username"] == "user_b"
        assert leaderboard[1]["total_points"] == 15

    def test_get_leaderboard_up_to_round_final(self, db, matches_by_round, scored_predictions):
        """Test final round includes all matches."""
        live = RankingService.get_current_leaderboard()
        final = RankingService.get_leaderboard_up_to_round("final")

        # Should be identical (both include all rounds)
        assert len(live) == len(final)
        for live_entry, final_entry in zip(live, final, strict=True):
            assert live_entry["username"] == final_entry["username"]
            assert live_entry["total_points"] == final_entry["total_points"]

    def test_get_leaderboard_up_to_round_none_returns_live(self, db, scored_predictions):
        """Test None parameter returns all finished matches."""
        live = RankingService.get_current_leaderboard()
        none_result = RankingService.get_leaderboard_up_to_round(None)

        assert live == none_result

    def test_get_leaderboard_up_to_round_invalid_code(self, db, scored_predictions):
        """Test invalid round code returns live view."""
        live = RankingService.get_current_leaderboard()
        invalid = RankingService.get_leaderboard_up_to_round("invalid")

        assert live == invalid

    def test_get_leaderboard_up_to_round_no_finished_matches(self, db):
        """Test round with no finished matches returns users with zero points."""
        from matches.models import Team

        team_a = Team.objects.create(name="Team A", fifa_code="TAA")
        team_b = Team.objects.create(name="Team B", fifa_code="TBB")

        # Create scheduled match (not finished)
        make_match(
            team_home=team_a,
            team_away=team_b,
            round="group",
            kickoff=timezone.now(),
            status="scheduled",
        )

        User.objects.create_user(username="test_user", password="test")

        leaderboard = RankingService.get_leaderboard_up_to_round("group")
        # Users should appear with 0 points when no matches are finished
        assert len(leaderboard) == 1
        assert leaderboard[0]["username"] == "test_user"
        assert leaderboard[0]["total_points"] == 0
        assert leaderboard[0]["exact_match_count"] == 0
        assert leaderboard[0]["jokers_used"] == 0

    def test_get_leaderboard_up_to_round_ranking_correctness(self, db, matches_by_round):
        """Test olympic ranking with filtered data."""
        from predictions.models import MatchPrediction

        user_c = User.objects.create_user(username="user_c", password="test")
        user_d = User.objects.create_user(username="user_d", password="test")

        # Both users predict group match
        MatchPrediction.objects.create(
            user=user_c,
            match=matches_by_round["group"],
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=6,
            is_exact_match=True,
            joker_active=False,
        )
        MatchPrediction.objects.create(
            user=user_d,
            match=matches_by_round["group"],
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=6,
            is_exact_match=True,
            joker_active=True,  # Used joker
        )

        leaderboard = RankingService.get_leaderboard_up_to_round("group")

        # Both have same points and exact matches, but user_c has fewer jokers used
        assert leaderboard[0]["username"] == "user_c"
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[0]["jokers_used"] == 0
        assert leaderboard[1]["username"] == "user_d"
        assert leaderboard[1]["rank"] == 2
        assert leaderboard[1]["jokers_used"] == 1

    def test_get_leaderboard_up_to_round_exact_match_count(
        self, db, matches_by_round, scored_predictions
    ):
        """Test exact_match_count is calculated correctly for filtered rounds."""
        leaderboard = RankingService.get_leaderboard_up_to_round("r16")

        user_a_entry = next(e for e in leaderboard if e["username"] == "user_a")
        user_b_entry = next(e for e in leaderboard if e["username"] == "user_b")

        # User A: 1 exact in group, 0 in r16 = 1 total through r16
        # User B: 0 exact in group, 1 in r16 = 1 total through r16
        assert user_a_entry["exact_match_count"] == 1
        assert user_b_entry["exact_match_count"] == 1


class TestBackwardCompatibility:
    """Test that refactored get_current_leaderboard maintains existing behavior."""

    def test_get_current_leaderboard_backward_compatible(self, db, users_with_stats):
        """Test that refactored method maintains existing behavior."""
        leaderboard = RankingService.get_current_leaderboard()

        assert isinstance(leaderboard, list)
        assert len(leaderboard) == 5

        # Verify structure matches existing expectations
        for entry in leaderboard:
            assert "rank" in entry
            assert "user_id" in entry
            assert "username" in entry
            assert "total_points" in entry
            assert "exact_match_count" in entry
            assert "jokers_used" in entry

        # Verify ordering (alice highest points)
        assert leaderboard[0]["username"] == "alice"
        assert leaderboard[0]["total_points"] == 100


class TestLiveChampionBonusInLeaderboard:
    """Test that live champion bonus is stored in total_points during final."""

    def test_live_champion_bonus_stored_in_total_points(self, db):
        """Test live bonus is added to total_points during final."""
        from matches.models import Team
        from scoring.champion_scoring import update_live_champion_bonuses

        # Create teams
        team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)

        # Create live final with home team leading
        make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="live",
            goals_home=2,
            goals_away=1,
        )

        # Create users with champion predictions
        user_correct = User.objects.create_user(
            username="correct_predictor",
            password="test",
            predicted_champion=team_home,
            total_points=50,
            champion_bonus_points=0,
        )
        user_wrong = User.objects.create_user(
            username="wrong_predictor",
            password="test",
            predicted_champion=team_away,
            total_points=60,
            champion_bonus_points=0,
        )

        # Update live champion bonuses (normally called by Match.save())
        count = update_live_champion_bonuses()
        assert count == 1

        # Refresh users from DB
        user_correct.refresh_from_db()
        user_wrong.refresh_from_db()

        # Correct predictor should have 50 + 20 = 70 in total_points
        assert user_correct.total_points == 70
        assert user_correct.champion_bonus_points == 20
        # Wrong predictor should still have 60
        assert user_wrong.total_points == 60
        assert user_wrong.champion_bonus_points == 0

        # Get leaderboard - should reflect stored total_points
        leaderboard = RankingService.get_current_leaderboard()
        correct_entry = next(e for e in leaderboard if e["user_id"] == user_correct.pk)
        wrong_entry = next(e for e in leaderboard if e["user_id"] == user_wrong.pk)

        assert correct_entry["total_points"] == 70
        assert wrong_entry["total_points"] == 60
        assert correct_entry["rank"] < wrong_entry["rank"]

    def test_live_bonus_updates_when_champion_changes(self, db):
        """Test live bonus is recalculated when leading team changes."""
        from matches.models import Team
        from scoring.champion_scoring import update_live_champion_bonuses

        # Create teams
        team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)

        # Create live final
        final = make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="live",
            goals_home=2,
            goals_away=1,
        )

        # Create users
        user_home = User.objects.create_user(
            username="home_predictor",
            password="test",
            predicted_champion=team_home,
            total_points=50,
        )
        user_away = User.objects.create_user(
            username="away_predictor",
            password="test",
            predicted_champion=team_away,
            total_points=50,
        )

        # Scenario 1: Home team leading
        update_live_champion_bonuses()
        user_home.refresh_from_db()
        user_away.refresh_from_db()

        assert user_home.total_points == 70  # 50 + 20
        assert user_home.champion_bonus_points == 20
        assert user_away.total_points == 50
        assert user_away.champion_bonus_points == 0

        # Scenario 2: Away team takes the lead
        final.goals_home = 1
        final.goals_away = 3
        final.save()

        update_live_champion_bonuses()
        user_home.refresh_from_db()
        user_away.refresh_from_db()

        assert user_home.total_points == 50  # Bonus removed
        assert user_home.champion_bonus_points == 0
        assert user_away.total_points == 80  # 50 + 30
        assert user_away.champion_bonus_points == 30

    def test_live_bonus_removed_when_final_finished(self, db):
        """Test live bonus is replaced with final bonus when final ends."""
        from matches.models import Team
        from scoring.champion_scoring import update_live_champion_bonuses

        # Create teams
        team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)

        # Create live final
        final = make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="live",
            goals_home=2,
            goals_away=1,
        )

        # Create user
        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=team_home,
            total_points=50,
        )

        # Give user live bonus
        update_live_champion_bonuses()
        user.refresh_from_db()
        assert user.total_points == 70
        assert user.champion_bonus_points == 20

        # Finish the final
        final.status = "finished"
        final.save()

        # Update final champion bonus
        update_live_champion_bonuses()
        user.refresh_from_db()

        # Should still have 70 points, champion_bonus_points unchanged
        assert user.total_points == 70
        assert user.champion_bonus_points == 20

    def test_no_live_bonus_when_final_not_started(self, db):
        """Test no live bonus when final hasn't started."""
        from matches.models import Team
        from scoring.champion_scoring import update_live_champion_bonuses

        # Create teams
        team_home = Team.objects.create(name="Germany", fifa_code="GER", champion_points=20)
        team_away = Team.objects.create(name="Brazil", fifa_code="BRA", champion_points=30)

        # Create scheduled final
        make_match(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="scheduled",
            goals_home=None,
            goals_away=None,
        )

        # Create user
        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=team_home,
            total_points=50,
        )

        # Try to update live bonuses
        count = update_live_champion_bonuses()
        assert count == 0

        user.refresh_from_db()
        assert user.total_points == 50
        assert user.champion_bonus_points == 0


class TestRecalculateUserScore:
    """Test recalculate_user_score preserves champion bonus."""

    def test_recalculate_user_score_preserves_champion_bonus(self, db) -> None:
        """recalculate_user_score() must preserve champion_bonus_points in total_points."""
        from matches.models import Team
        from predictions.models import MatchPrediction

        # Create a finished match
        team_a = Team.objects.create(name="Team A", fifa_code="TEA")
        team_b = Team.objects.create(name="Team B", fifa_code="TEB")
        match = make_match(
            team_home=team_a,
            team_away=team_b,
            round="group",
            kickoff=timezone.now(),
            status="finished",
            goals_home=2,
            goals_away=1,
        )

        # Create user with champion bonus already awarded
        user = User.objects.create_user(username="test", password="test")
        user.champion_bonus_points = 20
        user.total_points = 26  # 6 from match + 20 champion
        user.save()

        # Create a scored prediction worth 6 points
        MatchPrediction.objects.create(
            user=user,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
            points_earned=6,
            is_exact_match=True,
        )

        # Recalculate user score
        RankingService.recalculate_user_score(user)
        user.refresh_from_db()

        # total_points should be 6 (match) + 20 (champion bonus) = 26
        assert user.total_points == 26, "Champion bonus must be preserved in total_points"
        assert user.champion_bonus_points == 20
        assert user.exact_match_count == 1
        assert user.jokers_used == 0


class TestUpdateAllUserRanks:
    """Tests for RankingService.update_all_user_ranks()."""

    def test_update_all_user_ranks_basic(self, db):
        """Ranks assigned correctly for users with different scores."""
        # Create users with different scores
        user1 = User.objects.create_user("alice", password="test")
        user1.total_points = 100
        user1.exact_match_count = 5
        user1.jokers_used = 2
        user1.save()

        user2 = User.objects.create_user("bob", password="test")
        user2.total_points = 80
        user2.exact_match_count = 4
        user2.jokers_used = 3
        user2.save()

        count = RankingService.update_all_user_ranks()

        user1.refresh_from_db()
        user2.refresh_from_db()

        assert count == 2
        assert user1.global_rank == 1
        assert user2.global_rank == 2

    def test_update_all_user_ranks_olympic_ties(self, db):
        """Users with identical tiebreakers share rank, next rank skips."""
        user1 = User.objects.create_user("alice", password="test")
        user1.total_points = 100
        user1.exact_match_count = 5
        user1.jokers_used = 2
        user1.save()

        user2 = User.objects.create_user("bob", password="test")
        user2.total_points = 100  # Same
        user2.exact_match_count = 5  # Same
        user2.jokers_used = 2  # Same
        user2.save()

        user3 = User.objects.create_user("carol", password="test")
        user3.total_points = 80
        user3.exact_match_count = 4
        user3.jokers_used = 3
        user3.save()

        RankingService.update_all_user_ranks()

        user1.refresh_from_db()
        user2.refresh_from_db()
        user3.refresh_from_db()

        assert user1.global_rank == 1
        assert user2.global_rank == 1  # Tied
        assert user3.global_rank == 3  # Skips 2

    def test_update_all_user_ranks_empty_users(self, db):
        """Handles no active users gracefully."""
        count = RankingService.update_all_user_ranks()
        assert count == 0

    def test_update_all_user_ranks_excludes_inactive(self, db):
        """Inactive users are not ranked."""
        active_user = User.objects.create_user("active", password="test")
        active_user.total_points = 100
        active_user.save()

        inactive_user = User.objects.create_user("inactive", password="test")
        inactive_user.total_points = 200
        inactive_user.is_active = False
        inactive_user.save()

        count = RankingService.update_all_user_ranks()

        active_user.refresh_from_db()
        inactive_user.refresh_from_db()

        assert count == 1
        assert active_user.global_rank == 1
        assert inactive_user.global_rank is None


class TestRankUpdateSignal:
    """Tests for rank updates via match result signal."""

    def test_ranks_update_after_match_result(self, db):
        """Global ranks update after match result is entered."""
        from matches.models import Team
        from matches.signals import match_result_entered
        from predictions.models import MatchPrediction

        # Create teams
        team_a = Team.objects.create(name="Team A", fifa_code="TEA")
        team_b = Team.objects.create(name="Team B", fifa_code="TEB")

        # Create match
        match = make_match(
            team_home=team_a,
            team_away=team_b,
            round="group",
            kickoff=timezone.now(),
            status="scheduled",
        )

        # Create users with predictions
        user1 = User.objects.create_user("alice", password="test")
        user2 = User.objects.create_user("bob", password="test")

        MatchPrediction.objects.create(
            user=user1,
            match=match,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        MatchPrediction.objects.create(
            user=user2,
            match=match,
            predicted_goals_home=1,
            predicted_goals_away=2,
        )

        # Verify ranks are None initially
        user1.refresh_from_db()
        user2.refresh_from_db()
        assert user1.global_rank is None
        assert user2.global_rank is None

        # Enter match result (triggers signal)
        match.goals_home = 2
        match.goals_away = 1
        match.status = "finished"
        match.save()

        # Manually trigger signal (to avoid relying on model save)
        match_result_entered.send(sender=match.__class__, match=match)

        # Verify ranks are now set
        user1.refresh_from_db()
        user2.refresh_from_db()
        assert user1.global_rank is not None
        assert user2.global_rank is not None

    def test_ranks_correct_after_multiple_match_results(self, db):
        """Global ranks update correctly after multiple match results."""
        from matches.models import Team
        from matches.signals import match_result_entered
        from predictions.models import MatchPrediction

        # Create teams
        team_a = Team.objects.create(name="Team A", fifa_code="TEA")
        team_b = Team.objects.create(name="Team B", fifa_code="TEB")

        # Create two matches
        match1 = make_match(
            team_home=team_a,
            team_away=team_b,
            round="group",
            kickoff=timezone.now(),
            status="scheduled",
        )
        match2 = make_match(
            team_home=team_b,
            team_away=team_a,
            round="group",
            kickoff=timezone.now(),
            status="scheduled",
        )

        # Create users with predictions
        user1 = User.objects.create_user("alice", password="test")
        user2 = User.objects.create_user("bob", password="test")

        # Alice predicts both matches correctly
        MatchPrediction.objects.create(
            user=user1,
            match=match1,
            predicted_goals_home=2,
            predicted_goals_away=1,
        )
        MatchPrediction.objects.create(
            user=user1,
            match=match2,
            predicted_goals_home=1,
            predicted_goals_away=2,
        )

        # Bob predicts both matches incorrectly
        MatchPrediction.objects.create(
            user=user2,
            match=match1,
            predicted_goals_home=0,
            predicted_goals_away=0,
        )
        MatchPrediction.objects.create(
            user=user2,
            match=match2,
            predicted_goals_home=0,
            predicted_goals_away=0,
        )

        # Enter first match result
        match1.goals_home = 2
        match1.goals_away = 1
        match1.status = "finished"
        match1.save()
        match_result_entered.send(sender=match1.__class__, match=match1)

        # Verify ranks after first match
        user1.refresh_from_db()
        user2.refresh_from_db()
        assert user1.global_rank == 1  # Alice should be first
        assert user2.global_rank == 2  # Bob should be second

        # Enter second match result
        match2.goals_home = 1
        match2.goals_away = 2
        match2.status = "finished"
        match2.save()
        match_result_entered.send(sender=match2.__class__, match=match2)

        # Verify ranks after second match
        user1.refresh_from_db()
        user2.refresh_from_db()
        assert user1.global_rank == 1  # Alice should still be first (more points)
        assert user2.global_rank == 2  # Bob should still be second
