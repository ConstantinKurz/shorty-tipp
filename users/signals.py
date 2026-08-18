"""
Signal handlers for the users app.

Contains signal handlers for user-related events like champion prediction changes.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from users.models import User


@receiver(pre_save, sender=User)
def track_champion_change(sender, instance: User, **kwargs) -> None:
    """
    Track if predicted_champion is about to change.

    Stores the original value before save so post_save can detect changes.
    """
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            instance._original_predicted_champion_id = old_instance.predicted_champion_id
        except User.DoesNotExist:
            instance._original_predicted_champion_id = None
    else:
        instance._original_predicted_champion_id = None


@receiver(post_save, sender=User)
def recalculate_ranking_on_champion_change(
    sender, instance: User, created: bool, **kwargs
) -> None:
    """
    Recalculate rankings when user's predicted champion changes.

    This ensures that changing a champion prediction via admin
    triggers ranking recalculation, updating bonus points.

    Only fires when:
    - User is not newly created (existing user)
    - predicted_champion field actually changed
    """
    if created:
        # New users don't need recalculation
        return

    # Check if predicted_champion changed
    original_champion_id = getattr(instance, "_original_predicted_champion_id", None)
    current_champion_id = instance.predicted_champion_id

    if original_champion_id != current_champion_id:
        # Import here to avoid circular imports
        from scoring.ranking_service import RankingService

        RankingService.recalculate_user_score(instance)
