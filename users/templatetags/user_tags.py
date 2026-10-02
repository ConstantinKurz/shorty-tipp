"""
Template tags for the users app.
"""

from django import template

from matches.models import Round
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
    Convert a round code to the label configured for the active tournament.

    Usage in templates:
        {{ round_code|round_label }}
        {{ "group"|round_label }}  => "Gruppenphase"

    Args:
        round_code: Tournament round code.

    Returns:
        Configured label for the round, or the code unchanged if unknown/None.
    """
    if not round_code:
        return ""

    label = (
        Round.objects.filter(tournament__is_active=True, code=round_code)
        .values_list("label", flat=True)
        .first()
    )

    return label or round_code
