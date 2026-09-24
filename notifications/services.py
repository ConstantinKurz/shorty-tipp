"""Email notification services for the tipapp application."""

from __future__ import annotations

import logging
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone

from matches.models import Match
from predictions.models import MatchPrediction
from scoring.models import LeaderboardSnapshot
from users.models import User

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending notification emails."""

    @staticmethod
    def send_leaderboard_to_admin() -> tuple[bool, str]:
        """
        Send latest leaderboard snapshot to configured admin email.

        Retrieves the most recent LeaderboardSnapshot and sends its
        contents formatted as an email to the configured admin address.
        Includes all predictions for each user with joker status, timestamp, and
        points.

        Returns:
            Tuple of (success: bool, message: str)
        """
        admin_email = getattr(settings, "LEADERBOARD_ADMIN_EMAIL", "")
        if not admin_email:
            logger.warning("LEADERBOARD_ADMIN_EMAIL not configured")
            return False, "LEADERBOARD_ADMIN_EMAIL not configured"

        snapshot = LeaderboardSnapshot.objects.order_by("-created_at").first()
        if not snapshot:
            logger.warning("No leaderboard snapshot found")
            return False, "No leaderboard snapshot found"

        try:
            # Fetch all predictions for users in the leaderboard
            user_ids = [entry["user_id"] for entry in snapshot.data]
            users = {
                u.id: u
                for u in User.objects.filter(id__in=user_ids).select_related("predicted_champion")
            }

            # Build predictions map: {user_id: [predictions]}
            predictions_map: dict[int, list[MatchPrediction]] = {}
            all_predictions = (
                MatchPrediction.objects.filter(user_id__in=user_ids)
                .select_related("match", "match__team_home", "match__team_away")
                .order_by("match__kickoff", "created_at")
            )

            for pred in all_predictions:
                if pred.user_id not in predictions_map:
                    predictions_map[pred.user_id] = []
                predictions_map[pred.user_id].append(pred)

            # Enrich rankings with predictions
            rankings_with_predictions = []
            for entry in snapshot.data:
                user_id = entry["user_id"]
                rankings_with_predictions.append(
                    {
                        **entry,
                        "predictions": predictions_map.get(user_id, []),
                        "user": users.get(user_id),
                    }
                )

            context = {
                "snapshot": snapshot,
                "snapshot_date": snapshot.created_at.strftime("%d.%m.%Y %H:%M"),
                "rankings": rankings_with_predictions,
            }

            html_content = render_to_string("notifications/emails/leaderboard_report.html", context)
            text_content = render_to_string("notifications/emails/leaderboard_report.txt", context)

            send_mail(
                subject=f"Leaderboard Report - {snapshot.created_at.strftime('%d.%m.%Y')}",
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                html_message=html_content,
                fail_silently=False,
            )

            logger.info("Leaderboard email sent to %s", admin_email)
            return True, f"Leaderboard email sent to {admin_email}"

        except (SMTPException, OSError, TemplateDoesNotExist) as exc:
            logger.exception("Failed to send leaderboard email: %s", exc)
            return False, f"Failed to send email: {exc}"

    @staticmethod
    def get_users_with_missing_predictions() -> dict[User, list[Match]]:
        """
        Find users who have missing predictions for matches starting within 24 hours.

        Returns:
            Dictionary mapping User objects to lists of Match objects
            for which they don't have predictions.
        """
        now = timezone.now()
        in_24_hours = now + timedelta(hours=24)

        # Find matches starting within the next 24 hours
        upcoming_matches = Match.objects.filter(
            kickoff__gt=now,
            kickoff__lte=in_24_hours,
            status="scheduled",
        ).select_related("team_home", "team_away")

        if not upcoming_matches.exists():
            logger.debug("No upcoming matches in next 24 hours")
            return {}

        # Find active users (exclude staff, superusers, inactive)
        active_users = User.objects.filter(is_active=True, is_staff=False)

        result: dict[User, list[Match]] = {}

        for user in active_users:
            # Get matches this user hasn't predicted
            user_predictions = MatchPrediction.objects.filter(
                user=user, match__in=upcoming_matches
            ).values_list("match_id", flat=True)

            missing_matches = [
                match for match in upcoming_matches if match.pk not in user_predictions
            ]

            if missing_matches:
                result[user] = missing_matches

        return result

    @staticmethod
    def send_prediction_reminder(user: User, matches: list[Match]) -> tuple[bool, str]:
        """
        Send reminder to user about missing predictions.

        Args:
            user: User to notify
            matches: List of matches without predictions

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not user.email:
            logger.warning("User %s has no email address", user.username)
            return False, f"User {user.username} has no email address"

        if not matches:
            return False, "No matches to remind about"

        try:
            context = {
                "user": user,
                "matches": matches,
                "match_count": len(matches),
            }

            html_content = render_to_string(
                "notifications/emails/prediction_reminder.html", context
            )
            text_content = render_to_string("notifications/emails/prediction_reminder.txt", context)

            send_mail(
                subject=f"Erinnerung: {len(matches)} Tipp{'s' if len(matches) > 1 else ''} fehl{'en' if len(matches) > 1 else 't'} noch!",
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False,
            )

            logger.info(
                "Prediction reminder sent to %s for %d matches",
                user.email,
                len(matches),
            )
            return True, f"Reminder sent to {user.email}"

        except (SMTPException, OSError, TemplateDoesNotExist) as exc:
            logger.exception("Failed to send reminder to %s: %s", user.email, exc)
            return False, f"Failed to send email: {exc}"

    @classmethod
    def send_all_prediction_reminders(cls) -> tuple[int, int]:
        """
        Send prediction reminders to all users with missing predictions.

        Returns:
            Tuple of (successful_count, failed_count)
        """
        users_with_missing = cls.get_users_with_missing_predictions()

        if not users_with_missing:
            logger.info("No users with missing predictions found")
            return 0, 0

        success_count = 0
        fail_count = 0

        for user, matches in users_with_missing.items():
            success, message = cls.send_prediction_reminder(user, matches)
            if success:
                success_count += 1
            else:
                fail_count += 1
                logger.warning("Failed to send reminder to %s: %s", user.username, message)

        logger.info(
            "Prediction reminders sent: %d successful, %d failed",
            success_count,
            fail_count,
        )
        return success_count, fail_count
