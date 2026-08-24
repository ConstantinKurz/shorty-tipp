"""Tests for champion prediction scoring."""

import pytest
from django.utils import timezone

from matches.models import Match, Team
from scoring.champion_scoring import (
    calculate_champion_points,
    get_current_champion_team,
    update_live_champion_bonuses,
)
from scoring.match_scoring import ScoringService
from users.models import User


@pytest.fixture
def champion_team(db) -> Team:
    """Create champion team (category A)."""
    return Team.objects.create(
        name="Germany",
        fifa_code="GER",
        odds_category="A",
    )


@pytest.fixture
def runner_up_team(db) -> Team:
    """Create runner-up team."""
    return Team.objects.create(
        name="Brazil",
        fifa_code="BRA",
        odds_category="B",
    )


@pytest.fixture
def finished_final(db, champion_team: Team, runner_up_team: Team) -> Match:
    """Create finished final match."""
    return Match.objects.create(
        team_home=champion_team,
        team_away=runner_up_team,
        kickoff=timezone.now(),
        round="final",
        status="finished",
        goals_home=1,
        goals_away=0,
    )


class TestChampionPointsAwarded:
    """Test champion points are awarded correctly."""

    def test_points_awarded_when_prediction_matches_champion(
        self, db, champion_team: Team, finished_final: Match
    ) -> None:
        """Test user receives points when their prediction matches champion."""
        user = User.objects.create_user(
            username="winner",
            password="test",
            predicted_champion=champion_team,
        )

        count = update_live_champion_bonuses()

        user.refresh_from_db()
        assert count == 1
        assert user.total_points == 20  # Category A

    def test_no_points_when_prediction_wrong(
        self, db, champion_team: Team, runner_up_team: Team, finished_final: Match
    ) -> None:
        """Test user receives no points when prediction doesn't match."""
        user = User.objects.create_user(
            username="loser",
            password="test",
            predicted_champion=runner_up_team,
        )

        count = update_live_champion_bonuses()

        user.refresh_from_db()
        assert count == 0  # No users awarded
        assert user.total_points == 0


class TestChampionCategories:
    """Test champion scoring by odds category."""

    def test_category_a_champion_20_points(
        self, db, champion_team: Team, runner_up_team: Team, finished_final: Match
    ) -> None:
        """Test category A champion awards 20 points."""
        champion_team.odds_category = "A"
        champion_team.save()

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=champion_team,
        )

        update_live_champion_bonuses()

        user.refresh_from_db()
        assert user.total_points == 20

    def test_category_b_champion_30_points(
        self, db, runner_up_team: Team
    ) -> None:
        """Test category B champion awards 30 points."""
        # Set odds category for champion
        runner_up_team.odds_category = "B"
        runner_up_team.save()

        # Create a team for home (doesn't matter who)
        home_team = Team.objects.create(name="France", fifa_code="FRA")

        # Create final match with runner_up winning
        Match.objects.create(
            team_home=home_team,
            team_away=runner_up_team,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=0,
            goals_away=1,
        )

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=runner_up_team,
        )

        update_live_champion_bonuses()

        user.refresh_from_db()
        assert user.total_points == 30


class TestChampionScoringTriggers:
    """Test when champion scoring triggers."""

    def test_no_scoring_without_champion_set(self, db) -> None:
        """Test no scoring when no final match exists."""
        team = Team.objects.create(
            name="Germany",
            fifa_code="GER",
        )

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=team,
        )

        count = update_live_champion_bonuses()

        assert count == 0
        user.refresh_from_db()
        assert user.total_points == 0

    def test_no_scoring_without_finished_final(
        self, db, champion_team: Team, runner_up_team: Team
    ) -> None:
        """Test no scoring when final match not finished."""
        # Create unfinished final
        Match.objects.create(
            team_home=champion_team,
            team_away=runner_up_team,
            kickoff=timezone.now(),
            round="final",
            status="scheduled",  # Not finished
        )

        User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=champion_team,
        )

        count = update_live_champion_bonuses()

        assert count == 0


class TestMultipleUsers:
    """Test champion scoring with multiple users."""

    def test_multiple_users_predicting_champion_all_receive_points(
        self, db, champion_team: Team, finished_final: Match
    ) -> None:
        """Test all users who predicted champion receive points."""
        users = [
            User.objects.create_user(
                username=f"user{i}",
                password="test",
                predicted_champion=champion_team,
            )
            for i in range(3)
        ]

        count = update_live_champion_bonuses()

        assert count == 3
        for user in users:
            user.refresh_from_db()
            assert user.total_points == 20


class TestChampionMatchPredictionSeparation:
    """Test champion scoring is separate from match prediction scoring."""

    def test_champion_scoring_separate_from_match_prediction(
        self, db, champion_team: Team, runner_up_team: Team, finished_final: Match
    ) -> None:
        """Test champion points don't affect match prediction points."""
        from predictions.models import MatchPrediction

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=champion_team,
            total_points=50,  # Existing points from match predictions
        )

        # Create a match prediction for the final
        MatchPrediction.objects.create(
            user=user,
            match=finished_final,
            predicted_goals_home=1,
            predicted_goals_away=0,
            points_earned=18,  # Already scored
        )

        # Update champion bonuses
        update_live_champion_bonuses()

        user.refresh_from_db()
        # Should add champion points (20) to existing points (50)
        assert user.total_points == 70


