"""Point every match at the Round row matching its round code.

Fails loudly rather than guessing: a match whose code has no configured round
would otherwise silently lose its round.
"""

from django.db import migrations


def backfill_round_fk(apps, schema_editor):
    """Resolve each match's round code against the active tournament's rounds."""
    Match = apps.get_model("matches", "Match")
    Round = apps.get_model("matches", "Round")

    if not Match.objects.exists():
        return

    rounds_by_code = {
        round.code: round for round in Round.objects.filter(tournament__is_active=True)
    }

    used_codes = set(Match.objects.values_list("round", flat=True))
    missing = sorted(code for code in used_codes if code not in rounds_by_code)

    if missing:
        raise RuntimeError(
            "Cannot migrate Match.round: the active tournament has no round for "
            f"{missing}. Configured codes: {sorted(rounds_by_code)}."
        )

    for code, round in rounds_by_code.items():
        Match.objects.filter(round=code).update(round_fk=round)


def restore_round_codes(apps, schema_editor):
    """Write the round code back from the foreign key."""
    Match = apps.get_model("matches", "Match")
    Round = apps.get_model("matches", "Round")

    for round in Round.objects.all():
        Match.objects.filter(round_fk=round).update(round=round.code)


class Migration(migrations.Migration):
    dependencies = [
        ("matches", "0010_match_round_fk"),
    ]

    operations = [
        migrations.RunPython(backfill_round_fk, restore_round_codes),
    ]
