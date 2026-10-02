"""Forms for user management."""

from typing import Any

from django import forms
from django.core.validators import MaxLengthValidator

from matches.models import Team

from .models import User


class UserSettingsForm(forms.ModelForm):
    """Form for editing user profile settings."""

    username = forms.CharField(
        max_length=20,
        validators=[MaxLengthValidator(20)],
        help_text="Max. 20 Zeichen",
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-3 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500",
                "maxlength": "20",
            }
        ),
    )

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "w-full px-3 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500",
            }
        )
    )

    predicted_champion = forms.ModelChoiceField(
        queryset=Team.objects.order_by("name"),
        required=False,
        empty_label="-- Team wählen --",
        widget=forms.Select(
            attrs={
                "class": "w-full px-3 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500",
            }
        ),
    )

    theme_preference = forms.ChoiceField(
        choices=[("light", "Hell"), ("dark", "Dunkel"), ("system", "System")],
        widget=forms.RadioSelect(attrs={"class": "form-radio"}),
    )

    class Meta:
        model = User
        fields = ["username", "email", "predicted_champion", "theme_preference"]

    def __init__(self, *args: Any, champion_locked: bool = False, **kwargs: Any) -> None:
        """Initialize the form and drop the champion field when the pick is locked.

        Args:
            champion_locked: True once the first match has kicked off. When True the
                ``predicted_champion`` field is removed, so posted values are ignored and
                the stored pick is never overwritten.
        """
        super().__init__(*args, **kwargs)
        self.champion_locked = champion_locked
        if champion_locked:
            self.fields.pop("predicted_champion", None)

    def clean_username(self) -> str:
        """Validate username: max 20 chars, unique."""
        username: str = self.cleaned_data["username"]
        if len(username) > 20:
            raise forms.ValidationError("Username darf max. 20 Zeichen haben.")

        # Check uniqueness (excluding current user)
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Dieser Username ist bereits vergeben.")

        return username

    def clean_email(self) -> str:
        """Validate email: unique (excluding current user)."""
        email: str = self.cleaned_data["email"]

        # Check uniqueness (excluding current user)
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Diese E-Mail ist bereits vergeben.")

        return email
