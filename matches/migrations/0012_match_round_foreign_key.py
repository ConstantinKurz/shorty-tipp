"""Replace the Match.round code column with the foreign key to Round."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("matches", "0011_backfill_match_round_fk"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="match",
            name="round",
        ),
        migrations.RenameField(
            model_name="match",
            old_name="round_fk",
            new_name="round",
        ),
        migrations.AlterField(
            model_name="match",
            name="round",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="matches",
                to="matches.round",
                help_text="Tournament round",
            ),
        ),
    ]
