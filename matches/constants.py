"""
Central constants for tournament rounds and phases.

Single source of truth for round codes, ordering, and labels.
"""

# Round codes in tournament order
ROUND_ORDER = ["group", "r32", "r16", "qf", "sf", "3rd", "final"]

# Round labels (German)
ROUND_LABELS = {
    "group": "Gruppe",
    "r32": "Achtelfinale",
    "r16": "Achtelfinale",
    "qf": "Viertelfinale",
    "sf": "Halbfinale",
    "3rd": "3. Platz",
    "final": "Finale",
}


def get_available_rounds() -> list[dict[str, str]]:
    """
    Get list of rounds with code and label for UI dropdowns.

    Returns:
        List of dicts: [{"code": "group", "label": "Gruppe"}, ...]
    """
    return [{"code": code, "label": ROUND_LABELS[code]} for code in ROUND_ORDER]
