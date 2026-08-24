from datetime import UTC, datetime

import pytest
from django.db import IntegrityError

from matches.models import Match, Team


@pytest.mark.django_db
class TestTeamModel:
    """Tests for Team model."""

    def test_create_team_with_required_fields(self):
        """Test creating a team with all required fields."""
        team = Team.objects.create(
            name="Germany",
            fifa_code="GER"
        )
        assert team.id is not None
        assert team.name == "Germany"
        assert team.fifa_code == "GER"
        assert team.points == 0
        assert team.is_champion is False

    def test_team_str_returns_name(self):
        """Test __str__ returns team name."""
        team = Team.objects.create(
            name="Brazil",
            fifa_code="BRA"
        )
        assert str(team) == "Brazil"

    def test_fifa_code_uniqueness(self):
        """Test fifa_code unique constraint."""
        Team.objects.create(
            name="Germany",
            fifa_code="GER"
        )
        with pytest.raises(IntegrityError):
            Team.objects.create(
                name="Germany Duplicate",
                fifa_code="GER"  # Duplicate
            )

    def test_team_ordering_by_name(self):
        """Test teams are ordered alphabetically by name."""
        Team.objects.create(name="Germany", fifa_code="GER")
        Team.objects.create(name="Argentina", fifa_code="ARG")
        Team.objects.create(name="Brazil", fifa_code="BRA")

        teams = list(Team.objects.all())
        assert teams[0].name == "Argentina"
        assert teams[1].name == "Brazil"
        assert teams[2].name == "Germany"

    def test_team_default_points(self):
        """Test team creation with default points."""
        team = Team.objects.create(name="France", fifa_code="FRA")
        assert team.points == 0

    def test_set_team_points(self):
        """Test setting team points."""
        team = Team.objects.create(name="Spain", fifa_code="ESP")
        team.points = 100
        team.save()
        team.refresh_from_db()
        assert team.points == 100

    def test_negative_points_values(self):
        """Test team can have negative points."""
        team = Team.objects.create(name="Italy", fifa_code="ITA", points=-10)
        assert team.points == -10

    def test_default_is_champion_false(self):
        """Test team creation with default is_champion=False."""
        team = Team.objects.create(name="England", fifa_code="ENG")
        assert team.is_champion is False

    def test_mark_team_as_champion(self):
        """Test marking a team as champion."""
        team = Team.objects.create(name="Portugal", fifa_code="POR")
        team.is_champion = True
        team.save()
        team.refresh_from_db()
        assert team.is_champion is True

    def test_filter_champion_teams(self):
        """Test filtering champion teams."""
        Team.objects.create(name="Netherlands", fifa_code="NED", is_champion=False)
        champion = Team.objects.create(name="Belgium", fifa_code="BEL", is_champion=True)
        Team.objects.create(name="Croatia", fifa_code="CRO", is_champion=False)

        champions = list(Team.objects.filter(is_champion=True))
        assert len(champions) == 1
        assert champions[0] == champion


@pytest.mark.django_db
class TestMatchModel:
    """Tests for Match model."""

    @pytest.fixture
    def team_home(self):
        """Create a home team fixture."""
        return Team.objects.create(
            name="Germany",
            fifa_code="GER"
        )

    @pytest.fixture
    def team_away(self):
        """Create an away team fixture."""
        return Team.objects.create(
            name="Brazil",
            fifa_code="BRA"
        )

    def test_create_match_with_teams_and_metadata(self, team_home, team_away):
        """Test creating a match with required fields."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group"
        )
        assert match.id is not None
        assert match.team_home == team_home
        assert match.team_away == team_away
        assert match.kickoff == kickoff
        assert match.round == "group"
        assert match.status == "scheduled"  # Default

    def test_match_str_representation_scheduled(self, team_home, team_away):
        """Test __str__ for scheduled match."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group"
        )
        assert str(match) == "Germany vs Brazil (Group Stage)"

    def test_match_str_representation_finished(self, team_home, team_away):
        """Test __str__ for finished match with score."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            goals_home=2,
            goals_away=1,
            status="finished"
        )
        assert str(match) == "Germany 2-1 Brazil"

    def test_match_ordering_by_kickoff(self, team_home, team_away):
        """Test matches are ordered by kickoff datetime."""
        match1 = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=datetime(2026, 6, 22, 18, 0, tzinfo=UTC),
            round="group"
        )
        match2 = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=datetime(2026, 6, 20, 18, 0, tzinfo=UTC),
            round="group"
        )
        match3 = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=datetime(2026, 6, 25, 18, 0, tzinfo=UTC),
            round="group"
        )

        matches = list(Match.objects.all())
        assert matches[0] == match2  # Earliest
        assert matches[1] == match1
        assert matches[2] == match3  # Latest

    def test_team_home_matches_relationship(self, team_home, team_away):
        """Test team.home_matches returns correct matches."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group"
        )

        home_matches = team_home.home_matches.all()
        assert match in home_matches
        assert home_matches.count() == 1

    def test_team_away_matches_relationship(self, team_home, team_away):
        """Test team.away_matches returns correct matches."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group"
        )

        away_matches = team_away.away_matches.all()
        assert match in away_matches
        assert away_matches.count() == 1

    def test_match_with_null_goals_scheduled(self, team_home, team_away):
        """Test scheduled match without goals."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group"
        )
        assert match.goals_home is None
        assert match.goals_away is None
        assert match.status == "scheduled"

    def test_match_with_goals_finished(self, team_home, team_away):
        """Test finished match with goals."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="final",
            goals_home=3,
            goals_away=2,
            status="finished"
        )
        assert match.goals_home == 3
        assert match.goals_away == 2
        assert match.status == "finished"

    def test_match_external_id_field_exists(self, team_home, team_away):
        """Test Match model has external_id field with correct definition."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            external_id=12345
        )
        assert match.external_id == 12345

        # Verify field properties
        field = Match._meta.get_field('external_id')
        assert field.unique is True
        assert field.null is True
        assert field.blank is True
        assert field.db_index is True

    def test_match_external_id_unique_constraint(self, team_home, team_away):
        """Test external_id unique constraint is enforced."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            external_id=99999
        )

        # Attempt to create another match with same external_id
        with pytest.raises(IntegrityError):
            Match.objects.create(
                team_home=team_away,
                team_away=team_home,
                kickoff=kickoff,
                round="group",
                external_id=99999  # Duplicate
            )

    def test_match_external_id_nullable(self, team_home, team_away):
        """Test external_id can be null for manual matches."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            external_id=None
        )
        assert match.external_id is None

        # Multiple matches can have null external_id
        match2 = Match.objects.create(
            team_home=team_away,
            team_away=team_home,
            kickoff=kickoff,
            round="group",
            external_id=None
        )
        assert match2.external_id is None

    def test_match_winner_field_nullable(self, team_home, team_away):
        """Test winner field can be null for scheduled matches."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        match = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            winner=None
        )
        assert match.winner is None

    def test_match_winner_choices_valid(self, team_home, team_away):
        """Test all valid winner choice values."""
        kickoff = datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
        
        # Test home
        match_home = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            winner="home",
            goals_home=2,
            goals_away=1,
            status="finished"
        )
        assert match_home.winner == "home"

        # Test away
        match_away = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            winner="away",
            goals_home=0,
            goals_away=1,
            status="finished"
        )
        assert match_away.winner == "away"

        # Test draw
        match_draw = Match.objects.create(
            team_home=team_home,
            team_away=team_away,
            kickoff=kickoff,
            round="group",
            winner="draw",
            goals_home=1,
            goals_away=1,
            status="finished"
        )
        assert match_draw.winner == "draw"
