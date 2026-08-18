from django.apps import AppConfig


class ScoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "scoring"

    def ready(self) -> None:
        """Import signal handlers when the app is ready."""
        import scoring.signals  # noqa: F401
