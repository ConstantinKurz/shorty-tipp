"""
Tests for template tags in the users app.
"""

import pytest

from users.templatetags.user_tags import round_label


class TestRoundLabelFilter:
    """Test round_label template filter."""

    def test_round_label_filter_valid_codes(self):
        """Test round_label filter converts codes to German labels."""
        assert round_label("group") == "Gruppe"
        assert round_label("r32") == "Achtelfinale"
        assert round_label("r16") == "Achtelfinale"
        assert round_label("qf") == "Viertelfinale"
        assert round_label("sf") == "Halbfinale"
        assert round_label("3rd") == "3. Platz"
        assert round_label("final") == "Finale"

    def test_round_label_filter_invalid_code(self):
        """Test round_label filter handles invalid codes."""
        assert round_label("invalid") == "invalid"

    def test_round_label_filter_empty_string(self):
        """Test round_label filter handles empty string."""
        assert round_label("") == ""

    def test_round_label_filter_none(self):
        """Test round_label filter handles None."""
        assert round_label(None) == ""
