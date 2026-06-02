import sys
import types
import pytest
from unittest.mock import MagicMock

# Stub out heavy transitive dependencies so we can import settings.datastore
# in isolation without the full runtime dependency tree.
_STUB_MODULES = [
    "dotmap", "aiohttp", "uvicorn",
    "starlette", "starlette.datastructures",
    "fastapi", "fastapi.responses", "fastapi.templating",
    "fastapi.staticfiles",
    "pydantic", "pydantic.settings", "pydantic_settings",
    "jinja2",
]

# Snapshot so we can restore sys.modules after importing settings.datastore;
# otherwise these stubs (notably pydantic) leak into later-collected test files.
_saved_modules = {_n: sys.modules.get(_n)
                  for _n in _STUB_MODULES + ["settings", "settings.datastore"]}

for _name in _STUB_MODULES:
    if _name not in sys.modules:
        mod = types.ModuleType(_name)
        mod.__path__ = []
        mod.__file__ = f"<stub {_name}>"
        mod.__getattr__ = lambda attr: MagicMock()
        sys.modules[_name] = mod

# If a prior test stubbed 'settings' as a MagicMock, remove it so we can
# import the real package.
for _key in list(sys.modules):
    if _key == "settings" or _key.startswith("settings."):
        _mod = sys.modules[_key]
        if isinstance(_mod, MagicMock) or not hasattr(_mod, "__file__") or (
            hasattr(_mod, "__file__") and _mod.__file__ and "<stub" in str(_mod.__file__)
        ):
            del sys.modules[_key]

from settings.datastore import JSONDataStore

# Restore sys.modules so this file leaves no stubs behind for later-collected
# tests. JSONDataStore is already imported (cached) and the tests use it with an
# in-memory fake, so nothing here is needed afterwards.
for _name, _mod in _saved_modules.items():
    if _mod is None:
        sys.modules.pop(_name, None)
    else:
        sys.modules[_name] = _mod


def _make_store():
    mock_settings = MagicMock()
    mock_settings.load_data.return_value = {"__meta__": {}}
    return JSONDataStore(mock_settings)


class _MemSettings:
    """In-memory load_data/save_data so the datastore round-trips for real."""

    def __init__(self):
        self._data = {}

    def load_data(self):
        return self._data

    def save_data(self, data):
        self._data = data


def _mem_store():
    return JSONDataStore(_MemSettings())


def test_set_audio_settings_sample_rate_only():
    """set_audio_settings must not crash when only sample_rate_hz is provided."""
    store = _make_store()
    # This should NOT raise TypeError
    store.set_audio_settings(sample_rate_hz=44100)


def test_set_audio_settings_bitrate_only():
    """set_audio_settings must work when only bitrate_kbps is provided."""
    store = _make_store()
    store.set_audio_settings(bitrate_kbps=320)


def test_default_audio_settings_is_no_transcode():
    """Fresh store must default to 'no limit' (None/None) so it matches the
    runtime Settings default (audio_transcode_* = None) -- otherwise loading the
    datastore at startup would silently re-enable transcoding."""
    store = _mem_store()
    audio = store.get_audio_settings()
    assert audio["bitrate_kbps"] is None
    assert audio["sample_rate_hz"] is None


def test_audio_settings_roundtrip():
    """A saved limit must survive a load (the persistence the startup path relies on)."""
    store = _mem_store()
    store.set_audio_settings(bitrate_kbps=320, sample_rate_hz=96000)
    audio = store.get_audio_settings()
    assert audio["bitrate_kbps"] == 320
    assert audio["sample_rate_hz"] == 96000


def test_audio_settings_zero_means_no_limit():
    """0 (the UI's 'no limit' choice) persists as None, not 0."""
    store = _mem_store()
    store.set_audio_settings(bitrate_kbps=0, sample_rate_hz=0)
    audio = store.get_audio_settings()
    assert audio["bitrate_kbps"] is None
    assert audio["sample_rate_hz"] is None
