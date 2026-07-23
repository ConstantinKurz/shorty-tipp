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
