"""Round presets for creating a tournament of a known format.

Presets live in code, not in the database, because the database is dropped when the
installation switches to another tournament. A preset only supplies default values: once
a tournament is created, its rounds are ordinary rows with no reference back to the preset.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoundSpec:
    """Default values for one round of a preset."""

    code: str
    label: str
    order: int
    multiplier: int
    joker_count: int
    joker_multiplier: int
    api_stage: str
    joker_pool: str = ""
    prediction_limit: int | None = None
    is_final: bool = False


# 48 teams, 104 matches: group stage, round of 32, round of 16, quarter-finals,
# semi-finals, third-place match, final. This is the 2026 World Cup format.
WM48_ROUNDS: list[RoundSpec] = [
    RoundSpec("group", "Gruppenphase", 1, 1, 0, 2, "GROUP_STAGE", prediction_limit=36),
    RoundSpec("r32", "Sechzehntelfinale", 2, 2, 3, 2, "ROUND_OF_32"),
    RoundSpec("r16", "Achtelfinale", 3, 2, 3, 2, "ROUND_OF_16"),
    RoundSpec("qf", "Viertelfinale", 4, 3, 2, 2, "QUARTER_FINALS"),
    RoundSpec("sf", "Halbfinale", 5, 3, 2, 2, "SEMI_FINALS", joker_pool="ko_final"),
    RoundSpec("3rd", "Spiel um Platz 3", 6, 3, 2, 2, "THIRD_PLACE", joker_pool="ko_final"),
    RoundSpec("final", "Finale", 7, 3, 2, 2, "FINAL", joker_pool="ko_final", is_final=True),
]

# 32 teams: no round of 32. The format used from 1998 to 2022.
WM32_ROUNDS: list[RoundSpec] = [
    RoundSpec("group", "Gruppenphase", 1, 1, 0, 2, "GROUP_STAGE", prediction_limit=48),
    RoundSpec("r16", "Achtelfinale", 2, 2, 3, 2, "ROUND_OF_16"),
    RoundSpec("qf", "Viertelfinale", 3, 3, 2, 2, "QUARTER_FINALS"),
    RoundSpec("sf", "Halbfinale", 4, 3, 2, 2, "SEMI_FINALS", joker_pool="ko_final"),
    RoundSpec("3rd", "Spiel um Platz 3", 5, 3, 2, 2, "THIRD_PLACE", joker_pool="ko_final"),
    RoundSpec("final", "Finale", 6, 3, 2, 2, "FINAL", joker_pool="ko_final", is_final=True),
]

# 24 teams: no round of 32 and no third-place match. The European Championship format.
# The api_stage values are unverified against the live football-data.org EC competition.
EM24_ROUNDS: list[RoundSpec] = [
    RoundSpec("group", "Gruppenphase", 1, 1, 0, 2, "GROUP_STAGE", prediction_limit=36),
    RoundSpec("r16", "Achtelfinale", 2, 2, 3, 2, "LAST_16"),
    RoundSpec("qf", "Viertelfinale", 3, 3, 2, 2, "QUARTER_FINALS"),
    RoundSpec("sf", "Halbfinale", 4, 3, 2, 2, "SEMI_FINALS", joker_pool="ko_final"),
    RoundSpec("final", "Finale", 5, 3, 2, 2, "FINAL", joker_pool="ko_final", is_final=True),
]

TOURNAMENT_PRESETS: dict[str, list[RoundSpec]] = {
    "wm48": WM48_ROUNDS,
    "wm32": WM32_ROUNDS,
    "em24": EM24_ROUNDS,
}
