"""group_volume aggregates members' cached volumes into a single 0-100 group
volume for the web UI's group slider: it averages the members that report one
and returns None when none do (so the UI hides the slider, matching how a
device with no volume is handled). Mirrors GetVolume's averaging but reads the
already-cached member state instead of issuing a SOAP GetVolume per poll."""
import plex.adapters  # noqa: F401  (resolves the dlna<->plex import cycle)
from dlna.virtual.volume import group_volume


def test_none_when_no_member_reports_volume():
    assert group_volume([]) is None
    assert group_volume([None, None]) is None


def test_averages_members_that_report():
    assert group_volume([40, 60]) == 50


def test_ignores_none_members():
    assert group_volume([None, 30, None, 50]) == 40


def test_single_member():
    assert group_volume([35]) == 35
