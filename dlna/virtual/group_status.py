"""Health-lamp aggregation for virtual device groups.

Pure helper so the group status rollup can be unit-tested without importing
the heavy VirtualDlnaDevice (see test_group_status_lamp).
"""

# Member statuses that count as "reachable" for the group health lamp.
# A paused member is still reachable, so it counts as available -- otherwise
# pausing a whole group makes its lamp read "Unavailable"/"All Offline".
AVAILABLE_STATUSES = frozenset({"playing", "paused", "online"})


def aggregate_status_lamp(member_statuses, member_count):
    """Roll per-member statuses up into a single group health lamp.

    Args:
        member_statuses: iterable of per-member status strings
            (e.g. "playing", "paused", "online", "offline").
        member_count: total number of members in the group.

    Returns:
        (status_key, status_class, status_label) where status_key is one of
        "all_available", "degraded", or "unavailable".
    """
    available_count = sum(1 for status in member_statuses if status in AVAILABLE_STATUSES)
    if member_count > 0 and available_count == member_count:
        return "all_available", "lamp-online", "Available"
    if available_count == 0:
        return "unavailable", "lamp-offline", "Unavailable"
    return "degraded", "lamp-playing", "Degraded"
