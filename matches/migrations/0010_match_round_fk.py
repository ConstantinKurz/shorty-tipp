"""Add a nullable foreign key from Match to Round alongside the existing round code."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("matches", "0009_seed_wm2026_tournament"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="round_fk",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="matches",
                to="matches.round",
                help_text="Tournament round",
            ),
        ),
    ]