class TestDynamicChampionDetection:
    """Test live champion detection during final."""

    def test_returns_none_for_scheduled_final(self, db) -> None:
        """Test returns None when final hasn't started."""
        team_home = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        team_away = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="scheduled",
            goals_home=None,
            goals_away=None,
        )

        champion = get_current_champion_team()
        assert champion is None

    def test_returns_home_team_when_home_leads_live(self, db) -> None:
        """Test returns home team when they're leading during live final."""
        team_home = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        team_away = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="live",
            goals_home=2,
            goals_away=1,
        )

        champion = get_current_champion_team()
        assert champion == team_home

    def test_returns_away_team_when_away_leads_live(self, db) -> None:
        """Test returns away team when they're leading during live final."""
        team_home = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        team_away = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="live",
            goals_home=1,
            goals_away=3,
        )

        champion = get_current_champion_team()
        assert champion == team_away

    def test_returns_is_champion_team_on_draw_live(self, db) -> None:
        """Test returns winner team on draw during live final (penalty shootout)."""
        team_home = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        team_away = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="live",
            goals_home=2,
            goals_away=2,
            winner="away",  # Brazil wins on penalties
        )

        champion = get_current_champion_team()
        assert champion == team_away

    def test_returns_winning_team_after_finished_final(self, db) -> None:
        """Test returns winning team when final is finished."""
        team_home = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        team_away = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=1,
            goals_away=0,
        )

        champion = get_current_champion_team()
        assert champion == team_home

    def test_champion_from_winner_home(self, db) -> None:
        """Test returns home team when winner='home' (penalty shootout)."""
        team_home = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        team_away = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=1,
            goals_away=1,
            winner="home",
        )

        champion = get_current_champion_team()
        assert champion == team_home

    def test_champion_from_winner_away(self, db) -> None:
        """Test returns away team when winner='away' (penalty shootout)."""
        team_home = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        team_away = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=1,
            goals_away=1,
            winner="away",
        )

        champion = get_current_champion_team()
        assert champion == team_away

    def test_champion_penalty_shootout_winner_correct(self, db) -> None:
        """Test penalty shootout winner takes precedence over goals for draw."""
        team_home = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        team_away = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        # Simulates final: 1-1 after extra time, Brazil wins on penalties
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=1,
            goals_away=1,
            winner="away",  # Brazil won on penalties
        )

        champion = get_current_champion_team()
        assert champion == team_away

    def test_no_champion_if_final_not_finished(self, db) -> None:
        """Test returns None if final is still scheduled with no winner."""
        team_home = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        team_away = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="scheduled",
            goals_home=None,
            goals_away=None,
            winner=None,
        )

        champion = get_current_champion_team()
        assert champion is None


class TestChampionScoringIdempotency:
    """Test champion scoring is idempotent (can be called multiple times safely)."""

    def test_scoring_twice_same_as_scoring_once(self, db) -> None:
        """Test calling update_live_champion_bonuses() twice doesn't double-award points."""
        team_home = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        team_away = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=1,
            goals_away=0,
        )

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=team_home,
        )

        # First call - should award points
        count1 = update_live_champion_bonuses()
        assert count1 == 1

        user.refresh_from_db()
        assert user.total_points == 20
        assert user.champion_bonus_points == 20

        # Second call - should recalculate and award same bonus
        count2 = update_live_champion_bonuses()
        assert count2 == 1  # User still awarded (bonuses are recalculated)

        user.refresh_from_db()
        assert user.total_points == 20  # Still 20, not 40 (reset then re-awarded)
        assert user.champion_bonus_points == 20  # Still 20, not 40

    def test_category_a_gets_20_points_tracked(self, db) -> None:
        """Test category A champion awards 20 points and tracks it."""
        team = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        other_team = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=team,
            team_away=other_team,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=1,
            goals_away=0,
        )

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=team,
        )

        update_live_champion_bonuses()

        user.refresh_from_db()
        assert user.champion_bonus_points == 20

    def test_category_b_gets_30_points_tracked(self, db) -> None:
        """Test category B champion awards 30 points and tracks it."""
        team = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        other_team = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        Match.objects.create(
            team_home=team,
            team_away=other_team,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=2,
            goals_away=1,
        )

        user = User.objects.create_user(
            username="predictor",
            password="test",
            predicted_champion=team,
        )

        update_live_champion_bonuses()

        user.refresh_from_db()
        assert user.champion_bonus_points == 30

    def test_wrong_prediction_gets_zero_bonus(self, db) -> None:
        """Test users with wrong prediction don't get champion bonus."""
        champion = Team.objects.create(
            name="Germany", fifa_code="GER", odds_category="A"
        )
        runner_up = Team.objects.create(
            name="Brazil", fifa_code="BRA", odds_category="B"
        )
        Match.objects.create(
            team_home=champion,
            team_away=runner_up,
            kickoff=timezone.now(),
            round="final",
            status="finished",
            goals_home=1,
            goals_away=0,
        )

        user = User.objects.create_user(
            username="wrong_predictor",
            password="test",
            predicted_champion=runner_up,
        )

        update_live_champion_bonuses()

        user.refresh_from_db()
        assert user.total_points == 0
        assert user.champion_bonus_points == 0


