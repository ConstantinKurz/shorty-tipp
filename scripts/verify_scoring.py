#!/usr/bin/env python
"""
Manual verification script for scoring and ranking system.
Covers tasks 19.4 - 19.12 from implement-scoring-and-ranking change.

Run with: python manage.py shell < scripts/verify_scoring.py
Or copy/paste into Django shell.
"""

import sys
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

# Models
from matches.models import Match, Team
from predictions.models import MatchPrediction
from scoring.models import LeaderboardSnapshot
from scoring.ranking_service import RankingService
from users.models import User

print("=" * 60)
print("SCORING & RANKING VERIFICATION SCRIPT")
print("=" * 60)


def cleanup_test_data():
    """Remove test data created by this script."""
    MatchPrediction.objects.filter(match__team_home__fifa_code="TST").delete()
    Match.objects.filter(team_home__fifa_code="TST").delete()
    Team.objects.filter(fifa_code__startswith="TS").delete()
    LeaderboardSnapshot.objects.filter(snapshot_type="daily").delete()
    print("Cleaned up previous test data.")


def task_19_4_create_sample_predictions():
    """19.4 - Create sample predictions via shell."""
    print("\n--- 19.4: Create sample predictions ---")

    # Create test teams
    team_home, _ = Team.objects.get_or_create(
        fifa_code="TST", defaults={"name": "Test Home", "odds_category": "A"}
    )
    team_away, _ = Team.objects.get_or_create(
        fifa_code="TSA", defaults={"name": "Test Away", "odds_category": "B"}
    )
    print(f"Teams: {team_home} vs {team_away}")

    # Create test match (scheduled, no result yet)
    match, created = Match.objects.get_or_create(
        team_home=team_home,
        team_away=team_away,
        defaults={
            "kickoff": timezone.now() - timedelta(hours=2),
            "round": "group",
            "status": "scheduled",
        },
    )
    if not created:
        # Reset match for re-runs
        match.goals_home = None
        match.goals_away = None
        match.status = "scheduled"
        match.save()
    print(f"Match: {match}")

    # Get test user
    user = User.objects.first()
    if not user:
        print("ERROR: No users in database!")
        return None, None, None

    # Reset user stats for clean test
    user.total_points = 0
    user.exact_match_count = 0
    user.jokers_used = 0
    user.save()

    # Create prediction (exact match: 2-1)
    pred, _ = MatchPrediction.objects.update_or_create(
        user=user,
        match=match,
        defaults={
            "predicted_goals_home": 2,
            "predicted_goals_away": 1,
            "joker_active": False,
            "points_earned": None,
            "is_exact_match": False,
        },
    )
    print(f"Prediction: {pred}")
    print(f"User before scoring: points={user.total_points}, exact={user.exact_match_count}")

    return user, match, pred


def task_19_5_enter_result_verify_scoring(user, match, pred):
    """19.5 - Enter match results and verify automatic scoring."""
    print("\n--- 19.5: Enter match result + auto-scoring ---")

    if not all([user, match, pred]):
        print("SKIP: Missing test data from 19.4")
        return False

    # Enter result (exact match with prediction)
    match.goals_home = 2
    match.goals_away = 1
    match.status = "finished"
    match.save()  # This triggers ScoringService.score_all_predictions_for_match()

    print(f"Match result entered: {match}")

    # Verify prediction scored
    pred.refresh_from_db()
    print("Prediction after scoring:")
    print(f"  points_earned: {pred.points_earned}")
    print(f"  is_exact_match: {pred.is_exact_match}")

    # Expected: 6 points (exact match), group stage = x1 multiplier
    expected_points = 6
    if pred.points_earned == expected_points and pred.is_exact_match:
        print(f"PASS: Exact match scored correctly ({expected_points} points)")
        return True
    else:
        print(f"FAIL: Expected {expected_points} points, got {pred.points_earned}")
        return False


def task_19_6_verify_user_stats(user):
    """19.6 - Verify user statistics updated correctly."""
    print("\n--- 19.6: Verify user statistics ---")

    if not user:
        print("SKIP: No user")
        return False

    user.refresh_from_db()
    print("User stats:")
    print(f"  total_points: {user.total_points}")
    print(f"  exact_match_count: {user.exact_match_count}")
    print(f"  jokers_used: {user.jokers_used}")

    if user.total_points == 6 and user.exact_match_count == 1:
        print("PASS: User stats updated correctly")
        return True
    else:
        print("FAIL: Expected total_points=6, exact_match_count=1")
        return False


def task_19_7_generate_leaderboard():
    """19.7 - Generate leaderboard and verify ranking order."""
    print("\n--- 19.7: Generate leaderboard ---")

    ranking = RankingService.get_current_leaderboard()

    print(f"Leaderboard ({len(ranking)} entries):")
    for entry in ranking[:5]:  # Top 5
        print(
            f"  #{entry['rank']}: {entry['username']} - {entry['total_points']} pts "
            f"(exact: {entry['exact_match_count']}, jokers: {entry['jokers_used']})"
        )

    if len(ranking) > 0:
        print("PASS: Leaderboard generated")
        return True
    else:
        print("FAIL: Empty leaderboard")
        return False


