"""
Data migration to remove existing weekly snapshots.

Weekly snapshots are being deprecated; this migration removes any existing
weekly snapshot records while preserving daily and final snapshots.
"""

from django.db import migrations


def remove_weekly_snapshots(apps, schema_editor) -> None:
    """Remove all leaderboard snapshots with snapshot_type='weekly'."""
    LeaderboardSnapshot = apps.get_model("scoring", "LeaderboardSnapshot")
    count, _ = LeaderboardSnapshot.objects.filter(snapshot_type="weekly").delete()
    if count:
        print(f"  Removed {count} weekly snapshot(s)")


def noop_reverse(apps, schema_editor) -> None:
    """Reverse migration is a no-op (cannot restore deleted data)."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("scoring", "0001_create_leaderboardsnapshot"),
    ]

    operations = [
        migrations.RunPython(remove_weekly_snapshots, noop_reverse),
    ]
