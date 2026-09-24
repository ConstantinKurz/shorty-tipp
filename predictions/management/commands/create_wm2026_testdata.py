"""
Management command to create Shortytipp test data.

Creates a complete tournament dataset with 48 real teams, 104 matches
based on the actual Shortytipp format (12 groups of 4), test users, and
realistic predictions following all game rules.
"""

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from matches.models import Match, Team
from predictions.models import MatchPrediction
from scoring.match_scoring import ScoringService
from users.models import User

# Real Shortytipp Groups (12 groups × 4 teams)
# Based on the actual draw: https://en.wikipedia.org/wiki/2026_FIFA_World_Cup
WM2026_GROUPS: dict[str, list[tuple[str, str]]] = {
    "A": [
        ("Mexico", "MEX"),
        ("South Africa", "RSA"),
        ("Czech Republic", "CZE"),
        ("New Zealand", "NZL"),
    ],
    "B": [
        ("Canada", "CAN"),
        ("Bosnia and Herzegovina", "BIH"),
        ("Austria", "AUT"),
        ("Jordan", "JOR"),
    ],
    "C": [
        ("Brazil", "BRA"),
        ("Morocco", "MAR"),
        ("Algeria", "ALG"),
        ("Cape Verde", "CPV"),
    ],
    "D": [
        ("United States", "USA"),
        ("Paraguay", "PAR"),
        ("Australia", "AUS"),
        ("Curaçao", "CUW"),
    ],
    "E": [
        ("Germany", "GER"),
        ("Ivory Coast", "CIV"),
        ("Uzbekistan", "UZB"),
        ("Japan", "JPN"),
    ],
    "F": [
        ("Tunisia", "TUN"),
        ("Nigeria", "NGA"),
        ("Poland", "POL"),
        ("Chile", "CHI"),
    ],
    "G": [
        ("Belgium", "BEL"),
        ("Egypt", "EGY"),
        ("Senegal", "SEN"),
        ("Saudi Arabia", "KSA"),
    ],
    "H": [
        ("Uruguay", "URU"),
        ("Colombia", "COL"),
        ("Wales", "WAL"),
        ("Ecuador", "ECU"),
    ],
    "I": [
        ("Argentina", "ARG"),
        ("Iran", "IRN"),
        ("Cameroon", "CMR"),
        ("Peru", "PER"),
    ],
    "J": [
        ("Spain", "ESP"),
        ("Croatia", "CRO"),
        ("Ghana", "GHA"),
        ("South Korea", "KOR"),
    ],
    "K": [
        ("France", "FRA"),
        ("Switzerland", "SUI"),
        ("Denmark", "DEN"),
        ("Qatar", "QAT"),
    ],
    "L": [
        ("England", "ENG"),
        ("Netherlands", "NED"),
        ("Portugal", "POR"),
        ("Serbia", "SRB"),
    ],
}

# Tournament dates (Shortytipp) - using UTC
# Group stage: June 11-27, 2026
# Round of 32: June 28 - July 3
# Round of 16: July 4-7
# Quarter-finals: July 9-11
# Semi-finals: July 14-15
# Third place: July 18
# Final: July 19
GROUP_STAGE_START = datetime(2026, 6, 11, tzinfo=UTC)
R32_START = datetime(2026, 6, 28, tzinfo=UTC)
R16_START = datetime(2026, 7, 4, tzinfo=UTC)
QF_START = datetime(2026, 7, 9, tzinfo=UTC)
SF_START = datetime(2026, 7, 14, tzinfo=UTC)
THIRD_PLACE_DATE = datetime(2026, 7, 18, tzinfo=UTC)
FINAL_DATE = datetime(2026, 7, 19, tzinfo=UTC)

# Kickoff times (hours, UTC) - reflecting North American time zones
KICKOFF_TIMES = [17, 20, 23, 2]  # 1pm, 4pm, 7pm, 10pm ET


