"""Scoring models for the tipapp application."""

from django.db import models


class LeaderboardSnapshot(models.Model):
    """
    Stores a historical snapshot of the leaderboard at a point in time.

    Snapshots capture the complete ranking state for historical tracking
    and trend analysis. The data is stored as JSON to allow flexible
    ranking data without requiring foreign keys (which would break if
    users are deleted).
    """

    SNAPSHOT_TYPE_CHOICES = [
        ("daily", "Daily"),
        ("final", "Final"),
    ]

    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True, help_text="When this snapshot was created"
    )

    snapshot_type: models.CharField = models.CharField(
        max_length=10, choices=SNAPSHOT_TYPE_CHOICES, help_text="Type of snapshot (daily or final)"
    )

    data: models.JSONField = models.JSONField(
        help_text="Rankings array: [{rank, user_id, username, total_points, exact_match_count, jokers_used}, ...]"
    )

    class Meta:
        db_table = "scoring_leaderboardsnapshot"
        ordering = ["-created_at"]
        verbose_name = "leaderboard snapshot"
        verbose_name_plural = "leaderboard snapshots"

    def __str__(self) -> str:
        return f"{self.get_snapshot_type_display()} snapshot - {self.created_at.strftime('%Y-%m-%d %H:%M')}"  # type: ignore[attr-defined]
