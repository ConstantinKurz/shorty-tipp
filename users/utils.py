"""
Utility functions for the users app.
"""

# FIFA code to ISO 3166-1 alpha-2 mapping
FIFA_TO_ISO = {
    "ARG": "AR",
    "BRA": "BR",
    "FRA": "FR",
    "GER": "DE",
    "ESP": "ES",
    "ENG": "GB",
    "ITA": "IT",
    "MEX": "MX",
    "USA": "US",
    "CAN": "CA",
    "NED": "NL",
    "POR": "PT",
    "BEL": "BE",
    "URU": "UY",
    "COL": "CO",
    "CHI": "CL",
    "SUI": "CH",
}


def get_flag_emoji(country_code: str | None) -> str:
    """
    Convert an ISO 3166-1 alpha-2 or FIFA country code to a Unicode flag emoji.

    Accepts both 2-letter ISO codes (e.g., "DE", "BR") and 3-letter FIFA codes
    (e.g., "GER", "BRA"). FIFA codes are automatically converted to ISO.

    Uses regional indicator symbols: each letter A-Z maps to a Unicode
    codepoint in the range U+1F1E6 (🇦) to U+1F1FF (🇿).
    Two such symbols together form a flag emoji.

    Args:
        country_code: Two-letter ISO code or three-letter FIFA code.
                      Can be None or empty.

    Returns:
        Flag emoji string (e.g., "🇩🇪" for "DE" or "GER"), or empty string if
        country_code is None, empty, or invalid.

    Examples:
        >>> get_flag_emoji("DE")
        '🇩🇪'
        >>> get_flag_emoji("GER")
        '🇩🇪'
        >>> get_flag_emoji("BRA")
        '🇧🇷'
        >>> get_flag_emoji(None)
        ''
    """
    if not country_code:
        return ""

    code = country_code.strip().upper()

    # Convert FIFA code to ISO if 3 letters
    if len(code) == 3:
        code = FIFA_TO_ISO.get(code, "")
        if not code:
            return ""

    # Now must be 2-letter ISO code
    if len(code) != 2:
        return ""

    try:
        # Regional indicator base: 🇦 (U+1F1E6) corresponds to 'A' (ASCII 65)
        # Formula: codepoint = 0x1F1E6 + (ord(char) - ord('A'))
        return "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in code)
    except (TypeError, ValueError):
        return ""
