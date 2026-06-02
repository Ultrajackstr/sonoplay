"""average_group_volume backs VirtualDlnaDevice.GetVolume; it must return 0 for
an empty list (every member's volume read failed) instead of dividing by zero."""
import plex.adapters  # noqa: F401  (resolves the dlna<->plex import cycle)
from dlna.virtual.volume import average_group_volume


def test_average_of_empty_is_zero():
    assert average_group_volume([]) == 0


def test_average_of_values():
    assert average_group_volume([10, 20]) == 15


def test_average_single():
    assert average_group_volume([50]) == 50
