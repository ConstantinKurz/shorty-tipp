"""Tests for PredictionForm."""

from predictions.forms import PredictionForm


class TestPredictionForm:
    """Tests for the PredictionForm."""

    def test_valid_data_creates_valid_form(self):
        """Form should be valid with proper goal values."""
        form = PredictionForm(
            data={
                "predicted_goals_home": 2,
                "predicted_goals_away": 1,
            }
        )
        assert form.is_valid()

    def test_valid_with_zero_goals(self):
        """Form should accept 0:0 predictions."""
        form = PredictionForm(
            data={
                "predicted_goals_home": 0,
                "predicted_goals_away": 0,
            }
        )
        assert form.is_valid()

    def test_valid_with_max_goals(self):
        """Form should accept 20 as max value."""
        form = PredictionForm(
            data={
                "predicted_goals_home": 20,
                "predicted_goals_away": 20,
            }
        )
        assert form.is_valid()

    def test_negative_home_goals_rejected(self):
        """Form should reject negative home goals."""
        form = PredictionForm(
            data={
                "predicted_goals_home": -1,
                "predicted_goals_away": 1,
            }
        )
        assert not form.is_valid()
        assert "predicted_goals_home" in form.errors

    def test_negative_away_goals_rejected(self):
        """Form should reject negative away goals."""
        form = PredictionForm(
            data={
                "predicted_goals_home": 1,
                "predicted_goals_away": -1,
            }
        )
        assert not form.is_valid()
        assert "predicted_goals_away" in form.errors

    def test_home_goals_over_99_rejected(self):
        """Form should reject home goals over 99."""
        form = PredictionForm(
            data={
                "predicted_goals_home": 100,
                "predicted_goals_away": 1,
            }
        )
        assert not form.is_valid()
        assert "predicted_goals_home" in form.errors

    def test_away_goals_over_99_rejected(self):
        """Form should reject away goals over 99."""
        form = PredictionForm(
            data={
                "predicted_goals_home": 1,
                "predicted_goals_away": 100,
            }
        )
        assert not form.is_valid()
        assert "predicted_goals_away" in form.errors

    def test_missing_home_goals_rejected(self):
        """Form should reject missing home goals."""
        form = PredictionForm(
            data={
                "predicted_goals_away": 1,
            }
        )
        assert not form.is_valid()
        assert "predicted_goals_home" in form.errors

    def test_missing_away_goals_rejected(self):
        """Form should reject missing away goals."""
        form = PredictionForm(
            data={
                "predicted_goals_home": 1,
            }
        )
        assert not form.is_valid()
        assert "predicted_goals_away" in form.errors

    def test_empty_form_invalid(self):
        """Form should be invalid when empty."""
        form = PredictionForm(data={})
        assert not form.is_valid()
        assert "predicted_goals_home" in form.errors
        assert "predicted_goals_away" in form.errors

    def test_widgets_have_tailwind_classes(self):
        """Widgets should have Tailwind CSS classes."""
        form = PredictionForm()
        home_widget = form.fields["predicted_goals_home"].widget
        away_widget = form.fields["predicted_goals_away"].widget

        assert "rounded-lg" in home_widget.attrs.get("class", "")
        assert "rounded-lg" in away_widget.attrs.get("class", "")

    def test_widgets_have_min_max_attributes(self):
        """Widgets should have min/max attributes."""
        form = PredictionForm()
        home_widget = form.fields["predicted_goals_home"].widget
        away_widget = form.fields["predicted_goals_away"].widget

        assert home_widget.attrs.get("min") == "0"
        assert home_widget.attrs.get("max") == "99"
        assert away_widget.attrs.get("min") == "0"
        assert away_widget.attrs.get("max") == "99"
