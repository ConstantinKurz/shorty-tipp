"""
Template tags for the users app.
"""

from django import template

from users.utils import get_flag_emoji as _get_flag_emoji

register = template.Library()


@register.filter
def flag_emoji(country_code: str | None) -> str:
    """
    Convert a country code to a flag emoji.

    Usage in templates:
        {{ team.fifa_code|flag_emoji }}
        {{ "DE"|flag_emoji }}

    Args:
        country_code: Two-letter ISO country code.

    Returns:
        Flag emoji string or empty string.
    """
    return _get_flag_emoji(country_code)


@register.filter
def round_label(round_code: str | None) -> str:
    """
    Convert a round code to its German label.

    Usage in templates:
        {{ round_code|round_label }}
        {{ "group"|round_label }}  => "Gruppe"

    Args:
        round_code: Tournament round code.

    Returns:
        German label for the round or the code unchanged if invalid/None.
    """
    if not round_code:
        return ""

    labels = {
        "group": "Gruppe",
        "r32": "Achtelfinale",
        "r16": "Achtelfinale",
        "qf": "Viertelfinale",
        "sf": "Halbfinale",
        "3rd": "3. Platz",
        "final": "Finale",
    }

    return labels.get(round_code, round_code)
