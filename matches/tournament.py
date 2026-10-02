"""Access helpers and the creation factory for the tournament configuration."""

from __future__ import annotations

from dataclasses import asdict

from django.db import transaction

from matches.models import Round, Tournament
from matches.presets import TOURNAMENT_PRESETS


class NoActiveTournamentError(RuntimeError):
    """Raised when no tournament is marked as active."""


class UnknownPresetError(ValueError):
    """Raised when a preset name is not defined in ``TOURNAMENT_PRESETS``."""


def get_active_tournament() -> Tournament:
    """
    Return the tournament this installation is currently running.

    Returns:
        Tournament: The tournament with ``is_active=True``.

    Raises:
        NoActiveTournamentError: If no tournament is marked as active.
    """
    tournament = Tournament.objects.filter(is_active=True).first()

    if tournament is None:
        raise NoActiveTournamentError(
            "No active tournament is configured. Create a tournament and mark it as active "
            "in the Django admin before using the application."
        )

    return tournament


def create_rounds_from_preset(tournament: Tournament, preset: str) -> list[Round]:
    """
    Create the rounds of a preset for an existing tournament.

    Args:
        tournament: Tournament the rounds belong to.
        preset: Key in ``TOURNAMENT_PRESETS``.

    Returns:
        The created rounds.

    Raises:
        UnknownPresetError: If ``preset`` is not a known preset name.
    """
    if preset not in TOURNAMENT_PRESETS:
        raise UnknownPresetError(
            f"Unknown preset '{preset}'. Available presets: {', '.join(sorted(TOURNAMENT_PRESETS))}"
        )

    return Round.objects.bulk_create(
        Round(tournament=tournament, **asdict(spec)) for spec in TOURNAMENT_PRESETS[preset]
    )


@transaction.atomic
def create_tournament(
    *,
    name: str,
    slug: str,
    api_competition_code: str,
    api_season: int | None = None,
    lock_buffer_minutes: int = 3,
    preset: str | None = None,
    activate: bool = False,
) -> Tournament:
    """
    Create a tournament and, when a preset is given, its rounds.

    The admin, the ``create_tournament`` management command and the test fixtures all go
    through this function, so a configuration created in one place cannot differ from the
    same configuration created in another.

    Args:
        name: Display name of the tournament.
        slug: Unique short identifier.
        api_competition_code: football-data.org competition code.
        api_season: football-data.org season year, if the API requires one.
        lock_buffer_minutes: Minutes before kickoff after which predictions are locked.
        preset: Key in ``TOURNAMENT_PRESETS``; ``None`` creates a tournament with no rounds.
        activate: Deactivate the currently active tournament and activate this one.

    Returns:
        Tournament: The created tournament.

    Raises:
        UnknownPresetError: If ``preset`` is not a known preset name.
    """
    if preset is not None and preset not in TOURNAMENT_PRESETS:
        raise UnknownPresetError(
            f"Unknown preset '{preset}'. Available presets: {', '.join(sorted(TOURNAMENT_PRESETS))}"
        )

    if activate:
        Tournament.objects.filter(is_active=True).update(is_active=False)

    tournament = Tournament.objects.create(
        name=name,
        slug=slug,
        api_competition_code=api_competition_code,
        api_season=api_season,
        lock_buffer_minutes=lock_buffer_minutes,
        is_active=activate,
    )

    if preset is not None:
        create_rounds_from_preset(tournament, preset)

    return tournament
