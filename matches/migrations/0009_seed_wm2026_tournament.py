"""Seed the 2026 World Cup tournament with the values previously hardcoded in Python.

The ``r32`` round is deliberately seeded as "Sechzehntelfinale". ``matches/constants.py``
labels it "Achtelfinale", which is the label of ``r16`` and was a defect.
"""

from django.db import migrations

TOURNAMENT = {
    "name": "WM 2026",
    "slug": "wm-2026",
    "api_competition_code": "WC",
    "api_season": 2026,
    "lock_buffer_minutes": 3,
    "is_active": True,
}

ROUNDS = [
    {
        "code": "group",
        "label": "Gruppenphase",
        "order": 1,
        "multiplier": 1,
        "joker_count": 0,
        "joker_multiplier": 2,
        "joker_pool": "",
        "prediction_limit": 36,
        "is_final": False,
        "api_stage": "GROUP_STAGE",
    },
    {
        "code": "r32",
        "label": "Sechzehntelfinale",
        "order": 2,
        "multiplier": 2,
        "joker_count": 3,
        "joker_multiplier": 2,
        "joker_pool": "",
        "prediction_limit": None,
        "is_final": False,
        "api_stage": "ROUND_OF_32",
    },
    {
        "code": "r16",
        "label": "Achtelfinale",
        "order": 3,
        "multiplier": 2,
        "joker_count": 3,
        "joker_multiplier": 2,
        "joker_pool": "",
        "prediction_limit": None,
        "is_final": False,
        "api_stage": "ROUND_OF_16",
    },
    {
        "code": "qf",
        "label": "Viertelfinale",
        "order": 4,
        "multiplier": 3,
        "joker_count": 2,
        "joker_multiplier": 2,
        "joker_pool": "",
        "prediction_limit": None,
        "is_final": False,
        "api_stage": "QUARTER_FINALS",
    },
    {
        "code": "sf",
        "label": "Halbfinale",
        "order": 5,
        "multiplier": 3,
        "joker_count": 2,
        "joker_multiplier": 2,
        "joker_pool": "ko_final",
        "prediction_limit": None,
        "is_final": False,
        "api_stage": "SEMI_FINALS",
    },
    {
        "code": "3rd",
        "label": "Spiel um Platz 3",
        "order": 6,
        "multiplier": 3,
        "joker_count": 2,
        "joker_multiplier": 2,
        "joker_pool": "ko_final",
        "prediction_limit": None,
        "is_final": False,
        "api_stage": "THIRD_PLACE",
    },
    {
        "code": "final",
        "label": "Finale",
        "order": 7,
        "multiplier": 3,
        "joker_count": 2,
        "joker_multiplier": 2,
        "joker_pool": "ko_final",
        "prediction_limit": None,
        "is_final": True,
        "api_stage": "FINAL",
    },
]


def seed_wm2026(apps, schema_editor):
    """Create the WM 2026 tournament and its seven rounds."""
    Tournament = apps.get_model("matches", "Tournament")
    Round = apps.get_model("matches", "Round")

    if Tournament.objects.filter(slug=TOURNAMENT["slug"]).exists():
        return

    tournament = Tournament.objects.create(**TOURNAMENT)

    for round_values in ROUNDS:
        Round.objects.create(tournament=tournament, **round_values)


def remove_wm2026(apps, schema_editor):
    """Delete the seeded tournament and, by cascade, its rounds."""
    Tournament = apps.get_model("matches", "Tournament")

    Tournament.objects.filter(slug=TOURNAMENT["slug"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("matches", "0008_tournament_round"),
    ]

    operations = [
        migrations.RunPython(seed_wm2026, remove_wm2026),
    ]
