"""Replace the A/B odds categories with a per-team champion bonus.

``Team.points`` was declared but never read; it is renamed to ``champion_points`` and
filled from ``odds_category`` (A = 20, B = 30, blank = 0) before that column is dropped.
"""

from django.db import migrations, models

CATEGORY_POINTS = {"A": 20, "B": 30}


def derive_champion_points(apps, schema_editor):
    """Fill champion_points from the odds category of every team."""
    Team = apps.get_model("matches", "Team")

    for category, points in CATEGORY_POINTS.items():
        Team.objects.filter(odds_category=category).update(champion_points=points)

    Team.objects.exclude(odds_category__in=CATEGORY_POINTS).update(champion_points=0)


def reset_champion_points(apps, schema_editor):
    """Reverse step: champion points carry no information once the category is back."""
    Team = apps.get_model("matches", "Team")
    Team.objects.update(champion_points=0)


class Migration(migrations.Migration):
    dependencies = [
        ("matches", "0012_match_round_foreign_key"),
    ]

    operations = [
        migrations.RenameField(
            model_name="team",
            old_name="points",
            new_name="champion_points",
        ),
        migrations.AlterField(
            model_name="team",
            name="champion_points",
            field=models.IntegerField(
                default=0,
                help_text="Bonus points awarded to users who picked this team as champion",
            ),
        ),
        migrations.RunPython(derive_champion_points, reset_champion_points),
        migrations.RemoveField(
            model_name="team",
            name="odds_category",
        ),
    ]
