# Design: Fix Admin and Leaderboard Improvements

## Overview

This change addresses six admin and leaderboard issues through targeted fixes and enhancements. The implementation focuses on maintaining code quality, following Django best practices, and ensuring backward compatibility where appropriate.

## Architecture

### Component Overview

```
Fix Admin and Leaderboard Improvements
├── Champion Ranking Update (Signal Handler)
│   └── users/models.py: post_save signal for User
├── Icon Consistency (Templates)
│   ├── Audit current icon usage
│   ├── Create shared icon partials
│   └── Update templates to use consistent icons
├── Admin Navbar Link (Template Enhancement)
│   └── templates/base.html: conditional admin link
├── Enhanced CSV Export (Export Enhancement)
│   ├── scoring/exports.py: new detailed export function
│   └── scoring/admin.py: new admin action
├── Remove Weekly Snapshots (Model/Admin Cleanup)
│   ├── scoring/models.py: remove choice
│   ├── scoring/admin.py: remove action
│   ├── scoring/management/commands/create_snapshot.py: remove option
│   └── Add data migration
└── Manual Leaderboard Download (View)
    ├── scoring/views.py: new DownloadLeaderboardView
    ├── scoring/urls.py: new URL pattern
    └── Optional: Add navbar link
```

## Implementation Details

### 1. Champion Ranking Update Signal

**Problem**: Admin changes to `User.predicted_champion` don't trigger ranking recalculation.

**Solution**: Add post_save signal handler with field change detection.

**File**: `users/models.py`

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def recalculate_ranking_on_champion_change(
    sender, instance: User, created: bool, **kwargs
) -> None:
    """
    Recalculate rankings when user's predicted champion changes.
    
    This ensures that changing a champion prediction via admin
    triggers ranking recalculation, updating bonus points.
    """
    if created:
        # New users don't need recalculation
        return
    
    # Check if predicted_champion changed
    if instance.tracker.has_changed("predicted_champion"):
        from scoring.services import RankingService
        
        # Recalculate only this user's score
        RankingService.recalculate_user_score(instance)
```

**Requirements**:
- Install `django-model-utils` for field tracking: `pip install django-model-utils`
- Add `FieldTracker` to `User` model:
  ```python
  from model_utils import FieldTracker
  
  class User(AbstractUser):
      # ... existing fields ...
      tracker = FieldTracker(fields=["predicted_champion"])
  ```

**Alternative without django-model-utils**:
```python
@receiver(post_save, sender=User)
def recalculate_ranking_on_champion_change(
    sender, instance: User, created: bool, **kwargs
) -> None:
    if created:
        return
    
    # Fetch previous value from database
    try:
        old_instance = User.objects.get(pk=instance.pk)
        if old_instance.predicted_champion != instance.predicted_champion:
            from scoring.services import RankingService
            RankingService.recalculate_user_score(instance)
    except User.DoesNotExist:
        pass
```

**Note**: The alternative is less efficient (extra DB query) but doesn't require new dependency.

**Service Method**: Add to `scoring/services.py`:

```python
@staticmethod
def recalculate_user_score(user: User) -> None:
    """
    Recalculate scoring for a single user.
    
    Args:
        user: User instance to recalculate
    """
    # This is a wrapper for targeted recalculation
    # For now, call full recalculation (can be optimized later)
    RankingService.recalculate_all_user_scores()
