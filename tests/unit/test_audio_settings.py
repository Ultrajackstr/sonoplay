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


def _make_store():
    mock_settings = MagicMock()
    mock_settings.load_data.return_value = {"__meta__": {}}
    return JSONDataStore(mock_settings)


def test_set_audio_settings_sample_rate_only():
    """set_audio_settings must not crash when only sample_rate_hz is provided."""
    store = _make_store()
    # This should NOT raise TypeError
    store.set_audio_settings(sample_rate_hz=44100)


def test_set_audio_settings_bitrate_only():
    """set_audio_settings must work when only bitrate_kbps is provided."""
    store = _make_store()
    store.set_audio_settings(bitrate_kbps=320)