class Command(BaseCommand):
    """Create comprehensive Shortytipp test data with real teams and schedule."""

    help = (
        "Create Shortytipp test data: 48 real teams (groups A-L), "
        "104 matches (72 group + 32 knockout), test users, and predictions"
    )

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.teams: list[Team] = []
        self.matches: list[Match] = []
        self.users: list[User] = []
        self.predictions: list[MatchPrediction] = []

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing test data (matches, teams, test users) before creating new data",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=8,
            help="Number of test users (tippers) to create (default: 8)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        clear = options["clear"]
        num_users = options["users"]

        if num_users < 1:
            raise CommandError("--users must be at least 1")
        if num_users > 20:
            raise CommandError("--users must be at most 20")

        self.stdout.write(f"Creating Shortytipp test data with {num_users} users...")

        try:
            with transaction.atomic():
                if clear:
                    self._clear_existing_data()

                self._create_teams()
                self._create_matches()
                self._create_users(num_users)
                self._create_predictions()
                self._calculate_scores()
                self._validate_data()
                self._print_summary()

        except (ValueError, TypeError, KeyError, ValidationError, DatabaseError) as e:
            self.stderr.write(self.style.ERROR(f"Error creating test data: {e}"))
            raise CommandError(str(e)) from e

        self.stdout.write(self.style.SUCCESS("Shortytipp test data created successfully!"))

    def _clear_existing_data(self):
        """Delete existing test data."""
        self.stdout.write("  Clearing existing test data...")
        # Delete predictions first (FK constraint)
        MatchPrediction.objects.all().delete()
        # Delete matches
        Match.objects.all().delete()
        # Delete teams
        Team.objects.all().delete()
        # Delete test users (those starting with "tipper")
        User.objects.filter(username__startswith="tipper").delete()
        self.stdout.write("    Cleared all existing data")

    def _create_teams(self):
        """Create 48 teams from real Shortytipp groups."""
        self.stdout.write("  Creating 48 teams...")
        teams_to_create = []

        for _group_name, team_list in WM2026_GROUPS.items():
            for team_name, fifa_code in team_list:
                teams_to_create.append(
                    Team(
                        name=team_name,
                        fifa_code=fifa_code,
                    )
                )

        self.teams = Team.objects.bulk_create(teams_to_create)
        self.stdout.write(f"    Created {len(self.teams)} teams")

    def _create_matches(self):
        """Create 104 matches (72 group + 32 knockout)."""
        self.stdout.write("  Creating 104 matches...")
        matches_to_create = []

        # Build team lookup by FIFA code
        team_by_code: dict[str, Team] = {t.fifa_code: t for t in self.teams}

        # Group stage: 72 matches (12 groups × 6 matches per group with 4 teams)
        # Each group has round-robin: 1v2, 3v4, 1v3, 4v2, 4v1, 2v3 = 6 matches
        group_matches = self._create_group_stage_matches(team_by_code)
        matches_to_create.extend(group_matches)

        # Knockout rounds:
        # R32: 16 matches (32 teams -> 16)
        # R16: 8 matches (16 -> 8)
        # QF: 4 matches (8 -> 4)
        # SF: 2 matches (4 -> 2)
        # 3rd place: 1 match
        # Final: 1 match
        # Total knockout: 16 + 8 + 4 + 2 + 1 + 1 = 32
        r32_matches = self._create_knockout_matches("r32", 16, R32_START, 6)
        r16_matches = self._create_knockout_matches("r16", 8, R16_START, 4)
        qf_matches = self._create_knockout_matches("qf", 4, QF_START, 3)
        sf_matches = self._create_knockout_matches("sf", 2, SF_START, 2)
        third_matches = self._create_knockout_matches("3rd", 1, THIRD_PLACE_DATE, 1)
        final_matches = self._create_knockout_matches("final", 1, FINAL_DATE, 1)

        matches_to_create.extend(r32_matches)
        matches_to_create.extend(r16_matches)
        matches_to_create.extend(qf_matches)
        matches_to_create.extend(sf_matches)
        matches_to_create.extend(third_matches)
        matches_to_create.extend(final_matches)

        self.matches = Match.objects.bulk_create(matches_to_create)

        # Mark ~24 group stage matches as finished with results (about 1/3 of groups)
        self._set_finished_matches()

        self.stdout.write(f"    Created {len(self.matches)} matches")

    def _create_group_stage_matches(self, team_by_code: dict[str, Team]) -> list[Match]:
        """Create 72 group stage matches with round-robin pattern (4 teams per group)."""
        matches = []
        match_idx = 0

        for _group_name, team_list in WM2026_GROUPS.items():
            teams = [team_by_code[code] for _name, code in team_list]

            # Round-robin for 4 teams: 6 matches
            # Matchday 1: 1v2, 3v4
            # Matchday 2: 1v3, 4v2
            # Matchday 3: 4v1, 2v3
            pairings = [
                (teams[0], teams[1]),  # 1v2
                (teams[2], teams[3]),  # 3v4
                (teams[0], teams[2]),  # 1v3
                (teams[3], teams[1]),  # 4v2
                (teams[3], teams[0]),  # 4v1
                (teams[1], teams[2]),  # 2v3
            ]

            for i, (home, away) in enumerate(pairings):
                # Distribute matches over group stage period
                # Matchday 1: days 0-6, Matchday 2: days 7-12, Matchday 3: days 13-16
                if i < 2:
                    day_offset = match_idx % 7
                elif i < 4:
                    day_offset = 7 + (match_idx % 6)
                else:
                    day_offset = 13 + (match_idx % 4)

                kickoff_idx = match_idx % len(KICKOFF_TIMES)
                kickoff = GROUP_STAGE_START + timedelta(
                    days=day_offset, hours=KICKOFF_TIMES[kickoff_idx]
                )

                matches.append(
                    Match(
                        team_home=home,
                        team_away=away,
                        kickoff=kickoff,
                        round="group",
                        status="scheduled",
                    )
                )
                match_idx += 1

        return matches

    def _create_knockout_matches(
        self, round_code: str, num_matches: int, start_date: datetime, days_span: int
    ) -> list[Match]:
        """Create knockout stage matches with placeholder teams."""
        matches = []
        # Use random teams from our created teams for knockout matches
        available_teams = list(self.teams)

        for i in range(num_matches):
            # Pick two different teams
            home_idx = i * 2 % len(available_teams)
            away_idx = (i * 2 + 1) % len(available_teams)
            home = available_teams[home_idx]
            away = available_teams[away_idx]

            # Distribute over days
            day_offset = i % days_span
            kickoff_idx = i % len(KICKOFF_TIMES)
            kickoff = start_date + timedelta(days=day_offset, hours=KICKOFF_TIMES[kickoff_idx])

            matches.append(
                Match(
                    team_home=home,
                    team_away=away,
                    kickoff=kickoff,
                    round=round_code,
                    status="scheduled",
                )
            )

        return matches

    def _set_finished_matches(self):
        """Mark ~24 group stage matches as finished with random results."""
        group_matches = [m for m in self.matches if m.round == "group"]
        # Sort by kickoff to finish the earliest ones
        group_matches.sort(key=lambda m: m.kickoff)
        finished_count = min(24, len(group_matches))  # About 1/3 of 72 group matches

        for match in group_matches[:finished_count]:
            match.status = "finished"
            match.goals_home = random.randint(0, 5)
            match.goals_away = random.randint(0, 5)
            match.save()

    def _create_users(self, num_users: int):
        """Create test users."""
        self.stdout.write(f"  Creating {num_users} test users...")
        users_to_create = []
        for i in range(1, num_users + 1):
            user = User(
                username=f"tipper{i}",
                email=f"tipper{i}@example.com",
                is_active=True,
                is_staff=False,
            )
            user.set_password("testpass123")
            users_to_create.append(user)

        # Can't use bulk_create for passwords, need to save individually
        for user in users_to_create:
            user.save()
            self.users.append(user)

        self.stdout.write(f"    Created {len(self.users)} users")

    def _create_predictions(self):
        """Create predictions for all users following joker rules."""
        self.stdout.write("  Creating predictions...")

        # Joker limits per round
        joker_limits = {
            "group": 0,
            "r32": 3,
            "r16": 3,
            "qf": 2,
            "sf_combined": 2,  # sf, 3rd, final share pool
        }

        # Get matches by round
        all_matches = list(Match.objects.all().order_by("kickoff"))
        group_matches = [m for m in all_matches if m.round == "group"]
        knockout_matches = [m for m in all_matches if m.round != "group"]
        finished_matches = {m.pk for m in all_matches if m.status == "finished"}

        predictions_to_create = []

        for idx, user in enumerate(self.users):
            user_num = idx + 1
            # Prediction pattern based on user number
            pattern = self._get_prediction_pattern(user_num)

            # Group stage: exactly 36 predictions (random selection)
            selected_group = random.sample(group_matches, min(36, len(group_matches)))

            # Knockout: 80-100% coverage
            knockout_coverage = random.uniform(0.8, 1.0)
            knockout_count = int(len(knockout_matches) * knockout_coverage)
            selected_knockout = random.sample(knockout_matches, knockout_count)

            # Create predictions for group stage
            for match in selected_group:
                pred = self._create_single_prediction(
                    user, match, pattern, match.pk in finished_matches, joker_active=False
                )
                predictions_to_create.append(pred)

            # Create predictions for knockout with joker distribution
            # Organize by round for joker assignment
            knockout_by_round: dict[str, list[Match]] = {}
            for m in selected_knockout:
                round_key = m.round if m.round not in ["sf", "3rd", "final"] else "sf_combined"
                if round_key not in knockout_by_round:
                    knockout_by_round[round_key] = []
                knockout_by_round[round_key].append(m)

            # Assign jokers per round
            joker_assignments: set[int] = set()  # match PKs with jokers
            for round_key, round_matches in knockout_by_round.items():
                limit = joker_limits.get(round_key, 0)
                if limit > 0 and round_matches:
                    joker_count = min(limit, len(round_matches))
                    joker_matches = random.sample(round_matches, joker_count)
                    for m in joker_matches:
                        joker_assignments.add(m.pk)

            # Create knockout predictions
            for match in selected_knockout:
                joker_active = match.pk in joker_assignments
                pred = self._create_single_prediction(
                    user, match, pattern, match.pk in finished_matches, joker_active
                )
                predictions_to_create.append(pred)

        # Bulk create all predictions
        MatchPrediction.objects.bulk_create(predictions_to_create)
        self.predictions = list(MatchPrediction.objects.all())
        self.stdout.write(f"    Created {len(self.predictions)} predictions")

    def _get_prediction_pattern(self, user_num: int) -> str:
        """Get prediction pattern name for a user number."""
        patterns = [
            "optimistic",
            "pessimistic",
            "chaotic",
            "realistic",
            "home_bias",
            "conservative",
        ]
        if user_num <= len(patterns):
            return patterns[user_num - 1]
        return "realistic"  # Default for additional users

    def _create_single_prediction(
        self,
        user: User,
        match: Match,
        pattern: str,
        is_finished: bool,
        joker_active: bool,
    ) -> MatchPrediction:
        """Create a single prediction based on pattern and match status."""
        if is_finished and match.goals_home is not None and match.goals_away is not None:
            # For finished matches, vary accuracy
            home, away = self._generate_prediction_for_finished(
                match.goals_home, match.goals_away, pattern
            )
        else:
            home, away = self._generate_prediction(pattern)

        return MatchPrediction(
            user=user,
            match=match,
            predicted_goals_home=home,
            predicted_goals_away=away,
            joker_active=joker_active,
        )

    def _generate_prediction(self, pattern: str) -> tuple[int, int]:
        """Generate prediction goals based on pattern."""
        if pattern == "optimistic":
            # High scores: 3-5 goals per team
            return random.randint(3, 5), random.randint(3, 5)
        elif pattern == "pessimistic":
            # Low scores: 0-2 goals per team
            return random.randint(0, 2), random.randint(0, 2)
        elif pattern == "chaotic":
            # Random: 0-5 goals
            return random.randint(0, 5), random.randint(0, 5)
        elif pattern == "home_bias":
            # Home team advantage
            home = random.randint(1, 4)
            away = max(0, home - random.randint(0, 2))
            return home, away
        elif pattern == "conservative":
            # Many draws
            if random.random() < 0.4:
                score = random.randint(0, 2)
                return score, score
            return random.randint(0, 2), random.randint(0, 2)
        else:  # realistic
            # Balanced: 0-3 goals
            return random.randint(0, 3), random.randint(0, 3)

    def _generate_prediction_for_finished(
        self, actual_home: int, actual_away: int, pattern: str
    ) -> tuple[int, int]:
        """Generate prediction for finished match with varied accuracy."""
        accuracy = random.random()

        if accuracy < 0.2:
            # ~20% exact match
            return actual_home, actual_away
        elif accuracy < 0.5:
            # ~30% correct tendency (same winner/draw)
            diff = actual_home - actual_away
            if diff > 0:
                # Home win - predict home win with different score
                home = random.randint(1, 4)
                away = max(0, home - random.randint(1, 3))
            elif diff < 0:
                # Away win
                away = random.randint(1, 4)
                home = max(0, away - random.randint(1, 3))
            else:
                # Draw
                score = random.randint(0, 3)
                home, away = score, score
            # Avoid accidentally hitting exact match
            if home == actual_home and away == actual_away:
                home = (home + 1) % 5
            return home, away
        else:
            # ~50% miss - use pattern-based prediction
            return self._generate_prediction(pattern)

    def _calculate_scores(self):
        """Calculate scores for finished matches."""
        self.stdout.write("  Calculating scores...")

        finished_matches = Match.objects.filter(status="finished")
        scored_count = 0

        for match in finished_matches:
            count = ScoringService.score_all_predictions_for_match(match)
            scored_count += count

        self.stdout.write(f"    Scored {scored_count} predictions")

    def _validate_data(self):
        """Validate created data."""
        self.stdout.write("  Validating data...")

        # Match counts
        team_count = Team.objects.count()
        match_count = Match.objects.count()
        group_match_count = Match.objects.filter(round="group").count()
        r32_count = Match.objects.filter(round="r32").count()
        r16_count = Match.objects.filter(round="r16").count()
        qf_count = Match.objects.filter(round="qf").count()
        sf_stage_count = Match.objects.filter(round__in=["sf", "3rd", "final"]).count()

        if team_count != 48:
            raise CommandError(f"Expected 48 teams, got {team_count}")
        # 104 total: 72 group + 16 R32 + 8 R16 + 4 QF + 2 SF + 1 3rd + 1 Final
        if match_count != 104:
            raise CommandError(f"Expected 104 matches, got {match_count}")
        if group_match_count != 72:
            raise CommandError(f"Expected 72 group matches, got {group_match_count}")
        if r32_count != 16:
            raise CommandError(f"Expected 16 R32 matches, got {r32_count}")
        if r16_count != 8:
            raise CommandError(f"Expected 8 R16 matches, got {r16_count}")
        if qf_count != 4:
            raise CommandError(f"Expected 4 QF matches, got {qf_count}")
        if sf_stage_count != 4:
            raise CommandError(f"Expected 4 SF stage matches, got {sf_stage_count}")

        # Validate predictions per user
        for user in self.users:
            gs_preds = MatchPrediction.objects.filter(user=user, match__round="group").count()
            if gs_preds != 36:
                raise CommandError(
                    f"User {user.username} has {gs_preds} group stage predictions, expected 36"
                )

            # Joker counts
            r32_jokers = MatchPrediction.objects.filter(
                user=user, match__round="r32", joker_active=True
            ).count()
            r16_jokers = MatchPrediction.objects.filter(
                user=user, match__round="r16", joker_active=True
            ).count()
            qf_jokers = MatchPrediction.objects.filter(
                user=user, match__round="qf", joker_active=True
            ).count()
            sf_jokers = MatchPrediction.objects.filter(
                user=user, match__round__in=["sf", "3rd", "final"], joker_active=True
            ).count()

            if r32_jokers > 3:
                raise CommandError(f"User {user.username} has {r32_jokers} R32 jokers, max 3")
            if r16_jokers > 3:
                raise CommandError(f"User {user.username} has {r16_jokers} R16 jokers, max 3")
            if qf_jokers > 2:
                raise CommandError(f"User {user.username} has {qf_jokers} QF jokers, max 2")
            if sf_jokers > 2:
                raise CommandError(f"User {user.username} has {sf_jokers} SF stage jokers, max 2")

        self.stdout.write("    Validation passed")

    def _print_summary(self):
        """Print summary of created data."""
        team_count = Team.objects.count()
        match_count = Match.objects.count()
        finished_count = Match.objects.filter(status="finished").count()
        user_count = User.objects.filter(username__startswith="tipper").count()
        prediction_count = MatchPrediction.objects.count()
        scored_count = MatchPrediction.objects.filter(points_earned__isnull=False).count()
        exact_count = MatchPrediction.objects.filter(is_exact_match=True).count()
        joker_count = MatchPrediction.objects.filter(joker_active=True).count()

        self.stdout.write("  Summary:")
        self.stdout.write(f"    - Teams: {team_count}")
        self.stdout.write(f"    - Matches: {match_count} ({finished_count} finished)")
        self.stdout.write(f"    - Users: {user_count}")
        self.stdout.write(f"    - Predictions: {prediction_count}")
        self.stdout.write(f"    - Scored predictions: {scored_count}")
        self.stdout.write(f"    - Exact matches: {exact_count}")
        self.stdout.write(f"    - Active jokers: {joker_count}")
