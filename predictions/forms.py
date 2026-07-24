"""Prediction forms for the tipapp application."""

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from predictions.models import MatchPrediction


class PredictionForm(forms.ModelForm):
    """
    Form for creating/updating match predictions.

    Includes validation for goal values (0-99 range) and
    Tailwind-styled widgets for inline editing.
    """

    class Meta:
        model = MatchPrediction
        fields = ["predicted_goals_home", "predicted_goals_away"]
        widgets = {
            "predicted_goals_home": forms.NumberInput(
                attrs={
                    "class": (
                        "w-12 h-10 text-center text-lg font-semibold "
                        "bg-zinc-100 dark:bg-zinc-700 "
                        "border border-zinc-300 dark:border-zinc-600 "
                        "rounded-lg focus:ring-2 focus:ring-emerald-500 "
                        "focus:border-emerald-500 "
                        "text-zinc-900 dark:text-white "
                        "disabled:opacity-50 disabled:cursor-not-allowed"
                    ),
                    "min": "0",
                    "max": "99",
                    "placeholder": "-",
                }
            ),
            "predicted_goals_away": forms.NumberInput(
                attrs={
                    "class": (
                        "w-12 h-10 text-center text-lg font-semibold "
                        "bg-zinc-100 dark:bg-zinc-700 "
                        "border border-zinc-300 dark:border-zinc-600 "
                        "rounded-lg focus:ring-2 focus:ring-emerald-500 "
                        "focus:border-emerald-500 "
                        "text-zinc-900 dark:text-white "
                        "disabled:opacity-50 disabled:cursor-not-allowed"
                    ),
                    "min": "0",
                    "max": "99",
                    "placeholder": "-",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with validators for goal range."""
        super().__init__(*args, **kwargs)

        # Add range validators
        goal_validators = [MinValueValidator(0), MaxValueValidator(99)]
        self.fields["predicted_goals_home"].validators.extend(goal_validators)
        self.fields["predicted_goals_away"].validators.extend(goal_validators)

        # Make fields required
        self.fields["predicted_goals_home"].required = True
        self.fields["predicted_goals_away"].required = True
