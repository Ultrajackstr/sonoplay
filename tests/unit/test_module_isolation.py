"""Regression guard for test-suite sys.modules isolation.

Some test modules (test_adapter_stopped_state, test_audio_settings) replace heavy
dependencies with MagicMock stubs in sys.modules so they can import plex.adapters
/ settings.datastore in isolation. They now restore sys.modules afterwards. This
test deliberately imports the real `utils` (and, transitively, `settings` ->
pydantic) with NO local guard: if a stubbing test ever stops cleaning up after
itself, `xml2dict` here would be a MagicMock and this assertion would fail.

It sorts after the stubbing modules alphabetically, so it runs once they've had
their chance to pollute.
"""
from utils import xml2dict


def test_real_utils_importable_without_guard():
    # Real xml2dict returns a DotMap of the parsed XML; a leaked MagicMock stub
    # would not compare equal to "1".
    assert xml2dict("<a>1</a>").a == "1"
