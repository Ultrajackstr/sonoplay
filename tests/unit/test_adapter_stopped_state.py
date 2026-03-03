"""Unit tests for PlexDlnaAdapter.get_state() stopped-state handling.

Verifies that get_state() correctly returns {} for stopped / no-media /
None states by comparing the state *string* (self.state.state) rather
than the DlnaState object itself.
"""

import sys
import types
import pytest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out heavy transitive dependencies so we can import plex.adapters
# in isolation without needing the full runtime dependency tree.
# ---------------------------------------------------------------------------

def _make_stub(name):
    """Create a stub module whose every attribute is a MagicMock."""
    mod = types.ModuleType(name)
    mod.__path__ = []           # mark as package so sub-imports work
    mod.__file__ = f"<stub {name}>"
    mod.__getattr__ = lambda attr: MagicMock()
    return mod

_STUB_MODULES = [
    # Third-party libs
    "dotmap", "aiohttp", "aiohttp.ClientConnectionError",
    "xmltodict", "uvicorn",
    "starlette", "starlette.datastructures",
    "fastapi", "fastapi.responses", "fastapi.templating",
    "fastapi.staticfiles",
    "pydantic", "pydantic.settings",
    "jinja2",
    # Internal siblings / transitive
    "utils", "settings", "version",
    "plex.play_queue", "plex.subscribe", "plex.gdm", "plex.pin_login",
    "plex.plexserver",
    "dlna", "dlna.dlna_device", "dlna.discover",
    "dlna.virtual", "dlna.virtual.devices", "dlna.virtual.volume",
    "dlna.quirks",
]

for _name in _STUB_MODULES:
    if _name not in sys.modules:
        sys.modules[_name] = _make_stub(_name)

# Ensure the "plex" package exists but does NOT pull in plexserver
if "plex" not in sys.modules:
    _plex_pkg = types.ModuleType("plex")
    _plex_pkg.__path__ = ["plex"]
    _plex_pkg.__file__ = "<stub plex>"
    sys.modules["plex"] = _plex_pkg

# settings.settings must be subscribable
sys.modules["settings"].settings = MagicMock()

# utils helpers referenced at module level
_utils = sys.modules["utils"]
_utils.parse_timedelta = MagicMock(return_value=0)
_utils.convert_volume = MagicMock(return_value=50)
_utils.g = MagicMock()
_utils.pms_header = MagicMock(return_value={})
_utils.extract_value = MagicMock()

# PlayQueue
sys.modules["plex.play_queue"].PlayQueue = MagicMock

# DotMap
sys.modules["dotmap"].DotMap = MagicMock

# starlette QueryParams
sys.modules["starlette.datastructures"].QueryParams = MagicMock

# Now it's safe to import plex.adapters in isolation.
from plex.adapters import PlexDlnaAdapter  # noqa: E402


@pytest.fixture
def stopped_adapter():
    """Create a minimal PlexDlnaAdapter without running __init__.

    We only need the attributes that get_state() reads:
      - self.state   (a DlnaState-like object with a .state string)
      - self.queue   (None → stopped)
    """
    adapter = object.__new__(PlexDlnaAdapter)

    state = MagicMock()
    state.state = "STOPPED"

    adapter.state = state
    adapter.queue = None
    return adapter


@pytest.mark.asyncio
async def test_get_state_returns_empty_when_stopped(stopped_adapter):
    """get_state() must return {} when device state is STOPPED."""
    result = await stopped_adapter.get_state()
    assert result == {}


@pytest.mark.asyncio
async def test_get_state_returns_empty_when_no_media(stopped_adapter):
    """get_state() must return {} when device state is NO_MEDIA_PRESENT."""
    stopped_adapter.state.state = "NO_MEDIA_PRESENT"
    result = await stopped_adapter.get_state()
    assert result == {}


@pytest.mark.asyncio
async def test_get_state_returns_empty_when_state_is_none_attr(stopped_adapter):
    """get_state() must return {} when state.state is None."""
    stopped_adapter.state.state = None
    result = await stopped_adapter.get_state()
    assert result == {}


@pytest.mark.asyncio
async def test_get_state_returns_empty_when_state_obj_is_none(stopped_adapter):
    """get_state() must return {} when the state object itself is None."""
    stopped_adapter.state = None
    result = await stopped_adapter.get_state()
    assert result == {}


@pytest.mark.asyncio
async def test_get_state_returns_empty_when_queue_is_none(stopped_adapter):
    """get_state() must return {} when queue is None regardless of state."""
    stopped_adapter.state.state = "PLAYING"
    stopped_adapter.queue = None
    result = await stopped_adapter.get_state()
    assert result == {}
