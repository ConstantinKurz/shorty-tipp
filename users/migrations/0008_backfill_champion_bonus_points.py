# Generated data migration to backfill champion_bonus_points

from django.db import migrations


def backfill_champion_bonus_points(apps, schema_editor):
    """
    Backfill champion_bonus_points for users who already received the bonus.
    
    Logic:
    - Find users who predicted the champion team (is_champion=True)
    - Calculate what their bonus should be based on team's odds_category
    - Set champion_bonus_points to that value
    - Safe to run multiple times (only updates users with champion_bonus_points=0)
    """
    User = apps.get_model("users", "User")
    Team = apps.get_model("matches", "Team")
    Match = apps.get_model("matches", "Match")
    
    # Find the champion team
    try:
        champion = Team.objects.get(is_champion=True)
    except (Team.DoesNotExist, Team.MultipleObjectsReturned):
        # No champion set yet, or data integrity issue - skip backfill
        return
    
    # Check if final is finished
    final_match = Match.objects.filter(round="final", status="finished").first()
    if not final_match:
        # Final not finished yet - skip backfill
        return
    
    # Calculate champion points based on odds category
    if champion.odds_category == "A":
        champion_points = 20
    elif champion.odds_category == "B":
        champion_points = 30
    else:
        champion_points = 0
    
    if champion_points == 0:
        return
    
    # Update users who predicted correctly and haven't been backfilled yet
    users_to_backfill = User.objects.filter(
        predicted_champion=champion,
        champion_bonus_points=0,  # Only backfill users who haven't been updated yet
    )
    
    users_to_backfill.update(champion_bonus_points=champion_points)


def reverse_backfill(apps, schema_editor):
    """
    Reverse the backfill by setting champion_bonus_points back to 0.
    
    Note: This does NOT reverse the points added to total_points.
    This is just for tracking purposes.
    """
    User = apps.get_model("users", "User")
    User.objects.all().update(champion_bonus_points=0)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_user_champion_bonus_points"),
        ("matches", "0004_match_external_id"),  # Ensure Team model is available
    ]

    operations = [
        migrations.RunPython(
            backfill_champion_bonus_points,
            reverse_backfill,
        ),
    ]