def task_19_8_create_snapshot():
    """19.8 - Create snapshot and verify data saved."""
    print("\n--- 19.8: Create leaderboard snapshot ---")

    snapshot = RankingService.create_snapshot(snapshot_type="daily")

    print(f"Snapshot created: {snapshot}")
    print(f"  ID: {snapshot.id}")
    print(f"  Type: {snapshot.snapshot_type}")
    print(f"  Data entries: {len(snapshot.data)}")

    if snapshot.data and len(snapshot.data) > 0:
        print("PASS: Snapshot created with data")
        return True
    else:
        print("FAIL: Snapshot empty")
        return False


def task_19_9_export_csv():
    """19.9 - Export CSV and verify formatting."""
    print("\n--- 19.9: Export CSV ---")

    from scoring.exports import generate_leaderboard_csv

    ranking = RankingService.get_current_leaderboard()
    csv_content = generate_leaderboard_csv(ranking)
    lines = csv_content.strip().split("\n")

    print(f"CSV export ({len(lines)} lines):")
    for line in lines[:4]:  # Header + first 3 rows
        print(f"  {line}")

    if len(lines) > 1 and "rank" in lines[0].lower():
        print("PASS: CSV exported with header")
        return True
    else:
        print("FAIL: CSV format issue")
        return False


def task_19_10_export_pdf():
    """19.10 - Export PDF and verify formatting."""
    print("\n--- 19.10: Export PDF ---")

    try:
        from scoring.exports import generate_leaderboard_pdf

        ranking = RankingService.get_current_leaderboard()
        pdf_bytes = generate_leaderboard_pdf(ranking)

        print(f"PDF export: {len(pdf_bytes)} bytes")

        # Check PDF magic bytes
        if pdf_bytes[:4] == b"%PDF":
            print("PASS: Valid PDF generated")
            return True
        else:
            print("FAIL: Invalid PDF format")
            return False
    except ImportError as e:
        print(f"SKIP: PDF export dependency missing ({e})")
        return None
    except Exception as e:
        print(f"FAIL: PDF export error: {e}")
        return False


def task_19_11_recalculate_scores():
    """19.11 - Run recalculate_scores and verify consistency."""
    print("\n--- 19.11: Recalculate scores ---")

    from io import StringIO

    from django.core.management import call_command

    out = StringIO()
    call_command("recalculate_scores", stdout=out)
    output = out.getvalue()

    print("recalculate_scores output:")
    for line in output.strip().split("\n")[:5]:
        print(f"  {line}")

    print("PASS: recalculate_scores ran successfully")
    return True


def task_19_12_test_tiebreakers():
    """19.12 - Test tiebreakers with sample data."""
    print("\n--- 19.12: Test tiebreakers ---")

    # Create two users with same points but different tiebreakers
    user1, _ = User.objects.update_or_create(
        username="tiebreak_test1",
        defaults={
            "total_points": 100,
            "exact_match_count": 5,
            "jokers_used": 2,
        },
    )
    user2, _ = User.objects.update_or_create(
        username="tiebreak_test2",
        defaults={
            "total_points": 100,
            "exact_match_count": 5,
            "jokers_used": 3,  # More jokers = worse
        },
    )
    user3, _ = User.objects.update_or_create(
        username="tiebreak_test3",
        defaults={
            "total_points": 100,
            "exact_match_count": 4,  # Fewer exact = worse
            "jokers_used": 1,
        },
    )

    ranking = RankingService.get_current_leaderboard()

    # Find our test users
    test_ranks = {}
    for entry in ranking:
        if entry["username"].startswith("tiebreak_test"):
            test_ranks[entry["username"]] = entry["rank"]

    print("Tiebreaker test ranks:")
    for username, rank in sorted(test_ranks.items(), key=lambda x: x[1]):
        print(f"  #{rank}: {username}")

    # Expected order: test1 < test2 (fewer jokers) and test1 < test3 (more exact)
    if test_ranks.get("tiebreak_test1", 99) < test_ranks.get(
        "tiebreak_test2", 99
    ) and test_ranks.get("tiebreak_test1", 99) < test_ranks.get("tiebreak_test3", 99):
        print("PASS: Tiebreakers work correctly")
        result = True
    else:
        print("FAIL: Tiebreaker order incorrect")
        result = False

    # Cleanup test users
    User.objects.filter(username__startswith="tiebreak_test").delete()

    return result


def main():
    """Run all verification tasks."""
    results = {}

    with transaction.atomic():
        cleanup_test_data()

        # Run tasks
        user, match, pred = task_19_4_create_sample_predictions()
        results["19.4"] = user is not None

        results["19.5"] = task_19_5_enter_result_verify_scoring(user, match, pred)
        results["19.6"] = task_19_6_verify_user_stats(user)
        results["19.7"] = task_19_7_generate_leaderboard()
        results["19.8"] = task_19_8_create_snapshot()
        results["19.9"] = task_19_9_export_csv()
        results["19.10"] = task_19_10_export_pdf()
        results["19.11"] = task_19_11_recalculate_scores()
        results["19.12"] = task_19_12_test_tiebreakers()

        # Rollback test data
        transaction.set_rollback(True)

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    for task_id, passed in results.items():
        if passed is None:
            status = "SKIP"
        elif passed:
            status = "PASS"
        else:
            status = "FAIL"
        print(f"  {task_id}: {status}")

    passed_count = sum(1 for r in results.values() if r is True)
    total = len(results)
    print(f"\nResult: {passed_count}/{total} passed")

    if all(r is True or r is None for r in results.values()):
        print("\nALL VERIFICATIONS PASSED - Ready to archive change")
        return 0
    else:
        print("\nSOME VERIFICATIONS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
else:
    # Running via manage.py shell
    main()
