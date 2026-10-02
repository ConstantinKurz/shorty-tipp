"""
Tests for template tags in the users app.
"""

import pytest

from users.templatetags.user_tags import round_label


@pytest.mark.django_db
class TestRoundLabelFilter:
    """Test round_label template filter."""

    def test_round_label_filter_valid_codes(self):
        """Labels come from the configured rounds of the active tournament."""
        assert round_label("group") == "Gruppenphase"
        assert round_label("r16") == "Achtelfinale"
        assert round_label("qf") == "Viertelfinale"
        assert round_label("sf") == "Halbfinale"
        assert round_label("3rd") == "Spiel um Platz 3"
        assert round_label("final") == "Finale"

    def test_round_label_r32_is_sechzehntelfinale(self):
        """The round of 32 is labelled Sechzehntelfinale, not Achtelfinale."""
        assert round_label("r32") == "Sechzehntelfinale"

    def test_round_label_filter_invalid_code(self):
        """Test round_label filter handles invalid codes."""
        assert round_label("invalid") == "invalid"

    def test_round_label_filter_empty_string(self):
        """Test round_label filter handles empty string."""
        assert round_label("") == ""

    def test_round_label_filter_none(self):
        """Test round_label filter handles None."""
        assert round_label(None) == ""
