"""Unit tests for the virtual-group health-lamp aggregation.

Pure helper, so no heavy imports / sys.modules stubbing needed.
"""
from dlna.virtual.group_status import aggregate_status_lamp


def _key(statuses):
    return aggregate_status_lamp(statuses, len(statuses))[0]


def test_all_playing_is_available():
    assert _key(["playing", "playing"]) == "all_available"


def test_all_online_is_available():
    assert _key(["online", "online"]) == "all_available"


def test_all_paused_is_available():
    # A paused group is still reachable -- it must NOT read as Unavailable.
    assert _key(["paused", "paused"]) == "all_available"


def test_paused_and_online_mix_is_available():
    assert _key(["paused", "online", "playing"]) == "all_available"


def test_all_offline_is_unavailable():
    assert _key(["offline", "offline"]) == "unavailable"


def test_some_offline_is_degraded():
    assert _key(["playing", "offline"]) == "degraded"


def test_paused_with_offline_is_degraded():
    assert _key(["paused", "offline"]) == "degraded"


def test_empty_group_is_unavailable():
    assert aggregate_status_lamp([], 0)[0] == "unavailable"


def test_returns_class_and_label_triple():
    assert aggregate_status_lamp(["playing"], 1) == ("all_available", "lamp-online", "Available")
    assert aggregate_status_lamp(["offline"], 1) == ("unavailable", "lamp-offline", "Unavailable")
    assert aggregate_status_lamp(["playing", "offline"], 2) == ("degraded", "lamp-playing", "Degraded")
