from django.contrib import admin

from matches.models import Match, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Admin interface for Team model."""

    list_display = ['name', 'fifa_code', 'odds_category', 'points', 'is_champion']
    list_display_links = ['name']
    list_filter = ['is_champion', 'odds_category']
    search_fields = ['name', 'fifa_code']
    ordering = ['name']
    list_editable = ['odds_category']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """Admin interface for Match model."""

    list_display = ['match_teams', 'kickoff', 'round', 'score', 'status']
    list_filter = ['round', 'status']
    search_fields = ['team_home__name', 'team_away__name']
    date_hierarchy = 'kickoff'
    ordering = ['kickoff']

    @admin.display(description='Match')
    def match_teams(self, obj: Match) -> str:
        """Display teams in list view."""
        return f"{obj.team_home.name} vs {obj.team_away.name}"

    @admin.display(description='Score')
    def score(self, obj: Match) -> str:
        """Display score if available."""
        if obj.goals_home is not None and obj.goals_away is not None:
            return f"{obj.goals_home}-{obj.goals_away}"
        return "-"
