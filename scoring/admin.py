"""Admin configuration for scoring app."""

import csv
from io import StringIO
from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html

from scoring.models import LeaderboardSnapshot
from scoring.services import RankingService


@admin.register(LeaderboardSnapshot)
class LeaderboardSnapshotAdmin(admin.ModelAdmin):
    """Admin interface for LeaderboardSnapshot model."""

    list_display = [
        "id",
        "snapshot_type",
        "created_at",
        "entry_count",
        "top_player",
    ]
    list_filter = ["snapshot_type", "created_at"]
    ordering = ["-created_at"]
    readonly_fields = [
        "created_at",
        "snapshot_type",
        "data",
        "formatted_rankings",
    ]
    actions = ["create_daily_snapshot", "create_weekly_snapshot", "export_csv"]

    @admin.display(description="Entries")
    def entry_count(self, obj: LeaderboardSnapshot) -> int:
        """Show number of entries in snapshot."""
        return len(obj.data) if obj.data else 0

    @admin.display(description="Leader")
    def top_player(self, obj: LeaderboardSnapshot) -> str:
        """Show the top-ranked player."""
        if obj.data and len(obj.data) > 0:
            top = obj.data[0]
            return f"{top.get('username', '?')} ({top.get('total_points', 0)} pts)"
        return "-"

    @admin.display(description="Rankings")
    def formatted_rankings(self, obj: LeaderboardSnapshot) -> str:
        """Display formatted rankings table."""
        if not obj.data:
            return "No data"

        rows = ["<table>"]
        rows.append(
            "<tr><th>Rank</th><th>Player</th><th>Points</th>"
            "<th>Exact</th><th>Jokers</th></tr>"
        )
        for entry in obj.data[:50]:  # Limit to 50 for display
            rows.append(
                f"<tr><td>{entry.get('rank', '-')}</td>"
                f"<td>{entry.get('username', '-')}</td>"
                f"<td>{entry.get('total_points', 0)}</td>"
                f"<td>{entry.get('exact_match_count', 0)}</td>"
                f"<td>{entry.get('jokers_used', 0)}</td></tr>"
            )
        if len(obj.data) > 50:
            rows.append(f"<tr><td colspan='5'>... and {len(obj.data) - 50} more</td></tr>")
        rows.append("</table>")
        return format_html("".join(rows))

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Disable manual creation - use actions instead."""
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Any = None
    ) -> bool:
        """Snapshots are immutable."""
        return False

    @admin.action(description="Create daily snapshot from current leaderboard")
    def create_daily_snapshot(
        self, request: HttpRequest, queryset: Any
    ) -> None:
        """Create a new daily snapshot."""
        snapshot = RankingService.create_snapshot("daily")
        self.message_user(
            request,
            f"Created daily snapshot with {len(snapshot.data)} entries (ID: {snapshot.pk})",
        )

    @admin.action(description="Create weekly snapshot from current leaderboard")
    def create_weekly_snapshot(
        self, request: HttpRequest, queryset: Any
    ) -> None:
        """Create a new weekly snapshot."""
        snapshot = RankingService.create_snapshot("weekly")
        self.message_user(
            request,
            f"Created weekly snapshot with {len(snapshot.data)} entries (ID: {snapshot.pk})",
        )

    @admin.action(description="Export selected snapshots to CSV")
    def export_csv(
        self, request: HttpRequest, queryset: Any
    ) -> HttpResponse:
        """Export selected snapshots to CSV."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "snapshot_id",
                "snapshot_type",
                "created_at",
                "rank",
                "username",
                "total_points",
                "exact_match_count",
                "jokers_used",
            ]
        )

        for snapshot in queryset:
            for entry in snapshot.data or []:
                writer.writerow(
                    [
                        snapshot.pk,
                        snapshot.snapshot_type,
                        snapshot.created_at.isoformat(),
                        entry.get("rank", ""),
                        entry.get("username", ""),
                        entry.get("total_points", 0),
                        entry.get("exact_match_count", 0),
                        entry.get("jokers_used", 0),
                    ]
                )

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=leaderboard_snapshots.csv"
        return response
