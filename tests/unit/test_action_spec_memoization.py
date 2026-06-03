"""control() must not re-scan the SCPD action list on every SOAP call.

get_action_spec memoizes {action_name: action} after the first build, so the
0.8s poll loop's GetPositionInfo/GetTransportInfo do an O(1) dict lookup instead
of a linear scan with a per-action as_text() coercion.
"""
import types

import plex.adapters  # noqa: F401  (resolves the dlna<->plex import cycle)
from dlna.dlna_device import DlnaDeviceService

SERVICE_DICT = {
    "serviceType": "urn:schemas-upnp-org:service:AVTransport:1",
    "controlURL": "/ctrl",
    "eventSubURL": "/evt",
    "SCPDURL": "/scpd",
}
FAKE_SPEC = {"scpd": {"actionList": {"action": [{"name": "Play"}, {"name": "Stop"}]}}}


def _service():
    svc = DlnaDeviceService(SERVICE_DICT, types.SimpleNamespace(location_url="http://dev/"))
    svc._spec_info = FAKE_SPEC  # bypass the network round-trip in get_spec
    return svc


async def test_get_action_spec_returns_matching_action():
    svc = _service()
    assert (await svc.get_action_spec("Play"))["name"] == "Play"
    assert (await svc.get_action_spec("Stop"))["name"] == "Stop"


async def test_get_action_spec_unknown_returns_none():
    assert await _service().get_action_spec("Nope") is None


async def test_action_list_is_scanned_only_once():
    svc = _service()
    calls = {"n": 0}
    original = svc.get_actions

    async def counting(*a, **k):
        calls["n"] += 1
        return await original(*a, **k)

    svc.get_actions = counting
    await svc.get_action_spec("Play")
    await svc.get_action_spec("Stop")
    await svc.get_action_spec("Nope")
    assert calls["n"] == 1, f"action list re-scanned {calls['n']}x; expected memoized to 1"