```

---

### 2. Icon Consistency

**Problem**: Icons differ between prediction list and ranking views.

**Approach**:
1. Audit current icon usage across all templates
2. Identify inconsistencies (SVG paths, colors, sizes)
3. Create shared icon components
4. Replace all usages with shared components

**Audit Checklist**:
- Match status icons (locked 🔒, unlocked 🔓, finished ✅)
- Joker icons (⭐ or trophy 🏆)
- Champion icons (👑 or trophy)
- User profile icons
- Navigation icons

**Implementation Options**:

**Option A: Template Partials**
```django
{# templates/partials/icons/match_locked.html #}
<svg class="w-4 h-4 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
</svg>
```

Usage:
```django
{% include "partials/icons/match_locked.html" %}
```

**Option B: Template Tags** (more flexible)
```python
# users/templatetags/icon_tags.py
from django import template

register = template.Library()

@register.inclusion_tag("partials/icons/base_icon.html")
def icon(name: str, css_class: str = "w-4 h-4") -> dict:
    """Render an icon by name."""
    return {"name": name, "css_class": css_class}
```

**Recommended**: Use template partials (Option A) for simplicity.

**Files to Update**:
- `templates/predictions/prediction_row.html`
- `templates/predictions/prediction_list.html`
- `templates/partials/ranking_content.html`
- `templates/partials/compact_ranking.html`
- Any other templates with icons

---

### 3. Admin Navbar Link

**File**: `templates/base.html`

**Change**: Add admin link to navigation, visible only to staff users.

**Location**: After "Rules" link, before user menu separator.

```django
<a href="{% url 'users:rules' %}" class="...">
    Rules
</a>
{% if user.is_staff %}
    <a href="/admin/" class="text-zinc-600 dark:text-zinc-300 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors duration-200" target="_blank" title="Django Admin">
        Admin
    </a>
{% endif %}
<span class="text-zinc-300 dark:text-zinc-600">|</span>
```

**Notes**:
- Use `target="_blank"` to open admin in new tab (optional)
- Match existing link styling
- Position after "Rules" for logical grouping

---

### 4. Enhanced CSV Export

**Problem**: Current export only includes summary data, not prediction details.

**Solution**: Add detailed export function with per-match prediction data.

**File**: `scoring/exports.py`

Add new function:

```python
def generate_detailed_leaderboard_csv(leaderboard: list[dict]) -> str:
    """
    Generate detailed CSV with per-match prediction data.
    
    Includes user info, match details, predictions, results, points, and jokers.
    
    Args:
        leaderboard: List of dicts from RankingService.get_current_leaderboard()
        
    Returns:
        CSV content as string with detailed prediction rows
    """
    from matches.models import Match
    from predictions.models import MatchPrediction
    from users.models import User
    
    output = StringIO()
    fieldnames = [
        "rank",
        "username",
        "total_points",
        "match_id",
        "match_name",
        "match_date",
        "predicted_home",
        "predicted_away",
        "actual_home",
        "actual_away",
        "points_earned",
        "joker_used",
        "prediction_timestamp",
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    # Get all users in leaderboard
    user_ids = [entry["user_id"] for entry in leaderboard]
    users = {u.id: u for u in User.objects.filter(id__in=user_ids)}
    
    # Get all matches
    matches = Match.objects.all().order_by("date", "id")
    
    # Get all predictions
    predictions = MatchPrediction.objects.filter(
        user_id__in=user_ids
    ).select_related("match", "user")
    
    predictions_by_user = {}
    for pred in predictions:
        if pred.user_id not in predictions_by_user:
            predictions_by_user[pred.user_id] = {}
        predictions_by_user[pred.user_id][pred.match_id] = pred
    
    # Build rows
    for entry in leaderboard:
        user_id = entry["user_id"]
        user = users[user_id]
        user_preds = predictions_by_user.get(user_id, {})
        
        for match in matches:
            pred = user_preds.get(match.id)
            
            row = {
                "rank": entry["rank"],
                "username": entry["username"],
                "total_points": entry["total_points"],
                "match_id": match.id,
                "match_name": f"{match.home_team.name} vs {match.away_team.name}",
                "match_date": match.date.isoformat(),
                "predicted_home": pred.predicted_home_goals if pred else "",
                "predicted_away": pred.predicted_away_goals if pred else "",
                "actual_home": match.home_goals if match.home_goals is not None else "",
                "actual_away": match.away_goals if match.away_goals is not None else "",
                "points_earned": pred.points_earned if pred else 0,
                "joker_used": "Yes" if (pred and pred.is_joker) else "No",
                "prediction_timestamp": pred.updated_at.isoformat() if pred else "",
            }
            writer.writerow(row)
    
    return output.getvalue()
```

**Admin Action**: Add to `scoring/admin.py`:

```python
@admin.action(description="Export detailed leaderboard with predictions (CSV)")
def export_detailed_csv(self, request, queryset):
    """Export detailed CSV with all prediction data."""
    leaderboard = RankingService.get_current_leaderboard()
    return csv_response(
        leaderboard,
        filename=f"detailed_leaderboard_{timezone.now().date()}.csv",
        detailed=True,  # Flag to use detailed export
    )
```

Update `csv_response` to support detailed export:

```python
def csv_response(
    leaderboard: list[dict],
    filename: str = "leaderboard.csv",
    detailed: bool = False,
) -> HttpResponse:
    """
    Create an HttpResponse with CSV content for download.
    
    Args:
        leaderboard: List of dicts from RankingService.get_current_leaderboard()
        filename: Name of the downloaded file
        detailed: If True, include per-match prediction details
        
    Returns:
        HttpResponse with CSV content
    """
    if detailed:
        content = generate_detailed_leaderboard_csv(leaderboard)
    else:
        content = generate_leaderboard_csv(leaderboard)
        
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
```

---

### 5. Remove Weekly Snapshot Type

**Files to Modify**:

1. **scoring/models.py**:
```python
class LeaderboardSnapshot(models.Model):
    SNAPSHOT_TYPE_CHOICES = [
        ("daily", "Daily"),
        ("final", "Final"),
        # Remove: ("weekly", "Weekly"),
    ]
```

2. **scoring/admin.py**:
```python
# Remove this action:
# @admin.action(description="Create weekly snapshot from current leaderboard")
# def create_weekly_snapshot(self, request, queryset):
#     ...
```

Update actions list:
```python
actions = ["create_daily_snapshot", "export_csv"]  # Remove create_weekly_snapshot
```

3. **scoring/management/commands/create_snapshot.py**:
```python
parser.add_argument(
    "snapshot_type",
    type=str,
    choices=["daily", "final"],  # Remove "weekly"
    help="Type of snapshot to create (daily or final)",
)
```

4. **Add Data Migration**:
```python
# scoring/migrations/0002_remove_weekly_snapshots.py
from django.db import migrations

def remove_weekly_snapshots(apps, schema_editor):
    """Remove existing weekly snapshots."""
    LeaderboardSnapshot = apps.get_model("scoring", "LeaderboardSnapshot")
    count = LeaderboardSnapshot.objects.filter(snapshot_type="weekly").count()
    LeaderboardSnapshot.objects.filter(snapshot_type="weekly").delete()
    print(f"Removed {count} weekly snapshots")

class Migration(migrations.Migration):
    dependencies = [
        ("scoring", "0001_create_leaderboardsnapshot"),
    ]
    
    operations = [
        migrations.RunPython(remove_weekly_snapshots, migrations.RunPython.noop),
        # Update field choices (reflected in model, not in migration)
    ]
```

**Decision**: Keep or remove existing weekly snapshots?
- **Recommended**: Remove them (data migration above)
- **Alternative**: Keep historic data, just prevent new weekly snapshots

---

### 6. Manual Leaderboard Download

**View**: Add to `scoring/views.py`:

```python
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from scoring.exports import csv_response

@method_decorator(staff_member_required, name="dispatch")
class DownloadLeaderboardView(View):
    """
    Staff-only view to download current leaderboard as CSV.
    
    Provides on-demand leaderboard export without creating a snapshot.
    """
    
    def get(self, request: HttpRequest) -> HttpResponse:
        """Generate and return CSV of current leaderboard."""
        leaderboard = RankingService.get_current_leaderboard()
        
        # Check for detailed export request
        detailed = request.GET.get("detailed", "false").lower() == "true"
        
        filename = f"leaderboard_{timezone.now().date()}.csv"
        return csv_response(leaderboard, filename=filename, detailed=detailed)
```

**URL**: Add to `scoring/urls.py`:

```python
from django.urls import path
from . import views

app_name = "scoring"

urlpatterns = [
    # ... existing patterns ...
    path("admin/download-leaderboard/", views.DownloadLeaderboardView.as_view(), name="download-leaderboard"),
]
```

**Optional Navbar Link**: Add to `templates/base.html` (staff only):

```django
{% if user.is_staff %}
    <a href="{% url 'scoring:download-leaderboard' %}" class="..." title="Download Current Leaderboard">
        📊 Export
    </a>
{% endif %}
```

**Access URLs**:
- Summary CSV: `/scoring/admin/download-leaderboard/`
- Detailed CSV: `/scoring/admin/download-leaderboard/?detailed=true`

---

## Testing Strategy

### 1. Champion Ranking Update
- **Unit test**: Verify signal fires when champion changes
- **Unit test**: Verify signal doesn't fire on user creation
- **Unit test**: Verify signal doesn't fire when champion unchanged
- **Integration test**: Change champion via admin, verify ranking updates

### 2. Icon Consistency
- **Manual test**: Visual audit across all views
- **Template test**: Verify icon partials render correctly

### 3. Admin Navbar Link
- **View test**: Verify link visible to staff users
- **View test**: Verify link hidden from non-staff users
- **Template test**: Verify correct URL

### 4. Enhanced CSV Export
- **Unit test**: Verify detailed CSV structure
- **Unit test**: Verify CSV includes all matches and predictions
- **Integration test**: Export from admin action, verify content
- **Unit test**: Verify summary vs. detailed export

### 5. Remove Weekly Snapshots
- **Unit test**: Verify weekly choice removed from model
- **Migration test**: Verify migration removes weekly snapshots
- **Admin test**: Verify weekly action removed

### 6. Manual Leaderboard Download
- **View test**: Verify staff-only access
- **View test**: Verify non-staff gets 403/redirect
- **Integration test**: Download CSV, verify structure
- **Integration test**: Verify detailed parameter works

---

## Migration Plan

1. Deploy champion signal handler
2. Deploy icon consistency updates
3. Deploy admin navbar link
4. Deploy enhanced CSV export
5. Run migration to remove weekly snapshots
6. Deploy manual download view
7. Update documentation

**Rollback**: All changes are backward compatible except weekly snapshot removal (reversible via migration).

---

## Security Considerations

- Manual download view requires `@staff_member_required`
- CSV exports don't include sensitive data (passwords, emails)
- Signal handler doesn't introduce new permissions
- Admin link only visible to staff users
