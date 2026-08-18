"""
Signals for match-related events.

This module defines signals that are sent when match data changes.
"""

from django.dispatch import Signal

# Signal sent when a match result (goals) is entered or updated
# Provides arguments: sender (Match class), match (Match instance)
match_result_entered = Signal()
