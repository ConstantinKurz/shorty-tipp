"""
Shared ranking utilities for the tipapp application.

Provides Olympic-style ranking functionality used by both the predictions
and scoring services to ensure consistency.
"""

from collections.abc import Callable
from typing import Any


def apply_olympic_ranking(
    items: list[dict[str, Any]],
    tiebreaker_fn: Callable[[dict[str, Any], dict[str, Any]], bool],
    rank_key: str = "rank",
) -> list[dict[str, Any]]:
    """
    Apply Olympic-style ranking to a sorted list of items.

    Users with identical values (as determined by tiebreaker_fn) share the
    same rank. The next rank skips accordingly (1, 2, 2, 4, not 1, 2, 2, 3).

    Args:
        items: Pre-sorted list of dicts to rank (must be sorted by ranking criteria)
        tiebreaker_fn: Function that returns True if two items should share the same rank
        rank_key: Key name to store the rank in each dict (default: "rank")

    Returns:
        The same list with rank numbers added to each dict

    Example:
        >>> items = [
        ...     {"user": "alice", "points": 100, "exact": 5},
        ...     {"user": "bob", "points": 95, "exact": 4},
        ...     {"user": "carol", "points": 95, "exact": 4},
        ...     {"user": "dave", "points": 90, "exact": 3},
        ... ]
        >>> def tiebreaker(a, b):
        ...     return a["points"] == b["points"] and a["exact"] == b["exact"]
        >>> apply_olympic_ranking(items, tiebreaker)
        [
            {"user": "alice", "points": 100, "exact": 5, "rank": 1},
            {"user": "bob", "points": 95, "exact": 4, "rank": 2},
            {"user": "carol", "points": 95, "exact": 4, "rank": 2},
            {"user": "dave", "points": 90, "exact": 3, "rank": 4},
        ]
    """
    if not items:
        return items

    current_rank = 1
    prev_item: dict[str, Any] | None = None
    users_at_rank = 0

    for item in items:
        if prev_item is not None:
            # Check if this item shares rank with previous
            same_rank = tiebreaker_fn(item, prev_item)

            if not same_rank:
                current_rank += users_at_rank
                users_at_rank = 1
            else:
                users_at_rank += 1
        else:
            users_at_rank = 1

        item[rank_key] = current_rank
        prev_item = item

    return items


def create_tiebreaker_from_keys(
    *keys: str,
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    """
    Create a tiebreaker function that compares multiple keys.

    Args:
        *keys: Keys to compare for equality

    Returns:
        Function that returns True if all keys match between two dicts

    Example:
        >>> tiebreaker = create_tiebreaker_from_keys("total_points", "exact_count", "jokers_count")
        >>> tiebreaker(
        ...     {"total_points": 100, "exact_count": 5, "jokers_count": 2},
        ...     {"total_points": 100, "exact_count": 5, "jokers_count": 2}
        ... )
        True
    """

    def tiebreaker(a: dict[str, Any], b: dict[str, Any]) -> bool:
        return all(a.get(key) == b.get(key) for key in keys)

    return tiebreaker
